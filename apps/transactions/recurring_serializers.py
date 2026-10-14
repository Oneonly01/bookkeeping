from rest_framework import serializers

from .models import RecurringExecution, RecurringTransaction
from .serializers import TransactionCreateSerializer, TransactionTagSerializer


class RecurringTransactionCreateSerializer(TransactionCreateSerializer):
    """
    创建周期账单模板。

    沿用普通账单的金额、账户、分类、标签校验；
    交易时间由计划日期生成，不由客户端单独传入。
    """

    transaction_time = None

    # ==========================================
    # 模板名称 / 执行周期
    # ==========================================
    name = serializers.CharField(
        max_length=100,
    )
    frequency = serializers.ChoiceField(
        choices=RecurringTransaction.Frequency.choices,
    )
    interval = serializers.IntegerField(
        min_value=1,
        max_value=365,
        required=False,
        default=1,
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
    )

    def validate(self, attrs):
        """结束日期不能早于起始日期。"""
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if self.instance is not None:
            start_date = attrs.get("start_date", self.instance.start_date)
            end_date = attrs.get("end_date", self.instance.end_date)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                "结束日期不能早于起始日期",
            )
        return attrs


class RecurringTransactionUpdateSerializer(RecurringTransactionCreateSerializer):
    """修改模板；未传字段保持原值，不修改已生成账单。"""

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.required = False
            field.default = serializers.empty
        return fields

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "请至少提供一个需要修改的字段",
            )
        return super().validate(attrs)


class RecurringTransactionSerializer(serializers.ModelSerializer):
    """周期账单模板返回数据。"""

    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        """与普通账单一致，隐藏已删除标签。"""
        return TransactionTagSerializer(
            obj.tags.filter(is_deleted=False),
            many=True,
        ).data

    class Meta:
        model = RecurringTransaction
        fields = [
            "id", "name", "account", "category", "tags", "transaction_type",
            "amount", "merchant", "note", "frequency", "interval", "start_date",
            "end_date", "next_date", "is_active", "last_error", "created_at", "updated_at",
        ]
        read_only_fields = fields


class RecurringExecutionSerializer(serializers.ModelSerializer):
    """执行记录；transaction为生成的账单ID。"""

    class Meta:
        model = RecurringExecution
        fields = ["id", "scheduled_date", "transaction", "created_at"]
        read_only_fields = fields
