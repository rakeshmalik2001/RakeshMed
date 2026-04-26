from rest_framework.throttling import ScopedRateThrottle


class AuthSendOtpThrottle(ScopedRateThrottle):
    scope = "auth_send_otp"


class AuthVerifyOtpThrottle(ScopedRateThrottle):
    scope = "auth_verify_otp"
