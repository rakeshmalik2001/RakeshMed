import secrets

from django.conf import settings
from rest_framework import serializers

from .models import Prescription, PrescriptionReview
from .services import queue_prescription_submitted_notifications
from .storage import resolve_prescription_file_access_url, save_prescription_file


class PrescriptionListSerializer(serializers.ModelSerializer):
    file_access_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = (
            "id",
            "reference_code",
            "patient_name",
            "doctor_name",
            "status",
            "review_priority",
            "review_eta_hours",
            "uploaded_file_name",
            "uploaded_file_size_bytes",
            "file_access_url",
            "created_at",
            "reviewed_at",
        )

    def get_file_access_url(self, obj: Prescription) -> str:
        storage_url = resolve_prescription_file_access_url(
            storage_key=obj.storage_key,
            fallback_url=obj.uploaded_file_url,
        )
        if storage_url:
            return storage_url
        request = self.context.get("request")
        if not request:
            return f"/api/v1/prescriptions/{obj.reference_code}/file/"
        return request.build_absolute_uri(f"/api/v1/prescriptions/{obj.reference_code}/file/")


class PrescriptionReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)

    class Meta:
        model = PrescriptionReview
        fields = (
            "id",
            "decision",
            "notes",
            "substitute_guidance",
            "reviewer_name",
            "created_at",
        )


class PrescriptionDetailSerializer(PrescriptionListSerializer):
    reviews = PrescriptionReviewSerializer(many=True, read_only=True)

    class Meta(PrescriptionListSerializer.Meta):
        fields = PrescriptionListSerializer.Meta.fields + (
            "notes",
            "clarification_message",
            "uploaded_file_url",
            "uploaded_file_type",
            "storage_backend",
            "reviews",
        )


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Prescription
        fields = (
            "patient_name",
            "doctor_name",
            "notes",
            "file",
        )

    def validate_file(self, value):
        allowed_types = {
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/jpg",
        }
        detected_type = (getattr(value, "content_type", "") or "").lower()
        if detected_type not in allowed_types:
            raise serializers.ValidationError("Only PDF, JPG, and PNG prescription files are allowed.")
        if value.size > settings.PRESCRIPTION_MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("Prescription file exceeds the maximum allowed size.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        uploaded_file = validated_data.pop("file")
        file_bytes = uploaded_file.read()
        stored_file = save_prescription_file(
            file_bytes=file_bytes,
            content_type=(uploaded_file.content_type or "application/octet-stream"),
            original_name=uploaded_file.name,
        )
        prescription = Prescription.objects.create(
            user=request.user,
            reference_code=f"RX-{secrets.token_hex(4).upper()}",
            status="pending_review",
            uploaded_file_name=stored_file["original_name"],
            uploaded_file_url=stored_file["public_url_or_signed_url"],
            uploaded_file_type=stored_file["content_type"],
            storage_key=stored_file["storage_key"],
            storage_backend=stored_file["storage_backend"],
            uploaded_file_size_bytes=stored_file["size_bytes"],
            **validated_data,
        )
        if not prescription.uploaded_file_url:
            prescription.uploaded_file_url = request.build_absolute_uri(
                f"/api/v1/prescriptions/{prescription.reference_code}/file/"
            )
        prescription.save(update_fields=["uploaded_file_url", "updated_at"])
        queue_prescription_submitted_notifications(prescription=prescription)
        return prescription


class PrescriptionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=("pending_review", "clarification_required", "approved", "rejected")
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    substitute_guidance = serializers.CharField(required=False, allow_blank=True)
    clarification_message = serializers.CharField(required=False, allow_blank=True)
