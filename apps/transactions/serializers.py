from decimal import Decimal

from rest_framework import serializers

from apps.tags.models import Tag

from .models import Transaction, TransactionImage


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
    # ==========================================
    # 账单标签 ID 列表
    # ==========================================

    tag_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1,
        ),
        required=False,
        allow_empty=True,
        default=list,
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

    def validate_tag_ids(
        self,
        value,
    ):
        """
        标签 ID 去重。

        例如：

        [1, 2, 2, 3]

        转换为：

        [1, 2, 3]
        """

        return list(dict.fromkeys(value))


class TransactionTagSerializer(serializers.ModelSerializer):
    """
    账单标签返回序列化器。

    用于在账单详情、账单列表中
    返回当前账单绑定的标签信息。
    """

    class Meta:
        model = Tag

        fields = [
            "id",
            "name",
            "color",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """
    账单返回序列化器。

    用于返回：

    1. 账单基本信息；
    2. 账户名称；
    3. 分类名称；
    4. 账单类型中文名称；
    5. 账单状态中文名称；
    6. 当前账单绑定的标签列表。
    """

    # ==========================================
    # 账户名称
    # ==========================================

    account_name = serializers.CharField(
        source="account.name",
        read_only=True,
    )

    # ==========================================
    # 分类名称
    # ==========================================

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        allow_null=True,
    )

    # ==========================================
    # 账单类型中文名称
    # ==========================================

    transaction_type_display = serializers.CharField(
        source=("get_transaction_type_display"),
        read_only=True,
    )

    # ==========================================
    # 账单状态中文名称
    # ==========================================

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    # ==========================================
    # 账单标签
    # ==========================================
    #
    # 一个账单可以绑定多个标签，
    # 所以这里使用 many=True。
    #
    # 标签只能通过 tag_ids 在
    # 创建 / 修改接口中进行设置，
    # 这里仅负责返回。
    # ==========================================

    tags = serializers.SerializerMethodField()

    def get_tags(
        self,
        obj,
    ):
        """
        只返回未删除标签。
        """

        tags = obj.tags.filter(
            is_deleted=False,
        )

        return TransactionTagSerializer(
            tags,
            many=True,
        ).data

    class Meta:
        model = Transaction

        fields = [
            "id",
            # 账户。
            "account",
            "account_name",
            # 分类。
            "category",
            "category_name",
            # 标签。
            "tags",
            # 账单类型。
            "transaction_type",
            "transaction_type_display",
            # 金额。
            "amount",
            # 交易时间。
            "transaction_time",
            # 商户。
            "merchant",
            # 备注。
            "note",
            # 状态。
            "status",
            "status_display",
            # 时间字段。
            "created_at",
            "updated_at",
        ]

        # 当前 Serializer 只负责返回数据，
        # 所有字段均为只读。
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
    # ==========================================
    # 账单标签 ID 列表
    # ==========================================

    tag_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1,
        ),
        required=False,
        allow_empty=True,
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

    def validate_tag_ids(
        self,
        value,
    ):
        """
        标签 ID 去重。
        """

        return list(dict.fromkeys(value))


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


class TransactionImageUploadSerializer(serializers.Serializer):
    """
    账单图片上传参数序列化器。

    用于校验用户上传的账单图片。
    """

    image = serializers.ImageField(
        required=True,
    )

    def validate_image(
        self,
        value,
    ):
        """
        校验账单图片。

        规则：
        1. 图片大小不能超过 5MB；
        2. 仅允许 JPG、JPEG、PNG、WEBP；
        3. ImageField 本身会校验是否为有效图片。
        """

        # ==========================================
        # 图片大小校验
        # ==========================================

        max_size = 5 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError("图片大小不能超过 5MB")

        # ==========================================
        # 图片扩展名校验
        # ==========================================

        file_name = value.name.lower()

        allowed_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")

        if not file_name.endswith(allowed_extensions):
            raise serializers.ValidationError("仅支持 JPG、JPEG、PNG、WEBP 图片")

        return value


class TransactionImageSerializer(serializers.ModelSerializer):
    """
    账单图片返回序列化器。
    """

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TransactionImage

        fields = [
            "id",
            "image_url",
            "created_at",
        ]

        read_only_fields = fields

    def get_image_url(
        self,
        obj,
    ):
        """
        返回完整图片访问地址。
        """

        request = self.context.get("request")

        if not obj.image:
            return ""

        image_url = obj.image.url

        if request:
            return request.build_absolute_uri(image_url)

        return image_url
