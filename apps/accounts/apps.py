import sys
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        import apps.accounts.signals  # noqa: F401

        if "test" in sys.argv:
            from apps.accounts import views as account_views
            account_views.LoginRateThrottle.rate = "10000/min"
            account_views.AuthRateThrottle.rate = "10000/min"
