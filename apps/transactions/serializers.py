from decimal import Decimal

from rest_framework import serializers

from .models import Transaction


class TransactionCreateSerializer(serializers.Serializer):
    """
    新增收入 / 支出账单参数序列化器。
    """

    account_id = serializers.IntegerField(
        min_value=1,
        required=True,
    )

    category_id = serializers.IntegerField(
        min_value=1,
        required=True,
    )

    transaction_type = serializers.ChoiceField(
        choices=Transaction.TransactionType.choices,
        required=True,
    )

    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=True,
    )

    transaction_time = serializers.DateTimeField(
        required=True,
    )

    merchant = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )


class TransactionSerializer(serializers.ModelSerializer):
    """
    账单返回序列化器。
    """

    account_name = serializers.CharField(
        source="account.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        allow_null=True,
    )

    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Transaction

        fields = [
            "id",
            "account",
            "account_name",
            "category",
            "category_name",
            "transaction_type",
            "transaction_type_display",
            "amount",
            "transaction_time",
            "merchant",
            "note",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class TransactionUpdateSerializer(serializers.Serializer):
    """
    修改账单参数序列化器。
    """

    account_id = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    category_id = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    transaction_type = serializers.ChoiceField(
        choices=Transaction.TransactionType.choices,
        required=False,
    )

    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )

    transaction_time = serializers.DateTimeField(
        required=False,
    )

    merchant = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        """
        至少提供一个修改字段。
        """

        if not attrs:
            raise serializers.ValidationError("请至少提供一个需要修改的字段")

        return attrs


class TransactionQuerySerializer(serializers.Serializer):
    """
    账单列表查询参数序列化器。

    所有参数均为可选。
    """

    # 收入 / 支出类型。
    transaction_type = serializers.ChoiceField(
        choices=Transaction.TransactionType.choices,
        required=False,
    )

    # 账户 ID。
    account_id = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    # 分类 ID。
    category_id = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    # 开始日期。
    start_date = serializers.DateField(
        required=False,
    )

    # 结束日期。
    end_date = serializers.DateField(
        required=False,
    )

    # 搜索关键字。
    keyword = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        """
        校验日期范围。
        """

        start_date = attrs.get("start_date")

        end_date = attrs.get("end_date")

        # 如果开始日期和结束日期同时存在，
        # 开始日期不能晚于结束日期。
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始日期不能晚于结束日期")

        return attrs
