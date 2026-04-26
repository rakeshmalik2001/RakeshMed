from rest_framework.throttling import SimpleRateThrottle


class BaseRequestRateThrottle(SimpleRateThrottle):
    scope = ""

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class PublicCatalogReadThrottle(BaseRequestRateThrottle):
    scope = "public_catalog_read"


class PublicCatalogSearchThrottle(BaseRequestRateThrottle):
    scope = "public_catalog_search"


class PublicServiceabilityThrottle(BaseRequestRateThrottle):
    scope = "public_serviceability"


class CheckoutThrottle(BaseRequestRateThrottle):
    scope = "checkout"


class PaymentSessionThrottle(BaseRequestRateThrottle):
    scope = "payment_session"


class PrescriptionUploadThrottle(BaseRequestRateThrottle):
    scope = "prescription_upload"


class PaymentWebhookThrottle(BaseRequestRateThrottle):
    scope = "payment_webhook"
