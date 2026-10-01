from django.apps import AppConfig


class TagsConfig(AppConfig):
    """
    账单标签模块配置。
    """

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.tags"

    verbose_name = "账单标签"
