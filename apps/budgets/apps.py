from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    """
    预算管理模块配置。
    """

    # Django 默认主键类型。
    default_auto_field = "django.db.models.BigAutoField"

    # App 完整路径。
    name = "apps.budgets"

    # App 显示名称。
    verbose_name = "预算管理"
