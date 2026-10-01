from django.apps import AppConfig


class PreferencesConfig(AppConfig):
    """
    用户偏好模块配置。
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.preferences"
    verbose_name = "偏好设置"
