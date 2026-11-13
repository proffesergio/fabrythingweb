from django.apps import AppConfig


class StoreopsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "storeops"

    def ready(self):
        from . import signals  # noqa: F401
