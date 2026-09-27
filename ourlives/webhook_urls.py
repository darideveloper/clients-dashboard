from django.urls import path

from ourlives import views

urlpatterns = [
    path("ourlens/", views.form_webhook, name="form_webhook"),
]