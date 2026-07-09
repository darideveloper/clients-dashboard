import stripe
from django.conf import settings


def configure_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY


configure_stripe()


def create_checkout_session(amount_usd, token_count, app_settings_id, success_url, cancel_url):
    amount_cents = int(amount_usd * 100)

    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{token_count} Invitation Code Tokens",
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            },
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "source": "ourlives",
            "token_count": str(token_count),
            "app_settings_id": str(app_settings_id),
        },
    )

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
