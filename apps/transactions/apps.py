from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    """
    账单模块配置。
    """

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.transactions"

    verbose_name = "账单管理"
