import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError


logger = logging.getLogger(__name__)


@dataclass
class NormalizedPaymentEvent:
    event_id: str
    provider: str
    provider_event_type: str
    normalized_status: str
    order_number: str
    payment_reference: str
    event_timestamp: str
    raw_payload: dict


@dataclass
class VerifiedPaymentResult:
    normalized_status: str
    provider_payment_id: str
    raw_payload: dict


class BasePaymentAdapter:
    provider_name = "base"

    def create_payment_session(self, *, order, attempt) -> dict:
        raise NotImplementedError

    def validate_webhook(self, request) -> None:
        raise NotImplementedError

    def parse_webhook(self, request) -> NormalizedPaymentEvent:
        raise NotImplementedError

    def verify_client_payment(self, *, order, attempt, payload: dict) -> VerifiedPaymentResult:
        raise NotImplementedError

    def build_refund_request(self, *, order, attempt, refund_request) -> dict:
        return {
            "provider": self.provider_name,
            "order_number": order.order_number,
            "payment_reference": attempt.payment_reference if attempt else "",
            "refund_request_id": refund_request.id,
            "amount": str(refund_request.amount),
        }


class SimulatedGatewayAdapter(BasePaymentAdapter):
    provider_name = "simulated_gateway"
    status_map = {
        "authorized": "authorized",
        "captured": "paid",
        "paid": "paid",
        "success": "paid",
        "failed": "failed",
        "failure": "failed",
        "refund_initiated": "refund_pending",
        "refund_pending": "refund_pending",
        "refund_queued": "refund_pending",
        "refund_processed": "refunded",
        "refunded": "refunded",
        "refund_failed": "refund_failed",
    }

    def create_payment_session(self, *, order, attempt) -> dict:
        return {
            "order_number": order.order_number,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "amount": order.total,
            "provider": settings.PAYMENT_PROVIDER_NAME,
            "provider_key": settings.PAYMENT_PROVIDER_PUBLIC_KEY,
            "payment_reference": attempt.payment_reference,
            "checkout_url": f"/account/orders/{order.order_number}?pay={attempt.payment_reference}",
            "provider_order_id": "",
            "provider_currency": "INR",
        }

    def validate_webhook(self, request) -> None:
        secret = request.headers.get("X-Webhook-Secret", "").strip()
        accepted_secrets = {
            settings.PAYMENT_WEBHOOK_SECRET,
            getattr(settings, "PAYMENT_WEBHOOK_PREVIOUS_SECRET", ""),
        }
        accepted_secrets.discard("")
        if not accepted_secrets or secret not in accepted_secrets:
            raise PermissionDenied("Invalid webhook secret.")
        raw_timestamp = request.headers.get("X-Webhook-Timestamp", "").strip() or str(request.data.get("timestamp", "")).strip()
        if raw_timestamp:
            parsed_timestamp = parse_webhook_timestamp(raw_timestamp)
            age_seconds = abs((timezone.now() - parsed_timestamp).total_seconds())
            if age_seconds > settings.PAYMENT_WEBHOOK_MAX_AGE_SECONDS:
                raise PermissionDenied("Webhook timestamp is outside the accepted replay window.")

    def parse_webhook(self, request) -> NormalizedPaymentEvent:
        raw_status = str(request.data.get("status", "pending")).strip().lower()
        return NormalizedPaymentEvent(
            event_id=request.headers.get("X-Webhook-Event-Id", "").strip() or str(request.data.get("event_id", "")).strip(),
            provider=str(request.data.get("provider", settings.PAYMENT_PROVIDER_NAME)).strip() or self.provider_name,
            provider_event_type=raw_status,
            normalized_status=self.status_map.get(raw_status, "pending"),
            order_number=str(request.data.get("order_number", "")).strip(),
            payment_reference=str(request.data.get("payment_reference", "")).strip(),
            event_timestamp=request.headers.get("X-Webhook-Timestamp", "").strip() or str(request.data.get("timestamp", "")).strip(),
            raw_payload=request.data,
        )

    def verify_client_payment(self, *, order, attempt, payload: dict) -> VerifiedPaymentResult:
        return VerifiedPaymentResult(
            normalized_status="captured",
            provider_payment_id=str(payload.get("payment_reference", attempt.payment_reference)).strip() or attempt.payment_reference,
            raw_payload={**attempt.raw_payload, "verification": payload},
        )


