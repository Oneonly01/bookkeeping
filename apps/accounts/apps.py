from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    账户管理应用配置。
    """

    # Django 默认主键类型。
    default_auto_field = "django.db.models.BigAutoField"

    # 当前应用完整 Python 路径。
    name = "apps.accounts"

    # Django Admin 中显示的中文名称。
    verbose_name = "账户管理"
