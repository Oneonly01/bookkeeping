from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    Product,
    ProductPriceRecord,
)


class ProductCreateSerializer(serializers.Serializer):
    """
    创建商品请求序列化器。
    """

    # ==========================================
    # 商品名称
    # ==========================================

    name = serializers.CharField(
        max_length=150,
    )

    # ==========================================
    # 品牌
    # ==========================================

    brand = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 型号
    # ==========================================

    model_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 分类
    # ==========================================

    category = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 商品链接
    # ==========================================

    product_url = serializers.URLField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 商品图片
    # ==========================================

    image_url = serializers.URLField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 备注
    # ==========================================

    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_name(
        self,
        value,
    ):
        """
        商品名称不能只有空格。
        """

        value = value.strip()

        if not value:
            raise serializers.ValidationError("商品名称不能为空")

        return value


class ProductSerializer(serializers.ModelSerializer):
    """
    商品响应序列化器。
    """

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "brand",
            "model_name",
            "category",
            "product_url",
            "image_url",
            "note",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ProductQuerySerializer(serializers.Serializer):
    """
    商品列表查询参数。
    """

    keyword = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    category = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    brand = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    is_active = serializers.BooleanField(
        required=False,
    )


class ProductUpdateSerializer(serializers.Serializer):
    """
    修改商品请求序列化器。

    允许修改：

    1. 商品名称；
    2. 品牌；
    3. 型号；
    4. 分类；
    5. 商品链接；
    6. 商品图片；
    7. 备注；
    8. 启用状态。
    """

    # ==========================================
    # 商品名称
    # ==========================================

    name = serializers.CharField(
        max_length=150,
        required=False,
    )

    # ==========================================
    # 品牌
    # ==========================================

    brand = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 商品型号
    # ==========================================

    model_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 商品分类
    # ==========================================

    category = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 商品链接
    # ==========================================

    product_url = serializers.URLField(
        max_length=500,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 商品图片
    # ==========================================

    image_url = serializers.URLField(
        max_length=500,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 商品备注
    # ==========================================

    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 启用状态
    # ==========================================

    is_active = serializers.BooleanField(
        required=False,
    )

    def validate_name(
        self,
        value,
    ):
        """
        商品名称不能只有空格。
        """

        value = value.strip()

        if not value:
            raise serializers.ValidationError("商品名称不能为空")

        return value

    def validate(
        self,
        attrs,
    ):
        """
        至少需要修改一个字段。
        """

        if not attrs:
            raise serializers.ValidationError("至少需要修改一个字段")

        return attrs


class ProductPriceCreateSerializer(serializers.Serializer):
    """
    新增商品价格记录请求序列化器。
    """

    # ==========================================
    # 商品价格
    # ==========================================

    price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    # ==========================================
    # 平台
    # ==========================================

    platform = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 价格记录日期
    # ==========================================

    recorded_date = serializers.DateField(
        required=False,
    )

    # ==========================================
    # 备注
    # ==========================================

    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_recorded_date(
        self,
        value,
    ):
        """
        价格记录日期不能晚于今天。

        允许补录历史价格，
        但不允许记录未来价格。
        """

        if value > timezone.localdate():
            raise serializers.ValidationError("价格记录日期不能晚于今天")

        return value


class ProductPriceRecordSerializer(serializers.ModelSerializer):
    """
    商品价格历史响应序列化器。
    """

    class Meta:
        model = ProductPriceRecord

        fields = [
            "id",
            "price",
            "platform",
            "recorded_date",
            "note",
            "created_at",
        ]
