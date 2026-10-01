from django.apps import AppConfig


class ProductsConfig(AppConfig):
    """
    商品价格模块配置。
    """

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.products"

    verbose_name = "商品价格"
