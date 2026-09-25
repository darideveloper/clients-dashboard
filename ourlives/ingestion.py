"""Ourlens form webhook ingestion service.

Turns an n8n `mapping` payload (descriptive keys, OL-86+) into CRM rows:
Order / Organization / Rep / Contacts / Address / OrderItem(s) / InvitationCode(s).

Design decision summary (see openspec/changes/form-webhook-ingestion):
- `ourlens` is ALWAYS the code project for this webhook.
- Codes are auto-created per non-empty `code-N` (independent of the toggle);
  `code_type` is null when no bundle label is present.
- Reconcile is additive: existing codes/items never deleted; availability may
  go negative.
"""

import html
import logging
import re

from decimal import Decimal

from ourlives.models import (
    AppSettings,
    CodeType,
    Contact,
    ContactType,
    Country,
    Currency,
    InvitationCode,
    Order,
    OrderItem,
    OrderType,
    Organization,
    OrganizationAddress,
    Product,
    Project,
    Rep,
)

logger = logging.getLogger(__name__)

OURLENS_PROJECT_NAME = "ourlens"


class RejectedSubmission(Exception):
    """Payload is unprocessable (e.g. legacy/malformed) — end as `rejected`, not `error`."""

# pilot_currency code -> (region display name, product field, quantity field, price field)
PILOT_REGIONS = {
    "USD": ("US", "product-us", "quantity-us", "us-dollars"),
    "CAD": ("Canada", "product-canada", "quantity-canada", "canadian-dollars"),
    "GBP": ("UK", "product-uk", "quantity-uk", "gbp"),
    "ZAR": ("South Africa", "product-south-africa", "quantity-south-africa", "zar"),
}

# Form label -> fixture name, for labels that normalize differently than the
# fixture's stored name (applied after an exact normalized match fails).
def _norm_key(value):
    return "".join(ch for ch in value.casefold() if ch.isalnum())


_RAW_ALIASES = {
    "Vatican City": "Holy See",
    "East Timor": "Timor-Leste",
    "Brunei": "Brunei Darussalam",
    "Swaziland": "Eswatini",
    "Macedonia": "North Macedonia",
    "Moldova": "Moldova, Republic of",
    "Côte d'Ivoire": "Cote d'Ivoire",
    "Cape Verde": "Cabo Verde",
    "Czech Republic": "Czechia",
    "Laos": "Lao People's Democratic Republic",
    "Micronesia": "Micronesia, Federated States of",
    "North Korea": "Korea, Democratic People's Republic of",
    "Palestine": "Palestine, State of",
    "Russia": "Russian Federation",
    "South Korea": "Korea, Republic of",
    "Syria": "Syrian Arab Republic",
    "Taiwan": "Taiwan, Province of China",
    "Tanzania": "Tanzania, United Republic of",
    "Vietnam": "Viet Nam",
}

ALIASES = {
    _norm_key(k): _norm_key(v) for k, v in _RAW_ALIASES.items()
}


def normalize_order_number(value):
    """Collapse whitespace around dashes: 'OL - 95' -> 'OL-95'."""
    if not value:
        return ""
    return re.sub(r"\s*-\s*", "-", str(value).strip())


def normalize_name(value):
    """Lowercase and strip all whitespace, for natural-key matching."""
    if not value:
        return ""
    return "".join(str(value).casefold().split())


def split_full_name(value):
    """Split on the first space: 'Demo Harry Judd' -> ('Demo', 'Harry Judd')."""
    value = str(value or "").strip()
    if not value:
        return "", ""
    first, _, rest = value.partition(" ")
    return first, rest.strip()


