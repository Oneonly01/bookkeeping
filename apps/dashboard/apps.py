from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """
    首页 Dashboard 模块配置。
    """

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.dashboard"

    verbose_name = "首页数据"
