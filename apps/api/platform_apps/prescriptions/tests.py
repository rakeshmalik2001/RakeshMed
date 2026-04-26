from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from platform_apps.notifications.models import Notification
from platform_apps.notifications.tasks import send_prescription_review_sla_alert_task
from platform_apps.prescriptions.models import Prescription
from platform_apps.users.models import User


MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe5'\xd4\xa2"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class PrescriptionNotificationFlowTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9000000001",
            password="testpass123",
            full_name="Customer One",
            role="customer",
            is_phone_verified=True,
        )
        self.pharmacist = User.objects.create_user(
            phone_number="9000000002",
            password="testpass123",
            full_name="Pharmacist One",
            role="pharmacist",
            is_staff=True,
            is_phone_verified=True,
        )
        self.admin = User.objects.create_user(
            phone_number="9000000003",
            password="testpass123",
            full_name="Admin One",
            role="admin",
            is_staff=True,
            is_phone_verified=True,
        )

    def test_upload_queues_and_creates_notifications(self) -> None:
        self.client.force_authenticate(self.customer)

        with self.captureOnCommitCallbacks(execute=True):
            with (
                patch("platform_apps.prescriptions.serializers.queue_prescription_submitted_notifications") as queue_notifications,
                patch("platform_apps.notifications.tasks.send_prescription_review_sla_alert_task.apply_async") as apply_async,
            ):
                response = self.client.post(
                    "/api/v1/prescriptions/",
                    {
                        "patient_name": "Rahul",
                        "doctor_name": "Dr. Sharma",
                        "notes": "Take after food",
                        "file": SimpleUploadedFile("rx.png", MINIMAL_PNG, content_type="image/png"),
                    },
                    format="multipart",
                )

        self.assertEqual(response.status_code, 201, response.data)
        prescription = Prescription.objects.get()

        self.assertEqual(prescription.status, "pending_review")
        queue_notifications.assert_called_once_with(prescription=prescription)
        apply_async.assert_not_called()

    def test_review_decision_notifies_customer(self) -> None:
        prescription = Prescription.objects.create(
            user=self.customer,
            reference_code="RX-TEST1234",
            patient_name="Rahul",
            doctor_name="Dr. Sharma",
            uploaded_file_name="rx.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx.png",
            uploaded_file_size_bytes=128,
            status="pending_review",
        )
        self.client.force_authenticate(self.pharmacist)

        with self.captureOnCommitCallbacks(execute=True):
            with patch("platform_apps.prescriptions.views.queue_prescription_review_notifications") as queue_notifications:
                response = self.client.post(
                    f"/api/v1/prescriptions/pharmacist/queue/{prescription.reference_code}/review/",
                    {
                        "decision": "clarification_required",
                        "notes": "Dosage is not fully legible.",
                        "clarification_message": "Please upload a clearer image.",
                    },
                    format="json",
                )

        self.assertEqual(response.status_code, 200, response.data)
        prescription.refresh_from_db()

        self.assertEqual(prescription.status, "clarification_required")
        queue_notifications.assert_called_once_with(prescription=prescription)

    def test_customer_cannot_open_pharmacist_queue(self) -> None:
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/prescriptions/pharmacist/queue/")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_open_pharmacist_queue(self) -> None:
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/prescriptions/pharmacist/queue/")

        self.assertEqual(response.status_code, 200)

    def test_upload_exposes_storage_metadata(self) -> None:
        self.client.force_authenticate(self.customer)

        with self.captureOnCommitCallbacks(execute=True):
            with (
                patch("platform_apps.prescriptions.serializers.queue_prescription_submitted_notifications"),
                patch(
                    "platform_apps.prescriptions.serializers.save_prescription_file",
                    return_value={
                        "storage_key": "prescriptions/remote-rx.png",
                        "public_url_or_signed_url": "https://cdn.truecare.in/prescriptions/remote-rx.png",
                        "size_bytes": 128,
                        "content_type": "image/png",
                        "original_name": "rx.png",
                        "storage_backend": "s3",
                    },
                ),
            ):
                response = self.client.post(
                    "/api/v1/prescriptions/",
                    {
                        "patient_name": "Rahul",
                        "doctor_name": "Dr. Sharma",
                        "notes": "Take after food",
                        "file": SimpleUploadedFile("rx.png", MINIMAL_PNG, content_type="image/png"),
                    },
                    format="multipart",
                )

        self.assertEqual(response.status_code, 201, response.data)
        prescription = Prescription.objects.get()
        detail = self.client.get(f"/api/v1/prescriptions/{prescription.reference_code}/")

        self.assertEqual(prescription.storage_backend, "s3")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(
            detail.data["uploaded_file_url"],
            "https://cdn.truecare.in/prescriptions/remote-rx.png",
        )

    def test_prescription_upload_is_rate_limited(self) -> None:
        self.client.force_authenticate(self.customer)

        with patch.dict(
            "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
            {"prescription_upload": "1/hour"},
            clear=False,
        ):
            first = self.client.post(
                "/api/v1/prescriptions/",
                {
                    "patient_name": "Rahul",
                    "doctor_name": "Dr. Sharma",
                    "notes": "Take after food",
                    "file": SimpleUploadedFile("rx1.png", MINIMAL_PNG, content_type="image/png"),
                },
                format="multipart",
            )
            second = self.client.post(
                "/api/v1/prescriptions/",
                {
                    "patient_name": "Rahul",
                    "doctor_name": "Dr. Sharma",
                    "notes": "Take after food",
                    "file": SimpleUploadedFile("rx2.png", MINIMAL_PNG, content_type="image/png"),
                },
                format="multipart",
            )

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 429)


