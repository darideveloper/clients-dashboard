import json
import logging
from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages as django_messages
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ourlives.models import AppSettings, StripeEvent, calculate_token_count
from ourlives.stripe import create_checkout_session, verify_webhook_signature

logger = logging.getLogger(__name__)


@require_POST
def create_checkout(request):
    if not request.user.has_module_perms("ourlives"):
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        data = request.POST

    try:
        amount = Decimal(data.get("amount", "0"))
    except (TypeError, ValueError, ArithmeticError):
        return JsonResponse({"error": "Invalid amount"}, status=400)

    if amount <= 0:
        return JsonResponse({"error": "Amount must be greater than zero"}, status=400)

    settings_obj = AppSettings.get_solo()

    if settings_obj.price_per_token is None or settings_obj.price_per_token <= 0:
        return JsonResponse({"error": "Price must be configured first"}, status=400)

    if settings_obj.min_purchase_amount > 0 and amount < settings_obj.min_purchase_amount:
        return JsonResponse(
            {"error": f"Minimum purchase amount is ${settings_obj.min_purchase_amount:.2f}"},
            status=400,
        )

    token_count = calculate_token_count(amount, settings_obj.price_per_token)

    if token_count < 1:
        return JsonResponse(
            {"error": f"Amount too low. Minimum ${settings_obj.price_per_token:.2f} required for 1 token"},
            status=400,
        )

    referer = request.META.get("HTTP_REFERER", "")
    if referer:
        parsed = urlparse(referer)
        purchase_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    else:
        purchase_url = request.build_absolute_uri("/admin/ourlives/appsettings/purchase/")
    unit_amount_cents = int(settings_obj.price_per_token * 100)
    checkout_url = create_checkout_session(
        unit_amount_cents=unit_amount_cents,
        quantity=token_count,
        app_settings_id=settings_obj.pk,
        success_url=purchase_url,
        cancel_url=purchase_url,
        customer_email=request.user.email or "",
    )

    return redirect(checkout_url)


@csrf_exempt
@require_POST
def webhook(request):
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Invalid content type")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        return HttpResponseBadRequest("Missing Stripe-Signature header")

    event = verify_webhook_signature(payload, sig_header)

    if event is None:
        return HttpResponseBadRequest("Invalid signature")

    event_type = event.get("type")
    if event_type != "checkout.session.completed":
        logger.info("Ignoring unhandled event type: %s", event_type)
        return HttpResponse("OK")

    stripe_event_id = event.get("id")
    if StripeEvent.objects.filter(stripe_event_id=stripe_event_id).exists():
        logger.info("Duplicate event %s, skipping", stripe_event_id)
        return HttpResponse("OK")

    from ourlives.models import process_ourlives_checkout_completion

    process_ourlives_checkout_completion(event)

    return HttpResponse("OK")
