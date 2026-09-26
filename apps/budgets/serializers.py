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
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
    )

    # ==========================================
    # 提醒阈值
    # ==========================================

    alert_threshold = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.01,
        max_value=100,
        required=False,
        default=80,
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