class PrescriptionQueueServiceTests(TestCase):
    def setUp(self) -> None:
        self.customer = User.objects.create_user(
            phone_number="9000000021",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )

    def test_submitted_notification_service_enqueues_customer_and_ops_alerts(self) -> None:
        prescription = Prescription.objects.create(
            user=self.customer,
            reference_code="RX-SUBMIT",
            patient_name="Rahul",
            uploaded_file_name="rx.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx.png",
            uploaded_file_size_bytes=128,
            status="pending_review",
            review_priority="urgent",
            review_eta_hours=2,
        )

        from platform_apps.prescriptions.services import queue_prescription_submitted_notifications

        with (
            patch("platform_apps.prescriptions.services._schedule_on_commit", side_effect=lambda callback: callback()),
            patch("platform_apps.prescriptions.services.enqueue_notification") as enqueue_notification,
            patch("platform_apps.prescriptions.services.enqueue_role_notification") as enqueue_role_notification,
            patch("platform_apps.notifications.tasks.send_prescription_review_sla_alert_task.apply_async") as apply_async,
        ):
            queue_prescription_submitted_notifications(prescription=prescription)

        enqueue_notification.assert_called_once()
        enqueue_role_notification.assert_called_once()
        self.assertEqual(enqueue_notification.call_args.kwargs["user_id"], self.customer.pk)
        self.assertEqual(enqueue_notification.call_args.kwargs["title"], "Prescription received")
        self.assertEqual(
            enqueue_role_notification.call_args.kwargs["roles"],
            ["admin", "pharmacist", "support_agent"],
        )
        apply_async.assert_called_once()

    def test_review_notification_service_enqueues_customer_update(self) -> None:
        prescription = Prescription.objects.create(
            user=self.customer,
            reference_code="RX-CLARIFY",
            patient_name="Rahul",
            uploaded_file_name="rx.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx.png",
            uploaded_file_size_bytes=128,
            status="clarification_required",
            clarification_message="Please upload a clearer image.",
        )

        from platform_apps.prescriptions.services import queue_prescription_review_notifications

        with (
            patch("platform_apps.prescriptions.services._schedule_on_commit", side_effect=lambda callback: callback()),
            patch("platform_apps.prescriptions.services.enqueue_notification") as enqueue_notification,
        ):
            queue_prescription_review_notifications(prescription=prescription)

        enqueue_notification.assert_called_once()
        self.assertEqual(enqueue_notification.call_args.kwargs["user_id"], self.customer.pk)
        self.assertEqual(enqueue_notification.call_args.kwargs["title"], "Prescription needs clarification")
        self.assertIn("Please upload a clearer image.", enqueue_notification.call_args.kwargs["body"])


class PrescriptionSlaTaskTests(TestCase):
    def setUp(self) -> None:
        self.customer = User.objects.create_user(
            phone_number="9000000011",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.pharmacist = User.objects.create_user(
            phone_number="9000000012",
            password="testpass123",
            role="pharmacist",
            is_staff=True,
            is_phone_verified=True,
        )

    def test_sla_task_skips_non_pending_prescriptions(self) -> None:
        approved = Prescription.objects.create(
            user=self.customer,
            reference_code="RX-APPROVED",
            patient_name="Rahul",
            uploaded_file_name="rx.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx.png",
            uploaded_file_size_bytes=128,
            status="approved",
        )

        created = send_prescription_review_sla_alert_task(prescription_id=approved.pk)

        self.assertEqual(created, 0)
        self.assertFalse(Notification.objects.exists())

    def test_sla_task_alerts_ops_roles_for_pending_prescriptions(self) -> None:
        pending = Prescription.objects.create(
            user=self.customer,
            reference_code="RX-PENDING",
            patient_name="Rahul",
            uploaded_file_name="rx.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx.png",
            uploaded_file_size_bytes=128,
            status="pending_review",
        )

        created = send_prescription_review_sla_alert_task(prescription_id=pending.pk)

        self.assertEqual(created, 1)
        alert = Notification.objects.get(user=self.pharmacist)
        self.assertEqual(alert.title, "Prescription review SLA approaching")
        self.assertEqual(alert.meta["reference_code"], "RX-PENDING")
