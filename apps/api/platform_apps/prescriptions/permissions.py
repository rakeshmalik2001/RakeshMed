from rest_framework.permissions import BasePermission


class IsPharmacistOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in {"admin", "pharmacist"})
        )
