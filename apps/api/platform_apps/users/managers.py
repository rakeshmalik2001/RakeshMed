from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone_number: str, password: str | None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number must be set.")

        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        update_fields: list[str] = []
        if not user.created_by_id:
            user.created_by = user
            update_fields.append("created_by")
        if not user.updated_by_id:
            user.updated_by = user
            update_fields.append("updated_by")
        if update_fields:
            update_fields.append("updated_at")
            user.save(using=self._db, update_fields=update_fields)
        return user

    def create_user(self, phone_number: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "super_admin")
        extra_fields.setdefault("is_phone_verified", True)
        extra_fields.setdefault("account_status", "active")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone_number, password, **extra_fields)
