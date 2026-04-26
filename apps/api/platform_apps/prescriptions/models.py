from django.conf import settings
from django.db import models


class Prescription(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("pending_review", "Pending Review"),
        ("clarification_required", "Clarification Required"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    REVIEW_PRIORITY_CHOICES = (
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    )

    reference_code = models.CharField(max_length=24, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prescriptions")
    patient_name = models.CharField(max_length=255)
    doctor_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    uploaded_file_name = models.CharField(max_length=255)
    uploaded_file_url = models.URLField(blank=True)
    uploaded_file_type = models.CharField(max_length=64, blank=True)
    storage_key = models.CharField(max_length=500, blank=True)
    storage_backend = models.CharField(max_length=40, blank=True)
    uploaded_file_size_bytes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="submitted")
    review_priority = models.CharField(max_length=16, choices=REVIEW_PRIORITY_CHOICES, default="normal")
    review_eta_hours = models.PositiveIntegerField(default=4)
    clarification_message = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_prescriptions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference_code"]),
            models.Index(fields=["status", "review_priority", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference_code} - {self.patient_name}"


class PrescriptionReview(models.Model):
    DECISION_CHOICES = (
        ("submitted", "Submitted"),
        ("pending_review", "Pending Review"),
        ("clarification_required", "Clarification Required"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prescription_reviews")
    decision = models.CharField(max_length=32, choices=DECISION_CHOICES)
    notes = models.TextField(blank=True)
    substitute_guidance = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.prescription.reference_code} - {self.decision}"
