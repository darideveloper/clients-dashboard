from django.urls import path
from ourlives import views

urlpatterns = [
    path("create-checkout/", views.create_checkout, name="create-checkout"),
    path("webhook/", views.webhook, name="webhook"),
]