class GenericProviderAdapter(SimulatedGatewayAdapter):
    provider_name = "generic_provider"

    def create_payment_session(self, *, order, attempt) -> dict:
        payload = super().create_payment_session(order=order, attempt=attempt)
        payload["checkout_url"] = f"/account/orders/{order.order_number}?provider={settings.PAYMENT_PROVIDER_NAME}&pay={attempt.payment_reference}"
        return payload


class RazorpayAdapter(BasePaymentAdapter):
    provider_name = "razorpay"
    api_base_url = "https://api.razorpay.com/v1"
    event_status_map = {
        "payment.authorized": "authorized",
        "payment.captured": "captured",
        "payment.failed": "failed",
        "order.paid": "paid",
        "refund.created": "refund_pending",
        "refund.processed": "refunded",
        "refund.failed": "refund_failed",
    }
    entity_status_map = {
        "authorized": "authorized",
        "captured": "captured",
        "failed": "failed",
        "refunded": "refunded",
    }

    def create_payment_session(self, *, order, attempt) -> dict:
        provider_order_id = str(attempt.raw_payload.get("provider_order_id", "")).strip()
        provider_currency = str(attempt.raw_payload.get("provider_currency", "INR")).strip() or "INR"

        if not provider_order_id:
            response = self._request_json(
                "/orders",
                {
                    "amount": self._to_subunits(order.total),
                    "currency": provider_currency,
                    "receipt": attempt.payment_reference,
                    "notes": {
                        "order_number": order.order_number,
                        "payment_reference": attempt.payment_reference,
                    },
                },
            )
            provider_order_id = str(response.get("id", "")).strip()
            if not provider_order_id:
                raise APIException("Razorpay did not return an order id.")
            attempt.raw_payload = {
                **attempt.raw_payload,
                "provider_order_id": provider_order_id,
                "provider_currency": str(response.get("currency", provider_currency)).strip() or provider_currency,
                "provider_amount": response.get("amount", self._to_subunits(order.total)),
                "provider_response": response,
            }
            attempt.save(update_fields=["raw_payload"])

        return {
            "order_number": order.order_number,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "amount": order.total,
            "provider": self.provider_name,
            "provider_key": settings.PAYMENT_PROVIDER_PUBLIC_KEY,
            "payment_reference": attempt.payment_reference,
            "checkout_url": f"/account/orders/{order.order_number}",
            "provider_order_id": provider_order_id,
            "provider_currency": str(attempt.raw_payload.get("provider_currency", provider_currency)).strip() or "INR",
        }

    def validate_webhook(self, request) -> None:
        signature = request.headers.get("X-Razorpay-Signature", "").strip()
        if not signature:
            raise PermissionDenied("Missing Razorpay webhook signature.")

        raw_body = request.body
        accepted_secrets = [
            secret
            for secret in [settings.PAYMENT_WEBHOOK_SECRET, getattr(settings, "PAYMENT_WEBHOOK_PREVIOUS_SECRET", "")]
            if secret
        ]
        if not accepted_secrets:
            raise PermissionDenied("Webhook secret is not configured.")

        if not any(
            hmac.compare_digest(
                signature,
                hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest(),
            )
            for secret in accepted_secrets
        ):
            raise PermissionDenied("Invalid Razorpay webhook signature.")

    def parse_webhook(self, request) -> NormalizedPaymentEvent:
        payment_entity = self._get_nested_entity(request.data, "payment")
        order_entity = self._get_nested_entity(request.data, "order")
        refund_entity = self._get_nested_entity(request.data, "refund")
        notes = payment_entity.get("notes") or order_entity.get("notes") or refund_entity.get("notes") or {}
        event_type = str(request.data.get("event", "")).strip().lower()
        entity_status = (
            str(payment_entity.get("status", "")).strip().lower()
            or str(refund_entity.get("status", "")).strip().lower()
            or str(order_entity.get("status", "")).strip().lower()
        )

        return NormalizedPaymentEvent(
            event_id=request.headers.get("X-Razorpay-Event-Id", "").strip(),
            provider=self.provider_name,
            provider_event_type=event_type or entity_status or "pending",
            normalized_status=self.event_status_map.get(event_type, self.entity_status_map.get(entity_status, "pending")),
            order_number=str(notes.get("order_number", "")).strip(),
            payment_reference=(
                str(notes.get("payment_reference", "")).strip()
                or str(payment_entity.get("id", "")).strip()
                or str(refund_entity.get("payment_id", "")).strip()
                or str(order_entity.get("receipt", "")).strip()
            ),
            event_timestamp=str(request.data.get("created_at", "")).strip(),
            raw_payload=request.data,
        )

    def verify_client_payment(self, *, order, attempt, payload: dict) -> VerifiedPaymentResult:
        provider_order_id = str(payload.get("razorpay_order_id", "")).strip()
        provider_payment_id = str(payload.get("razorpay_payment_id", "")).strip()
        provider_signature = str(payload.get("razorpay_signature", "")).strip()
        expected_order_id = str(attempt.raw_payload.get("provider_order_id", "")).strip()

        if not provider_order_id or not provider_payment_id or not provider_signature:
            raise ValidationError("Razorpay payment verification payload is incomplete.")

        if not expected_order_id:
            raise ValidationError("Payment attempt is missing a Razorpay order id.")

        if provider_order_id != expected_order_id:
            raise PermissionDenied("Razorpay order id does not match this payment attempt.")

        signed_payload = f"{provider_order_id}|{provider_payment_id}".encode("utf-8")
        expected_signature = hmac.new(
            settings.PAYMENT_PROVIDER_SECRET_KEY.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(provider_signature, expected_signature):
            raise PermissionDenied("Invalid Razorpay payment signature.")

        return VerifiedPaymentResult(
            normalized_status="captured",
            provider_payment_id=provider_payment_id,
            raw_payload={
                **attempt.raw_payload,
                "provider_payment_id": provider_payment_id,
                "provider_signature": provider_signature,
            },
        )

    @staticmethod
    def _get_nested_entity(payload: dict, entity_name: str) -> dict:
        return payload.get("payload", {}).get(entity_name, {}).get("entity", {}) or {}

    @staticmethod
    def _to_subunits(amount) -> int:
        return int(round(float(amount) * 100))

    def _request_json(self, path: str, payload: dict) -> dict:
        basic_token = base64.b64encode(
            f"{settings.PAYMENT_PROVIDER_PUBLIC_KEY}:{settings.PAYMENT_PROVIDER_SECRET_KEY}".encode("utf-8")
        ).decode("utf-8")
        request = urllib_request.Request(
            f"{self.api_base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Basic {basic_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="ignore")
            logger.warning(
                "Razorpay order creation failed: status=%s body=%s",
                getattr(exc, "code", "unknown"),
                response_body or exc.reason,
            )
            if exc.code in {400, 401, 403}:
                raise APIException(
                    "Could not start Razorpay checkout. Check the configured Razorpay key pair and whether the account is in test mode."
                ) from exc
            raise APIException("Could not start Razorpay checkout right now. Please try again shortly.") from exc
        except urllib_error.URLError as exc:
            logger.warning("Razorpay request could not be completed: %s", exc)
            raise APIException("Could not reach Razorpay from the API service.") from exc


def parse_webhook_timestamp(raw_value: str):
    from datetime import datetime

    if raw_value.isdigit():
        return datetime.fromtimestamp(int(raw_value), tz=timezone.utc)
    normalized = raw_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PermissionDenied("Invalid webhook timestamp.") from exc
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def get_payment_adapter(provider_name: str | None = None) -> BasePaymentAdapter:
    resolved = (provider_name or settings.PAYMENT_PROVIDER_NAME or "simulated_gateway").strip().lower()
    if resolved == "simulated_gateway":
        return SimulatedGatewayAdapter()
    if resolved == "razorpay":
        return RazorpayAdapter()
    return GenericProviderAdapter()
