from django.apps import AppConfig


class SavingsConfig(AppConfig):
    """
    储蓄目标模块配置。
    """

    # Django 默认主键类型。
    default_auto_field = "django.db.models.BigAutoField"

    # App 完整路径。
    name = "apps.savings"

    # 后台显示名称。
    verbose_name = "储蓄目标"
