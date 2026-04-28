from unittest.mock import patch
from io import StringIO

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from platform_apps.audit.models import AuditLog
from platform_apps.notifications.models import Notification
from platform_apps.prescriptions.models import Prescription

from .admin import UserAdmin
from .forms import UserManagementForm
from .models import OTPRequest, RolePermissionMatrix, User
from .views import ensure_role_permission_matrices
from .services import notify_overdue_approval_escalation, notify_user_of_approval_decision, run_overdue_approval_escalations


class EmployeeCodeWorkflowTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            phone_number="9000000401",
            email="employee-code-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_generate_unique_employee_code_uses_role_prefix(self) -> None:
        employee_code = User.generate_unique_employee_code("admin")

        self.assertTrue(employee_code.startswith("ADM-"))
        self.assertEqual(len(employee_code.split("-")[1]), 8)

    def test_generate_unique_username_uses_full_name(self) -> None:
        username = User.generate_unique_username("Rakesh Malik")

        self.assertEqual(username, "rakesh.malik")

    def test_generate_unique_username_appends_suffix_when_taken(self) -> None:
        User.objects.create_user(
            phone_number="9000000414",
            email="existing-username@example.com",
            password="testpass123",
            username="rakesh.malik",
            role="admin",
            approval_status="approved",
            account_status="active",
        )

        username = User.generate_unique_username("Rakesh Malik")

        self.assertEqual(username, "rakesh.malik2")

    def test_employee_code_generate_endpoint_returns_role_based_code(self) -> None:
        response = self.client.get("/api/v1/auth/admin/users/employee-code/generate/?role=pharmacist")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["prefix"], "PHR")
        self.assertTrue(response.data["employee_code"].startswith("PHR-"))

    def test_username_generate_endpoint_returns_next_available_username(self) -> None:
        User.objects.create_user(
            phone_number="9000000416",
            email="existing-rakesh@example.com",
            password="testpass123",
            username="rakesh.malik",
            role="admin",
            approval_status="approved",
            account_status="active",
        )

        response = self.client.get("/api/v1/auth/admin/users/username/generate/?full_name=Rakesh%20Malik")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "rakesh.malik2")

    def test_employee_code_lookup_endpoint_returns_user_payload(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000402",
            email="lookup-user@example.com",
            password="testpass123",
            role="support_agent",
            employee_code="SUP-12345678",
            full_name="Lookup User",
            department="Support",
            designation="Support Agent",
            approval_status="approved",
            account_status="active",
        )

        response = self.client.get(f"/api/v1/auth/admin/users/employee-code/lookup/?employee_code={user.employee_code}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], user.pk)
        self.assertEqual(response.data["full_name"], "Lookup User")
        self.assertEqual(response.data["role"], "support_agent")

    def test_employee_code_lookup_endpoint_accepts_numeric_code_only(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000412",
            email="numeric-lookup-user@example.com",
            password="testpass123",
            role="security_admin",
            employee_code="SEC-73702670",
            full_name="Numeric Lookup User",
            approval_status="approved",
            account_status="active",
        )

        response = self.client.get("/api/v1/auth/admin/users/employee-code/lookup/?employee_code=73702670")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], user.pk)
        self.assertEqual(response.data["employee_code"], "SEC-73702670")

    def test_employee_code_lookup_endpoint_accepts_user_id(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000413",
            email="id-lookup-user@example.com",
            password="testpass123",
            role="warehouse_operator",
            employee_code="WHO-51689791",
            full_name="ID Lookup User",
            approval_status="approved",
            account_status="active",
        )

        response = self.client.get(f"/api/v1/auth/admin/users/employee-code/lookup/?user_id={user.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], user.pk)
        self.assertEqual(response.data["full_name"], "ID Lookup User")

    def test_location_options_endpoint_returns_country_state_district_data(self) -> None:
        country_response = self.client.get("/api/v1/auth/admin/users/location-options/")
        self.assertEqual(country_response.status_code, 200)
        self.assertIn("India", country_response.data["countries"])

        state_response = self.client.get("/api/v1/auth/admin/users/location-options/?country=India")
        self.assertEqual(state_response.status_code, 200)
        self.assertIn("Assam", state_response.data["states"])

        district_response = self.client.get("/api/v1/auth/admin/users/location-options/?country=India&state=Assam")
        self.assertEqual(district_response.status_code, 200)
        self.assertTrue(len(district_response.data["districts"]) > 0)

    def test_user_bulk_action_export_uses_export_permission_not_update(self) -> None:
        export_user = User.objects.create_user(
            phone_number="9000000417",
            email="export-only-warehouse@example.com",
            password="testpass123",
            role="warehouse_operator",
            approval_status="approved",
            account_status="active",
        )
        target_user = User.objects.create_user(
            phone_number="9000000418",
            email="bulk-export-target@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )
        self.client.force_authenticate(user=export_user)

        response = self.client.post(
            "/api/v1/auth/admin/users/bulk-actions/",
            {"action": "export", "user_ids": [target_user.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.ms-excel")
        self.assertIn("bulk-export-target@example.com", response.content.decode())

    def test_admin_user_lock_toggle_rejects_unknown_action(self) -> None:
        target_user = User.objects.create_user(
            phone_number="9000000419",
            email="lock-toggle-target@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
            account_locked=True,
            failed_login_attempts=3,
        )

        response = self.client.post(f"/api/v1/auth/admin/users/{target_user.pk}/reopen/")

        target_user.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Unsupported lock action.")
        self.assertTrue(target_user.account_locked)
        self.assertEqual(target_user.failed_login_attempts, 3)

    @override_settings(BACKEND_BASE_URL="http://testserver", DEFAULT_FROM_EMAIL="security@example.com")
    def test_admin_reset_password_endpoint_sends_reset_link_instead_of_plaintext_password(self) -> None:
        target_user = User.objects.create_user(
            phone_number="9000000499",
            email="reset-target@example.com",
            password="testpass123",
            role="support_agent",
            approval_status="approved",
            account_status="active",
        )

        response = self.client.post(f"/api/v1/auth/admin/users/{target_user.pk}/reset-password/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reset_link_sent"], True)
        self.assertNotIn("temporary_password", response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset/", mail.outbox[0].body)

    @override_settings(DEBUG=True, EXPOSE_DEBUG_OTP_CODE=False)
    def test_send_otp_does_not_expose_code_without_explicit_setting(self) -> None:
        response = self.client.post(
            "/api/v1/auth/send-otp/",
            {"phone_number": "9000000501", "purpose": "login"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("otp_code", response.data)

    def test_user_management_form_generates_employee_code_in_create_mode(self) -> None:
        form = UserManagementForm(
            data={
                "employee_code": "",
                "username": "ops.user",
                "full_name": "Ops User",
                "type_of_user": "",
                "role": "operations_manager",
                "department": "",
                "designation": "",
                "email": "ops-user@example.com",
                "phone_number": "9000000403",
                "country": "India",
                "state": "Assam",
                "district": "Abhayapuri",
                "address": "Operations HQ",
                "account_status": "active",
                "remarks": "Created from test flow.",
                "temporary_password": "tempPass123",
            },
            is_create=True,
            current_actor=self.admin_user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(user.employee_code.startswith("OPS-"))
        self.assertEqual(len(user.employee_code.split("-")[1]), 8)
        self.assertEqual(user.type_of_user, "employee")
        self.assertEqual(user.department, "Operations")
        self.assertEqual(user.designation, "Operations Manager")

    def test_user_management_form_generates_username_in_create_mode_when_blank(self) -> None:
        form = UserManagementForm(
            data={
                "employee_code": "",
                "username": "",
                "full_name": "Auto Username User",
                "type_of_user": "",
                "role": "operations_manager",
                "department": "",
                "designation": "",
                "email": "auto-username-user@example.com",
                "phone_number": "9000000415",
                "country": "India",
                "state": "Assam",
                "district": "Abhayapuri",
                "address": "Operations HQ",
                "account_status": "active",
                "remarks": "Auto username test.",
                "temporary_password": "tempPass123",
            },
            is_create=True,
            current_actor=self.admin_user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.username, "auto.username")

    def test_user_management_form_maps_department_and_designation_from_role(self) -> None:
        form = UserManagementForm(
            data={
                "employee_code": "",
                "username": "security.user",
                "full_name": "Security User",
                "type_of_user": "",
                "role": "security_admin",
                "department": "",
                "designation": "",
                "email": "security-user@example.com",
                "phone_number": "9000000404",
                "country": "India",
                "state": "Assam",
                "district": "Abhayapuri",
                "address": "Security Desk",
                "account_status": "active",
                "remarks": "Role-mapped values.",
                "temporary_password": "tempPass123",
            },
            is_create=True,
            current_actor=self.admin_user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["type_of_user"], "system")
        self.assertEqual(form.cleaned_data["department"], "IT Security")
        self.assertEqual(form.cleaned_data["designation"], "Security Administrator")


class WarehouseDashboardTests(TestCase):
    def test_warehouse_dashboard_route_renders_for_warehouse_operator(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000999",
            email="warehouse-dashboard@example.com",
            password="testpass123",
            role="warehouse_operator",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/warehouse/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Warehouse Dashboard")


class DeliveryDashboardTests(TestCase):
    def test_delivery_dashboard_route_renders_for_delivery_agent(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000998",
            email="delivery-dashboard@example.com",
            password="testpass123",
            role="delivery_agent",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/delivery/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delivery Dashboard")


class SupportDashboardTests(TestCase):
    def test_support_dashboard_route_renders_for_support_agent(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000997",
            email="support-dashboard@example.com",
            password="testpass123",
            role="support_agent",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/support/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Support Dashboard")


class FinanceDashboardTests(TestCase):
    def test_finance_dashboard_route_renders_for_finance_role(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000996",
            email="finance-dashboard@example.com",
            password="testpass123",
            role="finance",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/finance/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finance Dashboard")


class SecurityDashboardTests(TestCase):
    def test_security_dashboard_route_renders_for_security_admin(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000995",
            email="security-dashboard@example.com",
            password="testpass123",
            role="security_admin",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/security/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Security Dashboard")


class DoctorDashboardTests(TestCase):
    def test_doctor_dashboard_route_renders_for_doctor_role(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000994",
            email="doctor-dashboard@example.com",
            password="testpass123",
            role="doctor",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/doctor/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Doctor Dashboard")


class OperationsDashboardTests(TestCase):
    def test_operations_dashboard_route_renders_for_operations_manager(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000993",
            email="operations-dashboard@example.com",
            password="testpass123",
            role="operations_manager",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/operations/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations Dashboard")


class CatalogDashboardTests(TestCase):
    def test_catalog_dashboard_route_renders_for_catalog_manager(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000992",
            email="catalog-dashboard@example.com",
            password="testpass123",
            role="catalog_manager",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/catalog/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catalog Dashboard")


class ProcurementDashboardTests(TestCase):
    def test_procurement_dashboard_route_renders_for_procurement_manager(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000991",
            email="procurement-dashboard@example.com",
            password="testpass123",
            role="procurement_manager",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/procurement/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Procurement Dashboard")


class MarketingDashboardTests(TestCase):
    def test_marketing_dashboard_route_renders_for_marketing_manager(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000990",
            email="marketing-dashboard@example.com",
            password="testpass123",
            role="marketing_manager",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/marketing/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marketing Dashboard")


class ComplianceDashboardTests(TestCase):
    def test_compliance_dashboard_route_renders_for_compliance_officer(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000989",
            email="compliance-dashboard@example.com",
            password="testpass123",
            role="compliance_officer",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/compliance/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Compliance Dashboard")


class AuditorDashboardTests(TestCase):
    def test_auditor_dashboard_route_renders_for_auditor(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000988",
            email="auditor-dashboard@example.com",
            password="testpass123",
            role="auditor",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/auditor/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auditor Dashboard")


class ViewerDashboardTests(TestCase):
    def test_viewer_dashboard_route_renders_for_viewer(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000987",
            email="viewer-dashboard@example.com",
            password="testpass123",
            role="viewer",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/viewer/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Viewer Dashboard")

    def test_viewer_dashboard_route_respects_matrix_dashboard_access(self) -> None:
        user = User.objects.create_user(
            phone_number="9000001987",
            email="viewer-dashboard-denied@example.com",
            password="testpass123",
            role="viewer",
            account_status="active",
            approval_status="approved",
        )
        ensure_role_permission_matrices()
        matrix = RolePermissionMatrix.objects.get(role="viewer")
        matrix.matrix_permissions["core_access.dashboard_access"] = "denied"
        matrix.save(update_fields=["matrix_permissions", "updated_at"])

        client = Client()
        client.force_login(user)

        response = client.get("/viewer/dashboard/")

        self.assertEqual(response.status_code, 403)


class VendorStaffDashboardTests(TestCase):
    def test_vendor_staff_dashboard_route_renders_for_vendor_staff(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000986",
            email="vendor-staff-dashboard@example.com",
            password="testpass123",
            role="vendor_staff",
            account_status="active",
            approval_status="approved",
        )
        client = Client()
        client.force_login(user)

        response = client.get("/vendor-staff/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vendor Staff Dashboard")


class PermissionMatrixSectionTests(TestCase):
    def setUp(self) -> None:
        self.super_admin = User.objects.create_user(
            phone_number="9000000985",
            email="permission-matrix-super-admin@example.com",
            password="testpass123",
            role="super_admin",
            account_status="active",
            approval_status="approved",
            is_staff=True,
            is_superuser=True,
        )
        self.client = Client()
        self.client.force_login(self.super_admin)

    def test_permission_matrix_page_renders(self) -> None:
        response = self.client.get(reverse("super-admin-section", kwargs={"section_slug": "roles-permissions"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission Matrix")
        self.assertContains(response, "Core Access Matrix")

    def test_permission_matrix_save_updates_matrix_and_live_user_flags(self) -> None:
        from .views import ensure_role_permission_matrices

        ensure_role_permission_matrices()

        response = self.client.post(
            reverse("super-admin-section", kwargs={"section_slug": "roles-permissions"}),
            {
                "permission_action": "save",
                "perm__support_agent__user_management__create_users": "1",
                "perm__viewer__reports__view_reports": "1",
                "scope__viewer__reports__view_reports": "1",
            },
            follow=True,
        )

        support_matrix = RolePermissionMatrix.objects.get(role="support_agent")
        matrix = RolePermissionMatrix.objects.get(role="viewer")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(support_matrix.matrix_permissions["user_management.create_users"], "allowed")
        self.assertTrue(support_matrix.user_create)
        self.assertEqual(matrix.matrix_permissions["reports.view_reports"], "limited")
        self.assertFalse(matrix.user_read)

    def test_permission_matrix_ajax_save_returns_json_and_persists(self) -> None:
        from .views import ensure_role_permission_matrices

        ensure_role_permission_matrices()

        response = self.client.post(
            reverse("super-admin-section", kwargs={"section_slug": "roles-permissions"}),
            {
                "permission_action": "save",
                "matrix_state__viewer__reports__view_reports": "allowed",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        matrix = RolePermissionMatrix.objects.get(role="viewer")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "message": "Permission matrix updated successfully."})
        self.assertEqual(matrix.matrix_permissions["reports.view_reports"], "allowed")


class SuperAdminAppointmentsSectionTests(TestCase):
    def setUp(self) -> None:
        self.super_admin = User.objects.create_user(
            phone_number="9000000975",
            email="appointments-super-admin@example.com",
            password="testpass123",
            role="super_admin",
            account_status="active",
            approval_status="approved",
            is_staff=True,
            is_superuser=True,
        )
        self.reviewer = User.objects.create_user(
            phone_number="9000000976",
            email="appointments-reviewer@example.com",
            password="testpass123",
            full_name="Reviewer One",
            role="admin",
            account_status="active",
            approval_status="approved",
            is_staff=True,
            approval_specialty="vendor",
        )
        self.customer = User.objects.create_user(
            phone_number="9000000977",
            email="appointments-customer@example.com",
            password="testpass123",
            full_name="Patient One",
            role="customer",
            account_status="active",
            approval_status="approved",
        )
        Prescription.objects.create(
            user=self.customer,
            reference_code="RX-APPT-001",
            patient_name="Patient One",
            doctor_name="Dr. Sharma",
            uploaded_file_name="rx-1.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx-1.png",
            uploaded_file_size_bytes=128,
            status="clarification_required",
            review_priority="urgent",
        )
        Prescription.objects.create(
            user=self.customer,
            reference_code="RX-APPT-002",
            patient_name="Patient Two",
            doctor_name="Dr. Rao",
            uploaded_file_name="rx-2.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx-2.png",
            uploaded_file_size_bytes=256,
            status="pending_review",
        )
        self.client = Client()
        self.client.force_login(self.super_admin)

    def test_appointments_section_renders_live_coordination_content(self) -> None:
        response = self.client.get(reverse("super-admin-section", kwargs={"section_slug": "appointments"}))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Clinical coordination queue", content)
        self.assertIn("Doctor-linked follow-up cases", content)
        self.assertIn("Dr. Sharma", content)
        self.assertIn("Reviewer coverage", content)
        self.assertNotIn("No appointment module is wired yet", content)


class AuthSecurityTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_verify_otp_blocks_after_max_attempts(self) -> None:
        OTPRequest.objects.create(
            phone_number="9000000099",
            purpose="login",
            otp_code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            attempt_count=settings.OTP_MAX_ATTEMPTS,
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone_number": "9000000099",
                "otp_code": "123456",
                "purpose": "login",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn("Too many invalid OTP attempts", response.data["detail"])

    def test_security_headers_are_attached(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-API-Version"], "v1")
        self.assertIn("breaking changes require a new versioned path", response.headers["X-API-Deprecation-Policy"])
        self.assertIn("deprecation_policy", response.json())
        self.assertIn("compliance", response.json())

    def test_api_root_exposes_compliance_metadata(self) -> None:
        response = self.client.get("/")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["compliance"]["company_name"], "TrueCare Health Services Private Limited")
        self.assertIn("drug_license_number", payload["compliance"])
        self.assertIn("pharmacist_registration_number", payload["compliance"])

    def test_request_logging_middleware_emits_structured_log(self) -> None:
        with self.assertLogs("rakeshmed.request", level="INFO") as captured:
            response = self.client.get("/", HTTP_X_REQUEST_ID="test-request-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "test-request-id")
        self.assertIn("X-Response-Time-Ms", response.headers)
        self.assertTrue(
            any(
                "request.complete method=GET path=/ status=200" in line
                and "request_id=test-request-id" in line
                and "bytes=" in line
                and "user_role=anonymous" in line
                for line in captured.output
            )
        )

    def test_security_headers_include_permissions_policy(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("camera=()", response.headers["Permissions-Policy"])

    def test_logout_revokes_auth_token(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000010",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post("/api/v1/auth/logout/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_token_auth_rejects_password_reset_required_user(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000018",
            password="testpass123",
            email="token-reset@example.com",
            role="admin",
            approval_status="approved",
            account_status="active",
            force_password_reset=True,
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_expired_token_is_rejected(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000011",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        token = Token.objects.create(user=user)
        token.created = timezone.now() - timezone.timedelta(seconds=settings.AUTH_TOKEN_TTL_SECONDS + 5)
        token.save(update_fields=["created"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get("/api/v1/auth/me/")

        self.assertIn(response.status_code, {401, 403})
        self.assertIn("Session expired", response.data["detail"])
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_verify_otp_response_includes_session_expiry(self) -> None:
        OTPRequest.objects.create(
            phone_number="9000000012",
            purpose="login",
            otp_code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone_number": "9000000012",
                "otp_code": "123456",
                "purpose": "login",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("expires_at", response.data)
        self.assertTrue(response.data["user"]["session_expires_at"])

    def test_verify_otp_sets_created_by_to_self_for_new_user(self) -> None:
        OTPRequest.objects.create(
            phone_number="9000000013",
            purpose="login",
            otp_code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone_number": "9000000013",
                "otp_code": "123456",
                "purpose": "login",
                "full_name": "Self Created User",
                "email": "self-created@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(phone_number="9000000013")
        self.assertEqual(user.created_by_id, user.id)
        self.assertEqual(user.updated_by_id, user.id)

    def test_verify_otp_does_not_overwrite_existing_user_identity_fields(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000014",
            email="original@example.com",
            full_name="Original Customer",
            password="testpass123",
            role="customer",
            type_of_user="customer",
            approval_status="approved",
            account_status="active",
            is_phone_verified=False,
        )
        OTPRequest.objects.create(
            phone_number=user.phone_number,
            purpose="login",
            otp_code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone_number": user.phone_number,
                "otp_code": "123456",
                "purpose": "login",
                "full_name": "Injected Name",
                "email": "attacker@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, "original@example.com")
        self.assertEqual(user.full_name, "Original Customer")
        self.assertTrue(user.is_phone_verified)

    def test_verify_otp_rejects_non_customer_accounts(self) -> None:
        staff_user = User.objects.create_user(
            phone_number="9000000015",
            email="admin-otp@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        OTPRequest.objects.create(
            phone_number=staff_user.phone_number,
            purpose="login",
            otp_code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone_number": staff_user.phone_number,
                "otp_code": "123456",
                "purpose": "login",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("customer accounts", response.data["detail"])
        self.assertFalse(Token.objects.filter(user=staff_user).exists())

    def test_verify_otp_returns_validation_error_for_duplicate_email(self) -> None:
        User.objects.create_user(
            phone_number="9000000016",
            email="existing-otp@example.com",
            password="testpass123",
            role="customer",
            type_of_user="customer",
            approval_status="approved",
            account_status="active",
        )
        OTPRequest.objects.create(
            phone_number="9000000017",
            purpose="login",
            otp_code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        response = self.client.post(
            "/api/v1/auth/verify-otp/",
            {
                "phone_number": "9000000017",
                "otp_code": "123456",
                "purpose": "login",
                "email": "existing-otp@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_profile_update_returns_validation_error_for_duplicate_email(self) -> None:
        User.objects.create_user(
            phone_number="9000000020",
            email="taken-profile@example.com",
            password="testpass123",
            role="customer",
            type_of_user="customer",
            approval_status="approved",
            account_status="active",
        )
        user = User.objects.create_user(
            phone_number="9000000021",
            email="profile-owner@example.com",
            password="testpass123",
            role="customer",
            type_of_user="customer",
            approval_status="approved",
            account_status="active",
            is_phone_verified=True,
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.patch(
            "/api/v1/auth/me/",
            {"email": "taken-profile@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)


class PortalAuthFlowTests(TestCase):
    def setUp(self) -> None:
        self.client = Client(HTTP_HOST="localhost")

    def test_customer_registration_is_not_available_on_partner_portal(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Customer One",
                "email": "customer@example.com",
                "phone_number": "9000000101",
                "role": "customer",
                "password1": "testpass123",
                "password2": "testpass123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="customer@example.com").exists())
        self.assertIn("Select a valid choice", response.content.decode())

    def test_vendor_registration_requires_approval(self) -> None:
        User.objects.create_user(
            phone_number="9000000991",
            email="admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )

        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Vendor One",
                "email": "vendor@example.com",
                "phone_number": "9000000102",
                "role": "vendor",
                "business_name": "Vendor One Store",
                "vendor_license_number": "DL-99881",
                "vendor_license_document": SimpleUploadedFile("vendor-proof.pdf", b"vendor-proof", content_type="application/pdf"),
                "password1": "testpass123",
                "password2": "testpass123",
            },
            follow=True,
        )

        user = User.objects.get(email="vendor@example.com")
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(user.approval_status, "pending")
        self.assertEqual(user.business_name, "Vendor One Store")
        self.assertEqual(user.vendor_license_number, "DL-99881")
        self.assertIn("approval-documents/vendor/", user.vendor_license_document.name)
        self.assertIn("vendor-proof", user.vendor_license_document.name)
        self.assertEqual(user.vendor_license_document_status, "pending")
        self.assertTrue(Notification.objects.filter(title__icontains="approval required").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Approval required", mail.outbox[0].subject)
        self.assertEqual(user.created_by_id, user.id)
        self.assertEqual(user.updated_by_id, user.id)

    def test_pending_vendor_cannot_log_in(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000103",
            email="pending-vendor@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
        )

        response = self.client.post(
            reverse("login"),
            {"email": user.email, "password": "testpass123"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("awaiting admin approval", response.content.decode())

    def test_force_password_reset_user_cannot_complete_portal_login(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000104",
            email="forced-reset@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            force_password_reset=True,
        )

        response = self.client.post(reverse("login"), {"email": user.email, "password": "testpass123"}, follow=True)

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset/", mail.outbox[0].body)

    def test_password_reset_confirm_clears_force_reset_flag(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000105",
            email="confirm-reset@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            force_password_reset=True,
        )
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        start_response = self.client.get(reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}))

        response = self.client.post(
            start_response.url,
            {"new_password1": "NewTestPass123!", "new_password2": "NewTestPass123!"},
            follow=True,
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.assertFalse(user.force_password_reset)
        self.assertIsNotNone(user.password_last_changed_at)

    def test_pharmacist_registration_requires_registration_number(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Pharmacist One",
                "email": "pharmacist-one@example.com",
                "phone_number": "9000000106",
                "role": "pharmacist",
                "pharmacist_registration_document": SimpleUploadedFile("pharmacist-proof.pdf", b"pharmacist-proof", content_type="application/pdf"),
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("registration number is required", response.content.decode().lower())

    def test_pharmacist_registration_saves_proof_document(self) -> None:
        User.objects.create_user(
            phone_number="9000000992",
            email="admin2@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )

        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Pharmacist Two",
                "email": "pharmacist-two@example.com",
                "phone_number": "9000000107",
                "role": "pharmacist",
                "pharmacist_registration_number": "PHARM-4432",
                "pharmacist_registration_document": SimpleUploadedFile("pharmacist-proof.pdf", b"pharmacist-proof", content_type="application/pdf"),
                "password1": "testpass123",
                "password2": "testpass123",
            },
            follow=True,
        )

        user = User.objects.get(email="pharmacist-two@example.com")
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(user.approval_status, "pending")
        self.assertEqual(user.pharmacist_registration_number, "PHARM-4432")
        self.assertIn("approval-documents/pharmacist/", user.pharmacist_registration_document.name)
        self.assertIn("pharmacist-proof", user.pharmacist_registration_document.name)
        self.assertEqual(user.pharmacist_registration_document_status, "pending")

    def test_vendor_registration_rejects_invalid_document_extension(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Vendor Bad File",
                "email": "vendor-bad@example.com",
                "phone_number": "9000000108",
                "role": "vendor",
                "business_name": "Bad Vendor",
                "vendor_license_number": "DL-00001",
                "vendor_license_document": SimpleUploadedFile("vendor-proof.exe", b"bad-file", content_type="application/octet-stream"),
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("must be one of", response.content.decode().lower())

    def test_vendor_registration_rejects_large_document(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Vendor Large File",
                "email": "vendor-large@example.com",
                "phone_number": "9000000109",
                "role": "vendor",
                "business_name": "Large Vendor",
                "vendor_license_number": "DL-00002",
                "vendor_license_document": SimpleUploadedFile("vendor-proof.pdf", b"x" * (1024 * 1024 + 1), content_type="application/pdf"),
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("must be 1mb or smaller", response.content.decode().lower())

    def test_customer_login_redirects_to_frontend_account_app(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000104",
            email="approved-customer@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )

        response = self.client.post(
            reverse("login"),
            {"email": user.email, "password": "testpass123"},
        )

        self.assertRedirects(response, "http://localhost:3000/account", fetch_redirect_response=False)

    def test_mfa_enabled_user_is_redirected_to_challenge_before_login(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000110",
            email="mfa-user@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            mfa_enabled=True,
        )

        response = self.client.post(
            reverse("login"),
            {"email": user.email, "password": "testpass123"},
        )

        self.assertRedirects(response, reverse("mfa_challenge"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.session["portal_mfa_user_id"], user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verification code", mail.outbox[0].subject.lower())

    def test_mfa_challenge_completes_login_and_redirects_by_role(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000111",
            email="mfa-complete@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            mfa_enabled=True,
        )

        self.client.post(reverse("login"), {"email": user.email, "password": "testpass123"})
        code = self.client.session["portal_mfa_code"]

        response = self.client.post(reverse("mfa_challenge"), {"code": code})

        self.assertRedirects(response, "/admin/dashboard/", fetch_redirect_response=False)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(user.pk))
        self.assertNotIn("portal_mfa_code", self.client.session)

    def test_mfa_challenge_resend_sends_fresh_code(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000112",
            email="mfa-resend@example.com",
            password="testpass123",
            role="super_admin",
            approval_status="approved",
            account_status="active",
            mfa_enabled=True,
        )

        self.client.post(reverse("login"), {"email": user.email, "password": "testpass123"})
        session = self.client.session
        session["portal_mfa_resend_after"] = (timezone.now() - timezone.timedelta(seconds=1)).isoformat()
        session.save()
        old_code = self.client.session["portal_mfa_code"]

        response = self.client.post(reverse("mfa_challenge"), {"action": "resend"})

        self.assertRedirects(response, reverse("mfa_challenge"), fetch_redirect_response=False)
        self.assertNotEqual(self.client.session["portal_mfa_code"], old_code)
        self.assertEqual(len(mail.outbox), 2)

    def test_role_protected_dashboard_returns_403_for_wrong_role(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000105",
            email="customer2@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("vendor-dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.content.decode())


class ApprovalNotificationTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

    def test_notify_user_of_approval_decision_sends_email_and_notification(self) -> None:
        user = User.objects.create_user(
            phone_number="9000000201",
            email="pharmacist@example.com",
            password="testpass123",
            role="pharmacist",
            approval_status="approved",
            account_status="active",
        )

        notify_user_of_approval_decision(user, previous_status="pending")

        self.assertTrue(Notification.objects.filter(user=user, title__icontains="approved").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("approved", mail.outbox[0].subject.lower())

    def test_notify_overdue_approval_escalation_notifies_assignee_and_super_admin(self) -> None:
        assigned_admin = User.objects.create_user(
            phone_number="9000000203",
            email="assigned-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        super_admin = User.objects.create_user(
            phone_number="9000000204",
            email="super-admin@example.com",
            password="testpass123",
            role="super_admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
            is_superuser=True,
        )
        user = User.objects.create_user(
            phone_number="9000000205",
            email="overdue-vendor@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=assigned_admin,
            approval_assigned_at=timezone.now() - timezone.timedelta(hours=4),
            approval_due_at=timezone.now() - timezone.timedelta(hours=1),
        )

        escalated = notify_overdue_approval_escalation(user, actor=assigned_admin)

        user.refresh_from_db()
        self.assertTrue(escalated)
        self.assertIsNotNone(user.approval_last_escalated_at)
        self.assertTrue(Notification.objects.filter(user=assigned_admin, title__icontains="overdue").exists())
        self.assertTrue(Notification.objects.filter(user=super_admin, title__icontains="overdue").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Overdue approval escalation", mail.outbox[0].subject)
        self.assertTrue(AuditLog.objects.filter(entity_id=str(user.pk), event_type="approval_sla_escalated").exists())

    def test_notify_overdue_approval_escalation_respects_repeat_window(self) -> None:
        admin_user = User.objects.create_user(
            phone_number="9000000206",
            email="admin-repeat@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        user = User.objects.create_user(
            phone_number="9000000207",
            email="repeat-vendor@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=admin_user,
            approval_assigned_at=timezone.now() - timezone.timedelta(hours=4),
            approval_due_at=timezone.now() - timezone.timedelta(hours=1),
            approval_last_escalated_at=timezone.now() - timezone.timedelta(hours=1),
        )

        escalated = notify_overdue_approval_escalation(user, actor=admin_user)

        self.assertFalse(escalated)
        self.assertFalse(Notification.objects.filter(user=admin_user, title__icontains="overdue").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_run_overdue_approval_escalations_processes_only_due_requests(self) -> None:
        admin_user = User.objects.create_user(
            phone_number="9000000208",
            email="admin-scan@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        overdue_user = User.objects.create_user(
            phone_number="9000000209",
            email="scan-overdue@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=admin_user,
            approval_assigned_at=timezone.now() - timezone.timedelta(hours=3),
            approval_due_at=timezone.now() - timezone.timedelta(minutes=30),
        )
        User.objects.create_user(
            phone_number="9000000210",
            email="scan-ontrack@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=admin_user,
            approval_assigned_at=timezone.now() - timezone.timedelta(hours=1),
            approval_due_at=timezone.now() + timezone.timedelta(hours=2),
        )

        escalated_count = run_overdue_approval_escalations()

        overdue_user.refresh_from_db()
        self.assertEqual(escalated_count, 1)
        self.assertIsNotNone(overdue_user.approval_last_escalated_at)
        self.assertTrue(Notification.objects.filter(user=admin_user, meta__user_id=overdue_user.pk).exists())

    @override_settings(APPROVAL_ESCALATION_REPEAT_HOURS=0)
    def test_escalate_overdue_approvals_management_command_reports_count(self) -> None:
        admin_user = User.objects.create_user(
            phone_number="9000000211",
            email="admin-command@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        User.objects.create_user(
            phone_number="9000000212",
            email="command-overdue@example.com",
            password="testpass123",
            role="pharmacist",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=admin_user,
            approval_assigned_at=timezone.now() - timezone.timedelta(hours=2),
            approval_due_at=timezone.now() - timezone.timedelta(minutes=15),
        )

        stdout = StringIO()
        call_command("escalate_overdue_approvals", stdout=stdout)
        output = stdout.getvalue()
        self.assertIn("Escalated 1 overdue approval(s).", output)

    def test_admin_action_approve_selected_users_notifies_user(self) -> None:
        approver = User.objects.create_user(
            phone_number="9000000202",
            email="super-admin@example.com",
            password="testpass123",
            role="super_admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
            is_superuser=True,
        )
        pending_user = User.objects.create_user(
            phone_number="9000000203",
            email="vendor2@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
        )
        request = self.factory.post("/admin/users/user/")
        request.user = approver
        request._messages = []

        admin_instance = UserAdmin(User, self.admin_site)
        admin_instance.message_user = lambda *args, **kwargs: None

        admin_instance.approve_selected_users(request, User.objects.filter(pk=pending_user.pk))
        pending_user.refresh_from_db()

        self.assertEqual(pending_user.approval_status, "approved")
        self.assertTrue(Notification.objects.filter(user=pending_user, title__icontains="approved").exists())
        self.assertEqual(len(mail.outbox), 1)


class ApprovalQueuePageTests(TestCase):
    def setUp(self) -> None:
        self.client = Client(HTTP_HOST="localhost")
        self.admin_user = User.objects.create_user(
            phone_number="9000000301",
            email="queue-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.pending_vendor = User.objects.create_user(
            phone_number="9000000302",
            email="queue-vendor@example.com",
            password="testpass123",
            role="vendor",
            business_name="Queue Vendor Store",
            vendor_license_number="QUEUE-DL-100",
            approval_status="pending",
            account_status="active",
        )
        self.pending_vendor.vendor_license_document.save(
            "queue-vendor-proof.pdf",
            SimpleUploadedFile("queue-vendor-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.super_admin = User.objects.create_user(
            phone_number="9000000305",
            email="queue-super-admin@example.com",
            password="testpass123",
            role="super_admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_dashboard_shows_approval_queue_entry(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("Approval Queue", response.content.decode())
        self.assertIn("queue-vendor@example.com", response.content.decode())

    def test_admin_dashboard_shows_approval_presets(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Approval Presets", content)
        self.assertIn("My queue", content)
        self.assertIn("My overdue", content)
        self.assertIn("Unassigned", content)

    def test_admin_dashboard_my_queue_preset_targets_current_reviewer(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"{reverse('admin-approval-queue')}?assigned_to={self.admin_user.pk}", content)

    def test_admin_dashboard_shows_approval_preset_kpis(self) -> None:
        self.pending_vendor.approval_assigned_to = self.admin_user
        self.pending_vendor.approval_assigned_at = timezone.now()
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.save(update_fields=["approval_assigned_to", "approval_assigned_at", "approval_due_at", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("My Queue", content)
        self.assertIn("My Overdue", content)
        self.assertIn("Unassigned Approvals", content)
        self.assertIn(
            f"{reverse('admin-approval-queue')}?assigned_to={self.admin_user.pk}&amp;overdue=1",
            content,
        )

    def test_admin_dashboard_shows_extended_approval_drilldowns(self) -> None:
        self.pending_vendor.vendor_license_document_status = "rejected"
        self.pending_vendor.save(update_fields=["vendor_license_document_status", "updated_at"])
        User.objects.create_user(
            phone_number="9000000399",
            email="recent-approved@example.com",
            password="testpass123",
            role="pharmacist",
            approval_status="approved",
            account_status="active",
            approval_reviewed_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Document Rejected", content)
        self.assertIn("Recently Approved", content)
        self.assertIn(f"{reverse('admin-approval-queue')}?document_rejected=1", content)
        self.assertIn(f"{reverse('admin:users_user_changelist')}?approval_status__exact=approved", content)

    def test_admin_dashboard_shows_overdue_approval_snapshot(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.approval_assigned_to = self.admin_user
        self.pending_vendor.approval_assigned_at = timezone.now() - timezone.timedelta(hours=1)
        self.pending_vendor.save(update_fields=["approval_due_at", "approval_assigned_to", "approval_assigned_at", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Overdue Approval Requests", content)
        self.assertIn("Overdue By Owner", content)
        self.assertIn("Due", content)

    def test_admin_dashboard_shows_reviewer_workload_panel(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000388",
            email="queue-workload-admin@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.pending_vendor.approval_assigned_to = other_admin
        self.pending_vendor.approval_assigned_at = timezone.now()
        self.pending_vendor.save(update_fields=["approval_assigned_to", "approval_assigned_at", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Reviewer Workload", content)
        self.assertIn("queue-workload-admin@example.com", content)
        self.assertIn("Vendor Reviews", content)
        self.assertIn("Available", content)

    def test_admin_dashboard_links_to_reviewer_schedules(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse("admin-reviewer-schedules"), content)
        self.assertIn("Manage Reviewer Schedules", content)

    def test_approval_queue_shows_audit_history_timeline(self) -> None:
        AuditLog.objects.create(
            actor=self.pending_vendor,
            actor_label=str(self.pending_vendor),
            event_type="approval_request_created",
            entity_type="user",
            entity_id=str(self.pending_vendor.pk),
            message="Approval request created for queue-vendor@example.com.",
            meta={"role": "vendor"},
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("Approval request created for queue-vendor@example.com.", response.content.decode())

    def test_approval_queue_shows_saved_presets(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("My queue", content)
        self.assertIn("My overdue", content)
        self.assertIn("Unassigned", content)
        self.assertIn("Escalated", content)

    def test_reviewer_schedules_page_renders(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-reviewer-schedules"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Reviewer Schedules", content)
        self.assertIn("Save reviewer schedule", content)
        self.assertIn("queue-admin@example.com", content)

    def test_reviewer_schedules_page_updates_reviewer_settings(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-reviewer-schedules"),
            {
                "reviewer_id": str(self.admin_user.pk),
                "approval_specialty": "vendor",
                "approval_available_for_assignment": "on",
                "approval_unavailable_until": "",
                "approval_shift_start_hour": "10",
                "approval_shift_end_hour": "19",
                "approval_shift_weekdays": ["0", "1", "2"],
                "approval_leave_dates": "2026-04-30,2026-05-01",
            },
            follow=True,
        )

        self.admin_user.refresh_from_db()
        self.assertRedirects(response, reverse("admin-reviewer-schedules"))
        self.assertEqual(self.admin_user.approval_specialty, "vendor")
        self.assertEqual(self.admin_user.approval_shift_start_hour, 10)
        self.assertEqual(self.admin_user.approval_shift_end_hour, 19)
        self.assertEqual(self.admin_user.approval_shift_weekdays, "0,1,2")
        self.assertEqual(self.admin_user.approval_leave_dates, "2026-04-30,2026-05-01")
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="user",
                entity_id=str(self.admin_user.pk),
                event_type="reviewer_schedule_updated",
            ).exists()
        )

    def test_reviewer_schedules_page_blocks_non_admin(self) -> None:
        customer_user = User.objects.create_user(
            phone_number="9000000390",
            email="schedule-customer@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )
        self.client.force_login(customer_user)

        response = self.client.get(reverse("admin-reviewer-schedules"))

        self.assertEqual(response.status_code, 302)

    def test_my_queue_preset_filter_returns_only_assigned_items(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000322",
            email="queue-preset-other-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.pending_vendor.approval_assigned_to = self.admin_user
        self.pending_vendor.approval_assigned_at = timezone.now()
        self.pending_vendor.save(update_fields=["approval_assigned_to", "approval_assigned_at", "updated_at"])
        other_pending = User.objects.create_user(
            phone_number="9000000323",
            email="queue-preset-other-vendor@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=other_admin,
            approval_assigned_at=timezone.now(),
            business_name="Preset Other Store",
            vendor_license_number="PRESET-100",
        )
        other_pending.vendor_license_document.save(
            "queue-preset-other-proof.pdf",
            SimpleUploadedFile("queue-preset-other-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"), {"assigned_to": str(self.admin_user.pk)})

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-vendor@example.com", content)
        self.assertNotIn("queue-preset-other-vendor@example.com", content)

    def test_approval_queue_can_filter_by_assigned_reviewer(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000311",
            email="queue-other-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.pending_vendor.approval_assigned_to = self.admin_user
        self.pending_vendor.approval_assigned_at = timezone.now()
        self.pending_vendor.save(update_fields=["approval_assigned_to", "approval_assigned_at", "updated_at"])
        other_pending = User.objects.create_user(
            phone_number="9000000312",
            email="queue-other-vendor@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=other_admin,
            approval_assigned_at=timezone.now(),
            business_name="Other Store",
            vendor_license_number="OTHER-100",
        )
        other_pending.vendor_license_document.save(
            "queue-other-proof.pdf",
            SimpleUploadedFile("queue-other-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"), {"assigned_to": str(self.admin_user.pk)})

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-vendor@example.com", content)
        self.assertNotIn("queue-other-vendor@example.com", content)

    def test_approval_queue_can_filter_overdue_only(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.save(update_fields=["approval_due_at", "updated_at"])
        on_track_user = User.objects.create_user(
            phone_number="9000000313",
            email="queue-ontrack@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_due_at=timezone.now() + timezone.timedelta(hours=2),
            business_name="On Track Store",
            vendor_license_number="TRACK-100",
        )
        on_track_user.vendor_license_document.save(
            "queue-ontrack-proof.pdf",
            SimpleUploadedFile("queue-ontrack-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"), {"overdue": "1"})

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-vendor@example.com", content)
        self.assertNotIn("queue-ontrack@example.com", content)

    def test_approval_queue_can_filter_document_rejected_only(self) -> None:
        self.pending_vendor.vendor_license_document_status = "rejected"
        self.pending_vendor.save(update_fields=["vendor_license_document_status", "updated_at"])
        verified_user = User.objects.create_user(
            phone_number="9000000318",
            email="queue-verified@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            vendor_license_document_status="verified",
            business_name="Verified Store",
            vendor_license_number="VER-100",
        )
        verified_user.vendor_license_document.save(
            "queue-verified-proof.pdf",
            SimpleUploadedFile("queue-verified-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"), {"document_rejected": "1"})

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-vendor@example.com", content)
        self.assertNotIn("queue-verified@example.com", content)

    def test_approval_queue_can_filter_escalated_only(self) -> None:
        self.pending_vendor.approval_last_escalated_at = timezone.now() - timezone.timedelta(minutes=20)
        self.pending_vendor.save(update_fields=["approval_last_escalated_at", "updated_at"])
        non_escalated_user = User.objects.create_user(
            phone_number="9000000314",
            email="queue-not-escalated@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            business_name="No Escalation Store",
            vendor_license_number="NOESC-100",
        )
        non_escalated_user.vendor_license_document.save(
            "queue-not-escalated-proof.pdf",
            SimpleUploadedFile("queue-not-escalated-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"), {"escalated": "1"})

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-vendor@example.com", content)
        self.assertNotIn("queue-not-escalated@example.com", content)

    def test_approval_queue_shows_reviewer_workload_and_suggested_assignment(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000324",
            email="queue-suggested-admin@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        loaded_user = User.objects.create_user(
            phone_number="9000000325",
            email="queue-loaded@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=self.admin_user,
            approval_assigned_at=timezone.now(),
            business_name="Loaded Store",
            vendor_license_number="LOAD-100",
        )
        loaded_user.vendor_license_document.save(
            "queue-loaded-proof.pdf",
            SimpleUploadedFile("queue-loaded-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-suggested-admin@example.com", content)
        self.assertIn("Suggested reviewer: queue-suggested-admin@example.com (Vendor Reviews)", content)

    def test_approval_queue_shows_manual_reviewer_availability_labels(self) -> None:
        unavailable_admin = User.objects.create_user(
            phone_number="9000000325",
            email="queue-unavailable-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            approval_available_for_assignment=False,
            is_staff=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-unavailable-admin@example.com - Unavailable", content)

    def test_approval_queue_shows_off_shift_reviewer_label(self) -> None:
        off_shift_admin = User.objects.create_user(
            phone_number="9000000326",
            email="queue-offshift-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            approval_shift_start_hour=23,
            approval_shift_end_hour=23,
            is_staff=True,
        )
        off_shift_admin.approval_shift_start_hour = (timezone.localtime().hour + 2) % 24
        off_shift_admin.approval_shift_end_hour = (timezone.localtime().hour + 3) % 24
        off_shift_admin.save(update_fields=["approval_shift_start_hour", "approval_shift_end_hour", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-offshift-admin@example.com - Off shift", content)

    def test_approval_queue_shows_on_leave_reviewer_label(self) -> None:
        on_leave_admin = User.objects.create_user(
            phone_number="9000000327",
            email="queue-onleave-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            approval_leave_dates=timezone.localdate().isoformat(),
            is_staff=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-onleave-admin@example.com - On leave", content)

    def test_assign_suggested_uses_lowest_load_reviewer(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000326",
            email="queue-low-load-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        loaded_user = User.objects.create_user(
            phone_number="9000000327",
            email="queue-loaded-2@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=self.admin_user,
            approval_assigned_at=timezone.now(),
            business_name="Loaded Two Store",
            vendor_license_number="LOAD-200",
        )
        loaded_user.vendor_license_document.save(
            "queue-loaded-2-proof.pdf",
            SimpleUploadedFile("queue-loaded-2-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": str(self.pending_vendor.pk),
                "assignment_action": "assign_suggested",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, other_admin)

    def test_assign_suggested_prefers_matching_specialty(self) -> None:
        vendor_admin = User.objects.create_user(
            phone_number="9000000330",
            email="queue-vendor-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        pharmacist_admin = User.objects.create_user(
            phone_number="9000000331",
            email="queue-pharmacist-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="pharmacist",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        pharmacist_request = User.objects.create_user(
            phone_number="9000000332",
            email="queue-specialty-pharmacist@example.com",
            password="testpass123",
            role="pharmacist",
            approval_status="pending",
            account_status="active",
            pharmacist_registration_number="PHARM-SPECIAL-1",
        )
        pharmacist_request.pharmacist_registration_document.save(
            "queue-specialty-pharmacist-proof.pdf",
            SimpleUploadedFile("queue-specialty-pharmacist-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": str(pharmacist_request.pk),
                "assignment_action": "assign_suggested",
            },
            follow=True,
        )

        pharmacist_request.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(pharmacist_request.approval_assigned_to, pharmacist_admin)
        self.assertNotEqual(pharmacist_request.approval_assigned_to, vendor_admin)

    def test_assign_suggested_skips_unavailable_specialist(self) -> None:
        self.admin_user.approval_available_for_assignment = False
        self.admin_user.save(update_fields=["approval_available_for_assignment", "updated_at"])
        unavailable_vendor_admin = User.objects.create_user(
            phone_number="9000000336",
            email="queue-unavailable-vendor-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            approval_available_for_assignment=False,
            is_staff=True,
        )
        available_general_admin = User.objects.create_user(
            phone_number="9000000337",
            email="queue-available-general@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="all",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": str(self.pending_vendor.pk),
                "assignment_action": "assign_suggested",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, available_general_admin)
        self.assertNotEqual(self.pending_vendor.approval_assigned_to, unavailable_vendor_admin)

    def test_assign_suggested_skips_off_shift_specialist(self) -> None:
        self.admin_user.approval_available_for_assignment = False
        self.admin_user.save(update_fields=["approval_available_for_assignment", "updated_at"])
        off_shift_vendor_admin = User.objects.create_user(
            phone_number="9000000338",
            email="queue-offshift-vendor-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            approval_shift_start_hour=(timezone.localtime().hour + 2) % 24,
            approval_shift_end_hour=(timezone.localtime().hour + 3) % 24,
            is_staff=True,
        )
        available_general_admin = User.objects.create_user(
            phone_number="9000000339",
            email="queue-available-general-2@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="all",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": str(self.pending_vendor.pk),
                "assignment_action": "assign_suggested",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, available_general_admin)
        self.assertNotEqual(self.pending_vendor.approval_assigned_to, off_shift_vendor_admin)

    def test_assign_suggested_skips_on_leave_specialist(self) -> None:
        self.admin_user.approval_available_for_assignment = False
        self.admin_user.save(update_fields=["approval_available_for_assignment", "updated_at"])
        on_leave_vendor_admin = User.objects.create_user(
            phone_number="9000000340",
            email="queue-onleave-vendor-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            approval_leave_dates=timezone.localdate().isoformat(),
            is_staff=True,
        )
        available_general_admin = User.objects.create_user(
            phone_number="9000000341",
            email="queue-available-general-3@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="all",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": str(self.pending_vendor.pk),
                "assignment_action": "assign_suggested",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, available_general_admin)
        self.assertNotEqual(self.pending_vendor.approval_assigned_to, on_leave_vendor_admin)

    def test_bulk_assign_suggested_visible_balances_unassigned_queue(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000328",
            email="queue-bulk-suggested-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        second_unassigned = User.objects.create_user(
            phone_number="9000000329",
            email="queue-unassigned-two@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            business_name="Second Unassigned Store",
            vendor_license_number="UNASSIGNED-200",
        )
        second_unassigned.vendor_license_document.save(
            "queue-unassigned-two-proof.pdf",
            SimpleUploadedFile("queue-unassigned-two-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "bulk_action": "bulk_assign_suggested_visible",
                "filter_assigned_to": "unassigned",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        second_unassigned.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual({self.pending_vendor.approval_assigned_to, second_unassigned.approval_assigned_to}, {self.admin_user, other_admin})

    def test_bulk_assign_suggested_prefers_role_specialists(self) -> None:
        vendor_admin = User.objects.create_user(
            phone_number="9000000333",
            email="queue-bulk-vendor-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="vendor",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        pharmacist_admin = User.objects.create_user(
            phone_number="9000000334",
            email="queue-bulk-pharmacist-specialist@example.com",
            password="testpass123",
            role="admin",
            approval_specialty="pharmacist",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        pharmacist_request = User.objects.create_user(
            phone_number="9000000335",
            email="queue-bulk-specialty-pharmacist@example.com",
            password="testpass123",
            role="pharmacist",
            approval_status="pending",
            account_status="active",
            pharmacist_registration_number="PHARM-BULK-1",
        )
        pharmacist_request.pharmacist_registration_document.save(
            "queue-bulk-specialty-pharmacist-proof.pdf",
            SimpleUploadedFile("queue-bulk-specialty-pharmacist-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "bulk_action": "bulk_assign_suggested_visible",
                "filter_assigned_to": "unassigned",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        pharmacist_request.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, vendor_admin)
        self.assertEqual(pharmacist_request.approval_assigned_to, pharmacist_admin)

    def test_bulk_claim_visible_claims_filtered_queue(self) -> None:
        other_user = User.objects.create_user(
            phone_number="9000000315",
            email="queue-bulk-other@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            business_name="Bulk Other Store",
            vendor_license_number="BULK-200",
        )
        other_user.vendor_license_document.save(
            "queue-bulk-other-proof.pdf",
            SimpleUploadedFile("queue-bulk-other-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.save(update_fields=["approval_due_at", "updated_at"])
        other_user.approval_due_at = timezone.now() + timezone.timedelta(hours=2)
        other_user.save(update_fields=["approval_due_at", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "bulk_action": "bulk_claim_visible",
                "filter_overdue": "1",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        other_user.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, self.admin_user)
        self.assertIsNone(other_user.approval_assigned_to)

    def test_bulk_assign_visible_assigns_filtered_queue(self) -> None:
        other_admin = User.objects.create_user(
            phone_number="9000000316",
            email="queue-bulk-admin@example.com",
            password="testpass123",
            role="admin",
            approval_status="approved",
            account_status="active",
            is_staff=True,
        )
        unassigned_user = User.objects.create_user(
            phone_number="9000000317",
            email="queue-unassigned@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            business_name="Unassigned Store",
            vendor_license_number="UNASSIGNED-100",
        )
        unassigned_user.vendor_license_document.save(
            "queue-unassigned-proof.pdf",
            SimpleUploadedFile("queue-unassigned-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        assigned_user = User.objects.create_user(
            phone_number="9000000318",
            email="queue-assigned@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_assigned_to=self.admin_user,
            approval_assigned_at=timezone.now(),
            business_name="Assigned Store",
            vendor_license_number="ASSIGNED-100",
        )
        assigned_user.vendor_license_document.save(
            "queue-assigned-proof.pdf",
            SimpleUploadedFile("queue-assigned-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "bulk_action": "bulk_assign_visible",
                "assigned_reviewer_id": str(other_admin.pk),
                "filter_assigned_to": "unassigned",
            },
            follow=True,
        )

        unassigned_user.refresh_from_db()
        assigned_user.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(unassigned_user.approval_assigned_to, other_admin)
        self.assertEqual(assigned_user.approval_assigned_to, self.admin_user)

    def test_bulk_verify_visible_documents_updates_visible_roles(self) -> None:
        pharmacist = User.objects.create_user(
            phone_number="9000000319",
            email="queue-pharmacist@example.com",
            password="testpass123",
            role="pharmacist",
            approval_status="pending",
            account_status="active",
            pharmacist_registration_number="PHARM-100",
        )
        pharmacist.pharmacist_registration_document.save(
            "queue-pharmacist-proof.pdf",
            SimpleUploadedFile("queue-pharmacist-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "bulk_action": "bulk_verify_visible_documents",
                "approval_notes": "Bulk verified.",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        pharmacist.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.vendor_license_document_status, "verified")
        self.assertEqual(pharmacist.pharmacist_registration_document_status, "verified")
        self.assertEqual(self.pending_vendor.approval_notes, "Bulk verified.")
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="user",
                entity_id=str(pharmacist.pk),
                event_type="approval_document_status_changed",
            ).exists()
        )

    def test_bulk_reject_visible_documents_respects_filter_slice(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.save(update_fields=["approval_due_at", "updated_at"])
        on_track_user = User.objects.create_user(
            phone_number="9000000320",
            email="queue-doc-ontrack@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_due_at=timezone.now() + timezone.timedelta(hours=2),
            business_name="Doc On Track Store",
            vendor_license_number="DOC-TRACK-100",
        )
        on_track_user.vendor_license_document.save(
            "queue-doc-ontrack-proof.pdf",
            SimpleUploadedFile("queue-doc-ontrack-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "bulk_action": "bulk_reject_visible_documents",
                "filter_overdue": "1",
                "approval_notes": "Rejected overdue docs.",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        on_track_user.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.vendor_license_document_status, "rejected")
        self.assertEqual(on_track_user.vendor_license_document_status, "pending")

    def test_approval_queue_export_returns_csv(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue-export"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=\"approval-queue-export.csv\"", response["Content-Disposition"])
        self.assertIn("full_name,email,phone_number,role,approval_status", content)
        self.assertIn("queue-vendor@example.com", content)

    def test_approval_queue_export_respects_filters(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.save(update_fields=["approval_due_at", "updated_at"])
        on_track_user = User.objects.create_user(
            phone_number="9000000321",
            email="queue-export-ontrack@example.com",
            password="testpass123",
            role="vendor",
            approval_status="pending",
            account_status="active",
            approval_due_at=timezone.now() + timezone.timedelta(hours=2),
            business_name="Export On Track Store",
            vendor_license_number="EXPORT-100",
        )
        on_track_user.vendor_license_document.save(
            "queue-export-ontrack-proof.pdf",
            SimpleUploadedFile("queue-export-ontrack-proof.pdf", b"queue-proof", content_type="application/pdf"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue-export"), {"overdue": "1"})

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("queue-vendor@example.com", content)
        self.assertNotIn("queue-export-ontrack@example.com", content)

    def test_approval_detail_shows_full_timeline(self) -> None:
        AuditLog.objects.create(
            actor=self.pending_vendor,
            actor_label=str(self.pending_vendor),
            event_type="approval_request_created",
            entity_type="user",
            entity_id=str(self.pending_vendor.pk),
            message="Approval request created for queue-vendor@example.com.",
            meta={"role": "vendor"},
        )
        AuditLog.objects.create(
            actor=self.admin_user,
            actor_label=str(self.admin_user),
            event_type="approval_document_status_changed",
            entity_type="user",
            entity_id=str(self.pending_vendor.pk),
            message="Vendor document marked as verified for queue-vendor@example.com.",
            meta={"document_kind": "vendor", "document_status": "verified"},
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-detail", args=[self.pending_vendor.pk]))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Approval Request Detail", content)
        self.assertIn("Approval request created for queue-vendor@example.com.", content)
        self.assertIn("Vendor document marked as verified for queue-vendor@example.com.", content)
        self.assertIn("Download vendor proof", content)

    def test_admin_can_assign_reviewer_from_approval_queue(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": self.pending_vendor.pk,
                "assignment_action": "claim",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_assigned_to, self.admin_user)
        self.assertIsNotNone(self.pending_vendor.approval_assigned_at)
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="user",
                entity_id=str(self.pending_vendor.pk),
                event_type="approval_assignment_changed",
            ).exists()
        )

    def test_approval_detail_shows_overdue_sla_state(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.save(update_fields=["approval_due_at", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-detail", args=[self.pending_vendor.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("Overdue", response.content.decode())

    def test_overdue_queue_request_triggers_escalation_notification(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.approval_assigned_to = self.admin_user
        self.pending_vendor.approval_assigned_at = timezone.now() - timezone.timedelta(hours=1)
        self.pending_vendor.save(update_fields=["approval_due_at", "approval_assigned_to", "approval_assigned_at", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-queue"))

        self.pending_vendor.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.pending_vendor.approval_last_escalated_at)
        self.assertTrue(Notification.objects.filter(user=self.admin_user, title__icontains="overdue").exists())
        self.assertTrue(Notification.objects.filter(user=self.super_admin, title__icontains="overdue").exists())

    def test_admin_dashboard_shows_recent_approval_escalations(self) -> None:
        self.pending_vendor.approval_due_at = timezone.now() - timezone.timedelta(hours=2)
        self.pending_vendor.approval_assigned_to = self.admin_user
        self.pending_vendor.approval_assigned_at = timezone.now() - timezone.timedelta(hours=1)
        self.pending_vendor.save(update_fields=["approval_due_at", "approval_assigned_to", "approval_assigned_at", "updated_at"])
        self.client.force_login(self.admin_user)

        self.client.get(reverse("admin-approval-queue"))
        response = self.client.get(reverse("admin-dashboard"))

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Recent Approval Escalations", content)
        self.assertIn("Approval SLA escalated", content)

    def test_admin_approval_queue_can_approve_user(self) -> None:
        self.client.force_login(self.admin_user)
        self.pending_vendor.vendor_license_document_status = "verified"
        self.pending_vendor.save(update_fields=["vendor_license_document_status", "updated_at"])

        response = self.client.post(
            reverse("admin-approval-queue"),
            {"user_id": self.pending_vendor.pk, "decision": "approved", "approval_notes": "Verified license and business details."},
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_status, "approved")
        self.assertEqual(self.pending_vendor.approval_notes, "Verified license and business details.")
        self.assertEqual(self.pending_vendor.approval_reviewed_by, self.admin_user)
        self.assertIsNotNone(self.pending_vendor.approval_reviewed_at)

    def test_admin_approval_queue_blocks_approval_until_document_verified(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {"user_id": self.pending_vendor.pk, "decision": "approved", "approval_notes": "Trying too early."},
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.approval_status, "pending")
        self.assertIn("must be verified before approval", response.content.decode().lower())

    def test_admin_approval_queue_can_verify_document(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-queue"),
            {
                "user_id": self.pending_vendor.pk,
                "document_kind": "vendor",
                "document_decision": "verified",
                "approval_notes": "PDF reviewed and accepted.",
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-queue"))
        self.assertEqual(self.pending_vendor.vendor_license_document_status, "verified")
        self.assertEqual(self.pending_vendor.approval_notes, "PDF reviewed and accepted.")
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="user",
                entity_id=str(self.pending_vendor.pk),
                event_type="approval_document_status_changed",
            ).exists()
        )

    def test_admin_approval_detail_can_verify_document(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin-approval-detail", args=[self.pending_vendor.pk]),
            {
                "user_id": self.pending_vendor.pk,
                "document_kind": "vendor",
                "document_decision": "verified",
                "approval_notes": "Reviewed from detail page.",
                "next": reverse("admin-approval-detail", args=[self.pending_vendor.pk]),
            },
            follow=True,
        )

        self.pending_vendor.refresh_from_db()
        self.assertRedirects(response, reverse("admin-approval-detail", args=[self.pending_vendor.pk]))
        self.assertEqual(self.pending_vendor.vendor_license_document_status, "verified")
        self.assertEqual(self.pending_vendor.approval_notes, "Reviewed from detail page.")

    def test_non_admin_is_redirected_from_approval_queue(self) -> None:
        customer = User.objects.create_user(
            phone_number="9000000303",
            email="customer-queue@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )
        self.client.force_login(customer)

        response = self.client.get(reverse("admin-approval-queue"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_non_admin_is_redirected_from_approval_detail(self) -> None:
        customer = User.objects.create_user(
            phone_number="9000000310",
            email="customer-detail@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )
        self.client.force_login(customer)

        response = self.client.get(reverse("admin-approval-detail", args=[self.pending_vendor.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_admin_can_download_protected_approval_document(self) -> None:
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-approval-document-download", args=[self.pending_vendor.pk, "vendor"]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))

    def test_non_admin_is_redirected_from_protected_approval_document(self) -> None:
        customer = User.objects.create_user(
            phone_number="9000000304",
            email="customer-download@example.com",
            password="testpass123",
            role="customer",
            approval_status="approved",
            account_status="active",
        )
        self.client.force_login(customer)

        response = self.client.get(reverse("admin-approval-document-download", args=[self.pending_vendor.pk, "vendor"]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
