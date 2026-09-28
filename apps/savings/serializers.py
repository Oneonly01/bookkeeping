from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import SavingsGoal, SavingsRecord


class SavingsGoalCreateSerializer(serializers.Serializer):
    """
    创建储蓄目标请求序列化器。

    负责基础参数校验。
    """

    # ==========================================
    # 目标名称
    # ==========================================

    name = serializers.CharField(
        max_length=100,
    )

    # ==========================================
    # 目标金额
    # ==========================================

    target_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    # ==========================================
    # 截止日期
    # ==========================================

    deadline = serializers.DateField(
        required=False,
        allow_null=True,
    )

    # ==========================================
    # 图标
    # ==========================================

    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    # ==========================================
    # 颜色
    # ==========================================

    color = serializers.CharField(
        max_length=20,
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

    def validate_deadline(
        self,
        value,
    ):
        """
        校验截止日期。

        创建目标时，
        截止日期不能早于今天。
        """

        # 没有设置截止日期时直接返回。
        if value is None:
            return value

        # 获取当前本地日期。
        today = timezone.localdate()

        # 截止日期不能早于今天。
        if value < today:
            raise serializers.ValidationError("截止日期不能早于今天")

        return value


class SavingsGoalSerializer(serializers.ModelSerializer):
    """
    储蓄目标响应序列化器。
    """

    # 状态中文名称。
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    # 储蓄进度百分比。
    progress_percentage = serializers.SerializerMethodField()

    # 剩余需要储蓄金额。
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal

        fields = [
            "id",
            "name",
            "target_amount",
            "current_amount",
            "remaining_amount",
            "progress_percentage",
            "deadline",
            "icon",
            "color",
            "note",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]

    def get_progress_percentage(
        self,
        obj,
    ):
        """
        计算储蓄完成百分比。
        """

        # 防御性处理。
        if obj.target_amount <= 0:
            return "0.00"

        # 计算百分比。
        percentage = obj.current_amount / obj.target_amount * Decimal("100")

        # 保留两位小数。
        percentage = percentage.quantize(Decimal("0.01"))

        return f"{percentage:.2f}"

    def get_remaining_amount(
        self,
        obj,
    ):
        """
        计算距离目标还差多少钱。
        """

        remaining = obj.target_amount - obj.current_amount

        # 如果已经超额完成，
        # 剩余金额统一返回 0。
        if remaining < 0:
            remaining = Decimal("0.00")

        return f"{remaining:.2f}"


class SavingsGoalUpdateSerializer(serializers.Serializer):
    """
    储蓄目标修改请求序列化器。

    注意：

    current_amount 不允许通过普通修改接口直接修改。

    当前已存金额只能通过后续：
    deposit / withdraw
    接口进行变更。
    """

    # ==========================================
    # 目标名称
    # ==========================================

    name = serializers.CharField(
        max_length=100,
        required=False,
    )

    # ==========================================
    # 目标金额
    # ==========================================

    target_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )

    # ==========================================
    # 截止日期
    # ==========================================

    deadline = serializers.DateField(
        required=False,
        allow_null=True,
    )

    # ==========================================
    # 图标
    # ==========================================

    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 颜色
    # ==========================================

    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    # ==========================================
    # 备注
    # ==========================================

    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    def validate_deadline(
        self,
        value,
    ):
        """
        校验目标截止日期。

        修改后的截止日期不能早于今天。
        """

        # 用户允许清空截止日期。
        if value is None:
            return value

        today = timezone.localdate()

        if value < today:
            raise serializers.ValidationError("截止日期不能早于今天")

        return value

    def validate(
        self,
        attrs,
    ):
        """
        通用校验。
        """

        # PUT 请求至少需要传一个可修改字段。
        if not attrs:
            raise serializers.ValidationError("至少需要修改一个字段")

        return attrs


class SavingsDepositSerializer(serializers.Serializer):
    """
    储蓄目标存入资金请求序列化器。
    """

    # ==========================================
    # 存入金额
    # ==========================================

    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
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


class SavingsWithdrawSerializer(serializers.Serializer):
    """
    储蓄目标取出资金请求序列化器。
    """

    # ==========================================
    # 取出金额
    # ==========================================

    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
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


class SavingsRecordSerializer(serializers.ModelSerializer):
    """
    储蓄流水响应序列化器。
    """

    # 流水类型中文名称。
    record_type_display = serializers.CharField(
        source="get_record_type_display",
        read_only=True,
    )

    class Meta:
        model = SavingsRecord

        fields = [
            "id",
            "record_type",
            "record_type_display",
            "amount",
            "before_amount",
            "after_amount",
            "note",
            "created_at",
        ]
