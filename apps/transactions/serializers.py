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


class TransactionSummaryQuerySerializer(serializers.Serializer):
    """
    账单汇总查询参数序列化器。
    """

    # 开始日期。
    start_date = serializers.DateField(
        required=False,
    )

    # 结束日期。
    end_date = serializers.DateField(
        required=False,
    )

    def validate(self, attrs):
        """
        校验日期范围。
        """

        start_date = attrs.get("start_date")

        end_date = attrs.get("end_date")

        # 如果同时传入开始和结束日期，
        # 开始日期不能晚于结束日期。
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始日期不能晚于结束日期")

        return attrs


class TransactionTrendQuerySerializer(serializers.Serializer):
    """
    账单趋势查询参数序列化器。
    """

    # 开始日期。
    start_date = serializers.DateField(
        required=False,
    )

    # 结束日期。
    end_date = serializers.DateField(
        required=False,
    )

    def validate(self, attrs):
        """
        校验日期范围。
        """

        start_date = attrs.get("start_date")

        end_date = attrs.get("end_date")

        # 如果同时传入开始日期和结束日期，
        # 开始日期不能晚于结束日期。
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始日期不能晚于结束日期")

        return attrs


class TransactionCategoryStatisticsQuerySerializer(serializers.Serializer):
    """
    账单分类统计查询参数序列化器。

    用于校验：
    1. 账单类型；
    2. 开始日期；
    3. 结束日期。
    """

    # 账单类型。
    #
    # 只能是：
    # expense：支出
    # income：收入
    transaction_type = serializers.ChoiceField(
        choices=Transaction.TransactionType.choices,
        required=True,
    )

    # 开始日期。
    #
    # 非必填，例如：
    # 2026-09-01
    start_date = serializers.DateField(
        required=False,
    )

    # 结束日期。
    #
    # 非必填，例如：
    # 2026-09-30
    end_date = serializers.DateField(
        required=False,
    )

    def validate(self, attrs):
        """
        校验开始日期和结束日期是否合法。
        """

        # 获取开始日期。
        start_date = attrs.get("start_date")

        # 获取结束日期。
        end_date = attrs.get("end_date")

        # 如果两个日期都存在，
        # 则开始日期不能晚于结束日期。
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始日期不能晚于结束日期")

        # 返回校验通过的数据。
        return attrs


class TransactionMonthlyStatisticsQuerySerializer(serializers.Serializer):
    """
    月度统计查询参数序列化器。

    month：
        可选参数。

        格式：
        YYYY-MM

        例如：
        2026-09

    如果不传 month，
    默认统计当前月份。
    """

    # 月份参数。
    #
    # 使用字符串接收，
    # 后续在 validate_month 中统一校验格式。
    month = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=7,
    )

    def validate_month(
        self,
        value,
    ):
        """
        校验月份格式。

        正确格式：
        YYYY-MM

        例如：
        2026-09
        """

        # 导入 datetime，
        # 用于校验月份格式是否合法。
        from datetime import datetime

        try:
            # 尝试按照 YYYY-MM 格式解析。
            datetime.strptime(
                value,
                "%Y-%m",
            )

        except ValueError:
            # 如果解析失败，
            # 说明月份格式不正确。
            raise serializers.ValidationError("月份格式必须为 YYYY-MM")

        # 返回校验通过的月份。
        return value


class TransactionYearlyStatisticsQuerySerializer(serializers.Serializer):
    """
    年度收支统计查询参数序列化器。

    year：
        可选参数。

        例如：
        2026

    如果不传 year，
    默认统计当前年份。
    """

    # 年份。
    #
    # 限制一个合理范围，
    # 防止传入明显异常的数据。
    year = serializers.IntegerField(
        required=False,
        min_value=1900,
        max_value=2100,
    )
