from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from platform_apps.audit.services import record_audit_event
from config.throttles import PrescriptionUploadThrottle
from platform_apps.users.views import HasMatrixPermission, user_has_matrix_permission

from .models import Prescription, PrescriptionReview
from .permissions import IsPharmacistOrAdmin
from .serializers import (
    PrescriptionCreateSerializer,
    PrescriptionDecisionSerializer,
    PrescriptionDetailSerializer,
    PrescriptionListSerializer,
)
from .services import queue_prescription_review_notifications


class MyPrescriptionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "prescription_management.view",
        "POST": "prescription_management.upload",
    }
    parser_classes = [MultiPartParser, FormParser]

    def get_throttles(self):
        if self.request.method == "POST":
            return [PrescriptionUploadThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        return (
            Prescription.objects.filter(user=self.request.user)
            .select_related("reviewed_by")
            .prefetch_related("reviews__reviewer")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PrescriptionCreateSerializer
        return PrescriptionListSerializer


class MyPrescriptionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "prescription_management.view"
    serializer_class = PrescriptionDetailSerializer
    lookup_field = "reference_code"

    def get_queryset(self):
        return (
            Prescription.objects.filter(user=self.request.user)
            .select_related("reviewed_by")
            .prefetch_related("reviews__reviewer")
        )


class PharmacistQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsPharmacistOrAdmin, HasMatrixPermission]
    required_matrix_permission = "prescription_management.view"
    serializer_class = PrescriptionListSerializer

    def get_queryset(self):
        queryset = (
            Prescription.objects.select_related("user", "reviewed_by")
            .prefetch_related("reviews__reviewer")
            .order_by("-created_at")
        )
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class PharmacistPrescriptionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsPharmacistOrAdmin, HasMatrixPermission]
    required_matrix_permission = "prescription_management.view"
    serializer_class = PrescriptionDetailSerializer
    lookup_field = "reference_code"
    queryset = Prescription.objects.select_related("user", "reviewed_by").prefetch_related("reviews__reviewer")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_prescription_file(request, reference_code: str):
    if not user_has_matrix_permission(request.user, "prescription_management.view"):
        return Response({"detail": "You do not have permission to access prescriptions."}, status=status.HTTP_403_FORBIDDEN)

    queryset = Prescription.objects.select_related("user")
    if request.user.role in {"pharmacist", "admin", "finance", "support_agent"} or request.user.is_superuser:
        prescription = get_object_or_404(queryset, reference_code=reference_code)
    else:
        prescription = get_object_or_404(queryset.filter(user=request.user), reference_code=reference_code)

    if not prescription.storage_key:
        return Response({"detail": "No file is stored for this prescription."}, status=status.HTTP_404_NOT_FOUND)

    from .storage import open_prescription_file

    file_handle = open_prescription_file(prescription.storage_key)
    return FileResponse(
        file_handle,
        as_attachment=False,
        filename=prescription.uploaded_file_name,
        content_type=prescription.uploaded_file_type or "application/octet-stream",
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPharmacistOrAdmin])
@transaction.atomic
def review_prescription(request, reference_code: str):
    prescription = get_object_or_404(
        Prescription.objects.select_related("user").select_for_update(),
        reference_code=reference_code,
    )
    serializer = PrescriptionDecisionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    decision = serializer.validated_data["decision"]
    required_permission = (
        "prescription_management.approve" if decision == "approved" else "prescription_management.reject"
    )
    if not user_has_matrix_permission(request.user, required_permission):
        return Response({"detail": "You do not have permission for this prescription decision."}, status=status.HTTP_403_FORBIDDEN)

    notes = serializer.validated_data.get("notes", "")
    substitute_guidance = serializer.validated_data.get("substitute_guidance", "")
    clarification_message = serializer.validated_data.get("clarification_message", "")

    prescription.status = decision
    prescription.reviewed_by = request.user
    prescription.reviewed_at = timezone.now()
    if decision == "clarification_required":
        prescription.clarification_message = clarification_message or notes
    elif clarification_message:
        prescription.clarification_message = clarification_message
    prescription.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "clarification_message", "updated_at"]
    )

    PrescriptionReview.objects.create(
        prescription=prescription,
        reviewer=request.user,
        decision=decision,
        notes=notes,
        substitute_guidance=substitute_guidance,
    )
    record_audit_event(
        actor=request.user,
        event_type="prescription_reviewed",
        entity_type="prescription",
        entity_id=prescription.reference_code,
        severity="warning" if decision in {"clarification_required", "rejected"} else "info",
        message=f"Prescription {prescription.reference_code} marked {decision.replace('_', ' ')}.",
        meta={
            "decision": decision,
            "reviewer_role": request.user.role,
            "customer_id": prescription.user_id,
        },
    )
    queue_prescription_review_notifications(prescription=prescription)

    return Response(PrescriptionDetailSerializer(prescription).data, status=status.HTTP_200_OK)
