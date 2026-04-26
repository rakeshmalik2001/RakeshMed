from __future__ import annotations

from django.conf import settings
from django.db import transaction


class ReadReplicaRouter:
    """
    Route read queries to the optional replica connection when explicitly enabled.

    This keeps writes, migrations, and all transactional work on the primary.
    """

    def db_for_read(self, model, **hints):
        if not getattr(settings, "ENABLE_DB_REPLICA_ROUTING", False):
            return None

        if "replica" not in settings.DATABASES:
            return None

        if transaction.get_connection(using="default").in_atomic_block:
            return "default"

        return "replica"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
