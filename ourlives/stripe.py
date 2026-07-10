import stripe
from django.conf import settings


def configure_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY


configure_stripe()


def create_checkout_session(unit_amount_cents, quantity, app_settings_id, success_url, cancel_url, customer_email=""):
    session_params = {
        "payment_method_types": [],
        "line_items": [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Invitation Code Tokens"},
                    "unit_amount": unit_amount_cents,
                },
                "quantity": quantity,
            },
        ],
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "adaptive_pricing": {"enabled": True},
        "metadata": {
            "source": "ourlives",
            "token_count": str(quantity),
            "app_settings_id": str(app_settings_id),
        },
    }

    if customer_email:
        session_params["customer_email"] = customer_email

    session = stripe.checkout.Session.create(**session_params)

    return session.url


def verify_webhook_signature(payload, signature):
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET is not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
        return event
    except stripe.error.SignatureVerificationError:
        return None
