from decimal import Decimal
from rest_framework import serializers

from .models import Budget


class BudgetCreateSerializer(serializers.Serializer):
    """
    创建预算请求序列化器。

    负责：
    1. 参数格式校验；
    2. 基础字段校验。

    复杂业务规则放在 Service 中处理。
    """

    # ==========================================
    # 预算类型
    # ==========================================

    budget_type = serializers.ChoiceField(
        choices=Budget.BudgetType.choices,
    )

    # ==========================================
    # 分类 ID
    # ==========================================

    # 总预算时可以不传。
    #
    # 分类预算时必须传，
    # 具体规则由 Service 校验。
    category_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )

    # ==========================================
    # 年份
    # ==========================================

    year = serializers.IntegerField(
        min_value=1900,
        max_value=2100,
    )

    # ==========================================
    # 月份
    # ==========================================

    month = serializers.IntegerField(
        min_value=1,
        max_value=12,
    )

    # ==========================================
    # 预算金额
    # ==========================================

    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )

    # ==========================================
    # 提醒阈值
    # ==========================================

    alert_threshold = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("100.00"),
        required=False,
        default=Decimal("80.00"),
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

    def validate(self, attrs):
        """
        校验预算类型和分类参数之间的关系。
        """

        # 获取预算类型。
        budget_type = attrs.get("budget_type")

        # 获取分类 ID。
        category_id = attrs.get("category_id")

        # ======================================
        # 总预算
        # ======================================

        if budget_type == Budget.BudgetType.OVERALL and category_id is not None:
            raise serializers.ValidationError("总预算不能指定分类")

        # ======================================
        # 分类预算
        # ======================================

        if budget_type == Budget.BudgetType.CATEGORY and category_id is None:
            raise serializers.ValidationError("分类预算必须指定分类")

        return attrs


class BudgetSerializer(serializers.ModelSerializer):
    """
    预算响应序列化器。
    """

    # 预算类型中文名称。
    budget_type_display = serializers.CharField(
        source="get_budget_type_display",
        read_only=True,
    )

    # 分类名称。
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Budget

        fields = [
            "id",
            "budget_type",
            "budget_type_display",
            "category",
            "category_name",
            "year",
            "month",
            "amount",
            "alert_threshold",
            "note",
            "is_active",
            "created_at",
            "updated_at",
        ]


class BudgetUpdateSerializer(serializers.Serializer):
    """
    修改预算请求序列化器。
    """

    # 预算金额。
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )

    # 提醒阈值。
    alert_threshold = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("100.00"),
        required=False,
    )

    # 备注。
    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    # 是否启用。
    is_active = serializers.BooleanField(
        required=False,
    )

    def validate(
        self,
        attrs,
    ):
        """
        修改预算时至少传一个字段。
        """

        if not attrs:
            raise serializers.ValidationError("请至少提供一个需要修改的字段")

        return attrs


class BudgetProgressQuerySerializer(serializers.Serializer):
    """
    预算执行进度查询参数序列化器。

    支持：
    1. year：年份；
    2. month：月份。

    如果都不传，
    默认查询当前年月。
    """

    # 年份。
    year = serializers.IntegerField(
        required=False,
        min_value=1900,
        max_value=2100,
    )

    # 月份。
    month = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
    )

    def validate(
        self,
        attrs,
    ):
        """
        校验 year 和 month。

        year 和 month 要么同时传，
        要么都不传。
        """

        # 获取年份。
        year = attrs.get("year")

        # 获取月份。
        month = attrs.get("month")

        # 只传 year，
        # 没传 month。
        only_year = year is not None and month is None

        # 只传 month，
        # 没传 year。
        only_month = year is None and month is not None

        # 两个参数必须同时出现。
        if only_year or only_month:
            raise serializers.ValidationError("year 和 month 必须同时传入")

        return attrs


class BudgetQuerySerializer(serializers.Serializer):
    """
    预算列表查询参数序列化器。

    支持：
    1. 年份；
    2. 月份；
    3. 预算类型；
    4. 启用状态；
    5. 分类 ID。
    """

    # ==========================================
    # 年份
    # ==========================================

    year = serializers.IntegerField(
        required=False,
        min_value=1900,
        max_value=2100,
    )

    # ==========================================
    # 月份
    # ==========================================

    month = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
    )

    # ==========================================
    # 预算类型
    # ==========================================

    # overall：
    # 总预算。
    #
    # category：
    # 分类预算。
    budget_type = serializers.ChoiceField(
        choices=Budget.BudgetType.choices,
        required=False,
    )

    # ==========================================
    # 是否启用
    # ==========================================

    is_active = serializers.BooleanField(
        required=False,
    )

    # ==========================================
    # 分类 ID
    # ==========================================

    category_id = serializers.IntegerField(
        required=False,
        min_value=1,
    )


class BudgetCopySerializer(serializers.Serializer):
    """
    复制月度预算请求序列化器。

    用于把某个月的预算，
    批量复制到另一个月份。
    """

    # ==========================================
    # 来源年份
    # ==========================================

    source_year = serializers.IntegerField(
        min_value=1900,
        max_value=2100,
    )

    # ==========================================
    # 来源月份
    # ==========================================

    source_month = serializers.IntegerField(
        min_value=1,
        max_value=12,
    )

    # ==========================================
    # 目标年份
    # ==========================================

    target_year = serializers.IntegerField(
        min_value=1900,
        max_value=2100,
    )

    # ==========================================
    # 目标月份
    # ==========================================

    target_month = serializers.IntegerField(
        min_value=1,
        max_value=12,
    )

    def validate(
        self,
        attrs,
    ):
        """
        校验来源月份和目标月份。
        """

        # 来源年月。
        source_year = attrs["source_year"]

        source_month = attrs["source_month"]

        # 目标年月。
        target_year = attrs["target_year"]

        target_month = attrs["target_month"]

        # 不允许复制到同一个月份。
        same_month = source_year == target_year and source_month == target_month

        if same_month:
            raise serializers.ValidationError("来源月份和目标月份不能相同")

        return attrs
