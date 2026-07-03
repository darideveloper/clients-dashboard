from django.urls import reverse_lazy

from core.models import Brand


class BrandUrlMiddleware:
    login_path = reverse_lazy("admin:login")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.rstrip("/") == str(self.login_path).rstrip("/"):
            slug = request.GET.get("brand")
            if slug:
                try:
                    request._brand_override = Brand.objects.get(slug=slug)
                except Brand.DoesNotExist:
                    pass
        return self.get_response(request)