def split_address(raw):
    """Right-anchored comma parse -> {line1, line2, city, state, zip, country}.

    Tolerates 5-part (no line2) and 6-part addresses; country is the trailing
    select value.
    """
    parts = [p.strip() for p in (raw or "").split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return {"line1": "", "line2": "", "city": "", "state": "", "zip": "", "country": ""}
    country = parts[-1]
    zip_ = parts[-2] if len(parts) >= 2 else ""
    state = parts[-3] if len(parts) >= 3 else ""
    city = parts[-4] if len(parts) >= 4 else ""
    rest = parts[:-4]
    line1 = rest[0] if rest else ""
    line2 = ", ".join(rest[1:])
    return {
        "line1": line1,
        "line2": line2,
        "city": city,
        "state": state,
        "zip": zip_,
        "country": country,
    }


def resolve_country(label):
    """Resolve a form country label to a Country row, or None."""
    if not label:
        return None
    key = _norm_key(label)
    if key in ALIASES:
        key = ALIASES[key]
    for country in Country.objects.all():
        if _norm_key(country.name) == key:
            return country
    return None


def resolve_currency(code):
    if not code:
        return None
    return Currency.objects.filter(code=str(code).strip().upper()).first()


def resolve_code_type(bundle_name):
    if not bundle_name:
        return None
    return CodeType.objects.filter(name=str(bundle_name).strip()).first()


def resolve_product(region, tier):
    if not region or not tier:
        return None
    return Product.objects.filter(name=f"{region} {tier} Pilot").first()


def ourlens_project():
    # ponytail: get_or_create keeps fresh/test DBs working while the fixture
    # guarantees the real row; idempotent, never creates a duplicate.
    return Project.objects.get_or_create(name=OURLENS_PROJECT_NAME)[0]


def _val(mapping, key):
    value = mapping.get(key) if isinstance(mapping, dict) else None
    return str(value).strip() if value is not None else ""


def _yes(mapping, key):
    return _val(mapping, key).casefold() == "yes"


def strip_html(text):
    if not text:
        return ""
    unescaped = html.unescape(str(text))
    no_tags = re.sub(r"<[^>]+>", "", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def get_or_create_org(line1):
    normalized = normalize_name(line1)
    if not normalized:
        raise ValueError("Organization address line1 is required")
    for candidate in Organization.objects.all():
        if normalize_name(candidate.name) == normalized:
            return candidate
    return Organization.objects.create(name=line1)


def get_or_create_rep(email, full_name):
    first, last = split_full_name(full_name)
    return Rep.objects.get_or_create(
        email__iexact=email,
        defaults={"email": email, "first_name": first, "last_name": last or first},
    )[0]


def get_or_create_contact(org, email, name, phone, contact_type):
    first, last = split_full_name(name)
    defaults = {
        "contact_type": contact_type,
        "first_name": first,
        "last_name": last or first,
        "phone": phone,
    }
    return Contact.objects.get_or_create(
        organization=org, email__iexact=email,
        defaults={**defaults, "email": email},
    )[0]


def _contact_type(code):
    return ContactType.objects.filter(code=code).first()


def _resolve_order_type(code):
    return OrderType.objects.filter(code=code).first()


def _find_existing_order(normalized):
    for oid, raw in Order.objects.values_list("pk", "order_number"):
        if normalize_order_number(raw) == normalized:
            return Order.objects.get(pk=oid)
    return None


def _upsert_address(org, parsed):
    address = (
        OrganizationAddress.objects.filter(organization=org, is_primary=True).first()
        or OrganizationAddress.objects.filter(organization=org).order_by("pk").first()
    )
    country = resolve_country(parsed["country"])
    if address is None:
        return OrganizationAddress.objects.create(
            organization=org,
            country=country,
            line1=parsed["line1"],
            line2=parsed["line2"],
            city=parsed["city"],
            state=parsed["state"],
            zip=parsed["zip"],
            is_primary=True,
        )
    for field, value in (
        ("country", country),
        ("line1", parsed["line1"]),
        ("line2", parsed["line2"]),
        ("city", parsed["city"]),
        ("state", parsed["state"]),
        ("zip", parsed["zip"]),
    ):
        setattr(address, field, value)
    address.save()
    return address


def _build_pilot_items(order, mapping):
    """Create/replace OrderItems from the pilot-currency region block.

    Returns True when a product block was resolved, False when the pilot
    currency has no region block (e.g. EUR) so the caller can flag it.
    """
    pilot_currency = _val(mapping, "pilot-currency")
    region = PILOT_REGIONS.get(pilot_currency.strip().upper())
    if region is None:
        return False
    region_name, product_key, qty_key, price_key = region
    tier_value = _val(mapping, product_key)
    if not tier_value:
        return False
    tier = tier_value.split()[0]
    product = resolve_product(region_name, tier)
    if product is None:
        logger.warning("Pilot product not found: %s %s Pilot", region_name, tier)
        return False
    quantity = _val(mapping, qty_key)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1
    price = _val(mapping, price_key)
    try:
        unit_price = Decimal(price)
    except (TypeError, ValueError, ArithmeticError):
        unit_price = product.unit_price
    order.items.all().delete()
    OrderItem.objects.create(
        order=order, product=product, quantity=quantity, unit_price=unit_price
    )
    return True


def _create_codes(order, org, mapping, code_type):
    """Auto-create InvitationCodes from non-empty code-N; additive only.

    Non-empty values are de-duplicated deterministically (within the submission
    and against the order's existing codes), so a repeated literal never
    triggers a partial/failed create and never invents extra tokens. Duplicate
    skips are logged rather than raised.

    Returns the number of codes created on this call (accumulates on orders).
    """
    project = ourlens_project()
    existing = (
        set(order.invitation_codes.values_list("code", flat=True)) if order.pk else set()
    )
    seen = set()
    created = 0
    for slot in range(1, 21):
        value = _val(mapping, f"code-{slot}")
        if not value:
            continue
        if value in existing or value in seen:
            if value not in existing:
                logger.warning(
                    "Duplicate code value %r in submission skipped on order %s",
                    value, order.order_number,
                )
            continue
        try:
            InvitationCode.objects.create(
                project=project,
                organization=org,
                order=order,
                code=value,
                code_type=code_type,
                sequence=slot,
                is_active=True,
                max_use=1,
                current_use=0,
            )
        except Exception as exc:  # noqa: BLE001 - tolerant (e.g. global code collision)
            logger.warning("Skipping code %s on %s: %s", value, order.order_number, exc)
            continue
        existing.add(value)
        seen.add(value)
        created += 1
    return created


def ingest(mapping):
    """Create or reconcile an Order (and related rows) from an n8n mapping.

    Returns (status, order) where status is 'created' or 'updated'.
    """
    raw_order = _val(mapping, "order-number")
    if not raw_order:
        raise RejectedSubmission("order-number is required")
    normalized = normalize_order_number(raw_order)

    order = _find_existing_order(normalized)
    status = "updated" if order is not None else "created"

    parsed_address = split_address(_val(mapping, "company-address-purchasing-ourlens-scans"))
    org = get_or_create_org(parsed_address["line1"])
    _upsert_address(org, parsed_address)

    rep = get_or_create_rep(
        _val(mapping, "reps-email"), _val(mapping, "reps-name")
    )
    primary_contact = get_or_create_contact(
        org,
        _val(mapping, "primary-contact-email"),
        _val(mapping, "primary-contact"),
        _val(mapping, "primary-contact-phone"),
        _contact_type("primary"),
    )
    invoice_contact = get_or_create_contact(
        org,
        _val(mapping, "invoice-email"),
        _val(mapping, "invoice-contact"),
        _val(mapping, "invoice-contact-phone"),
        _contact_type("invoice"),
    )

    is_pilot = _yes(mapping, "is-this-a-pilot-order")
    order_type = _resolve_order_type("pilot" if is_pilot else "standard")

    order_fields = {
        "organization": org,
        "rep": rep,
        "primary_contact": primary_contact,
        "invoice_contact": invoice_contact,
        "po_number": _val(mapping, "po-number") or "",
        "is_upgrade_from_pilot": _yes(mapping, "is-this-an-upgrade-from-a-pilot"),
        "is_referral_order": _yes(mapping, "is-this-an-order-following-a-referral"),
        "referral_organisation": _val(mapping, "name-of-the-organsation-who-is-referring") or None,
        "additional_information": strip_html(
            _val(mapping, "please-add-an-additional-information-relating-to-this-order")
        ),
    }

    if is_pilot:
        order_fields["pilot_currency"] = resolve_currency(_val(mapping, "pilot-currency"))
        order_fields["currency"] = None
        order_fields["number_of_scans"] = None
        order_fields["cost_per_scan"] = None
    else:
        order_fields["currency"] = resolve_currency(_val(mapping, "currency"))
        order_fields["pilot_currency"] = None
        order_fields["number_of_scans"] = (
            int(_val(mapping, "number-of-scans")) if _val(mapping, "number-of-scans").isdigit() else None
        )
        order_fields["cost_per_scan"] = (
            Decimal(_val(mapping, "cost-per-scan"))
            if re.fullmatch(r"\d+(\.\d+)?", _val(mapping, "cost-per-scan"))
            else None
        )

    if order is None:
        order = Order.objects.create(order_number=raw_order, tokens_used=0, **order_fields)
    else:
        for field, value in order_fields.items():
            setattr(order, field, value)
        order.save()

    if order.pk and order.order_types.exists():
        order.order_types.clear()
    if order_type is not None:
        order.order_types.add(order_type)

    pilot_resolved = True
    if is_pilot:
        pilot_resolved = _build_pilot_items(order, mapping)

    code_type = resolve_code_type(
        _val(mapping, "how-many-additional-codes-do-you-require")
    )
    created_codes = _create_codes(order, org, mapping, code_type)
    if created_codes:
        order.tokens_used = (order.tokens_used or 0) + created_codes
        order.save(update_fields=("tokens_used",))

    country_label = parsed_address["country"]
    if country_label and resolve_country(country_label) is None:
        logger.warning("Unresolved country label: %r on order %s", country_label, raw_order)

    if is_pilot and not pilot_resolved:
        logger.warning(
            "Pilot order %s had no resolvable product block (e.g. EUR), created zero-price",
            raw_order,
        )

    return status, order