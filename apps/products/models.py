from django.conf import settings
from django.db import models
from django.db.models import Q


class Product(models.Model):
    """
    商品表。

    用户可以手动维护自己关注的商品，
    后续再通过价格记录表保存每次录入的商品价格。
    """

    # ==========================================
    # 所属用户
    # ==========================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="用户",
    )

    # ==========================================
    # 商品名称
    # ==========================================

    name = models.CharField(
        max_length=150,
        verbose_name="商品名称",
    )

    # ==========================================
    # 品牌
    # ==========================================

    brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="品牌",
    )

    # ==========================================
    # 商品型号
    # ==========================================

    model_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="商品型号",
    )

    # ==========================================
    # 商品分类
    # ==========================================

    category = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="商品分类",
    )

    # ==========================================
    # 商品链接
    # ==========================================

    # 用户可以手动保存商品购买链接。
    product_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="商品链接",
    )

    # ==========================================
    # 商品图片
    # ==========================================

    # 第一版先保存图片 URL，
    # 后续如果需要上传图片再扩展 ImageField。
    image_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="商品图片",
    )

    # ==========================================
    # 备注
    # ==========================================

    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    # ==========================================
    # 是否启用
    # ==========================================

    is_active = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    # ==========================================
    # 逻辑删除
    # ==========================================

    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否删除",
    )

    # ==========================================
    # 时间字段
    # ==========================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        """
        数据库配置。
        """

        db_table = "products"

        verbose_name = "商品"

        verbose_name_plural = "商品"

        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            # 当前用户商品列表。
            models.Index(
                fields=[
                    "user",
                    "is_deleted",
                ],
                name="product_user_deleted_idx",
            ),
            # 商品名称查询。
            models.Index(
                fields=[
                    "user",
                    "name",
                ],
                name="product_user_name_idx",
            ),
        ]

    def __str__(self):
        """
        后台展示。
        """

        return f"{self.user_id} - " f"{self.name}"


class ProductPriceRecord(models.Model):
    """
    商品价格历史记录。

    每次手动记录价格时都新增一条记录，
    不覆盖旧价格。
    """

    # ==========================================
    # 所属用户
    # ==========================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_price_records",
        verbose_name="用户",
    )

    # ==========================================
    # 所属商品
    # ==========================================

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="price_records",
        verbose_name="商品",
    )

    # ==========================================
    # 商品价格
    # ==========================================

    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="商品价格",
    )

    # ==========================================
    # 平台名称
    # ==========================================

    platform = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="平台",
    )

    # ==========================================
    # 价格记录日期
    # ==========================================

    recorded_date = models.DateField(
        verbose_name="价格记录日期",
    )

    # ==========================================
    # 备注
    # ==========================================

    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    # ==========================================
    # 创建时间
    # ==========================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        db_table = "product_price_records"

        verbose_name = "商品价格记录"
        verbose_name_plural = "商品价格记录"

        ordering = [
            "-recorded_date",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "recorded_date",
                ],
                name="product_price_date_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "recorded_date",
                ],
                name="product_price_user_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="product_price_positive_ck",
            ),
        ]

    def __str__(self):
        """
        后台显示内容。
        """

        return f"{self.product_id} - " f"{self.price} - " f"{self.recorded_date}"
