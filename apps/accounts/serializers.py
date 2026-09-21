# 导入 DRF 序列化器模块。
from decimal import Decimal
from rest_framework import serializers

# 导入账户模型。
from .models import Account, AccountBalanceAdjustment, Transfer


# 定义创建账户序列化器。
class AccountCreateSerializer(serializers.Serializer):
    """
    创建账户序列化器。

    主要职责：
    1. 校验账户名称；
    2. 校验账户类型；
    3. 校验初始余额；
    4. 校验当前用户是否存在同名账户。
    """

    # 账户名称。
    name = serializers.CharField(
        # 最大长度 50。
        max_length=50,
        # 必填。
        required=True,
        # 自动去除首尾空格。
        trim_whitespace=True,
        # 自定义错误提示。
        error_messages={
            "required": "请输入账户名称",
            "blank": "账户名称不能为空",
            "max_length": "账户名称长度不能超过50个字符",
        },
    )

    # 账户类型。
    account_type = serializers.ChoiceField(
        # 使用 Account 模型中的账户类型枚举。
        choices=Account.AccountType.choices,
        # 必填。
        required=True,
        # 自定义错误提示。
        error_messages={
            "required": "请选择账户类型",
            "invalid_choice": "账户类型不正确",
        },
    )

    # 初始余额。
    initial_balance = serializers.DecimalField(
        # 最大总位数 14。
        max_digits=14,
        # 保留两位小数。
        decimal_places=2,
        # 非必填。
        required=False,
        # 默认余额 0。
        default=0,
    )

    # 图标。
    icon = serializers.CharField(
        # 最大长度 100。
        max_length=100,
        # 非必填。
        required=False,
        # 允许空字符串。
        allow_blank=True,
        # 默认空字符串。
        default="",
    )

    # 颜色。
    color = serializers.CharField(
        # 最大长度 20。
        max_length=20,
        # 非必填。
        required=False,
        # 允许空字符串。
        allow_blank=True,
        # 默认空字符串。
        default="",
    )

    # 排序值。
    sort_order = serializers.IntegerField(
        # 非必填。
        required=False,
        # 默认 0。
        default=0,
        # 不允许负数。
        min_value=0,
    )

    # 是否设置为默认账户。
    is_default = serializers.BooleanField(
        # 非必填。
        required=False,
        # 默认 false。
        default=False,
    )

    def __init__(self, *args, **kwargs):
        """
        初始化序列化器。

        从 context 中取得 request，
        用于获取当前登录用户。
        """

        # 调用父类初始化方法。
        super().__init__(*args, **kwargs)

        # 获取 request。
        request = self.context.get("request")

        # 保存当前登录用户。
        self.user = request.user if request else None

    def validate_name(self, value):
        """
        校验当前用户是否存在同名未删除账户。
        """

        # 如果没有获取到当前用户，
        # 直接返回，由权限系统处理。
        if self.user is None:
            return value

        # 查询当前用户是否存在相同名称、
        # 并且没有逻辑删除的账户。
        exists = Account.objects.filter(
            user=self.user,
            name=value,
            is_deleted=False,
        ).exists()

        # 如果存在同名账户，
        # 不允许重复创建。
        if exists:
            raise serializers.ValidationError("已存在同名账户")

        # 校验成功。
        return value


# 定义账户返回序列化器。
class AccountSerializer(serializers.ModelSerializer):
    """
    账户信息返回序列化器。
    """

    # 返回账户类型对应的中文名称。
    account_type_display = serializers.CharField(
        source="get_account_type_display",
        read_only=True,
    )

    class Meta:
        """
        序列化器配置。
        """

        # 对应 Account 模型。
        model = Account

        # 接口返回字段。
        fields = [
            "id",
            "name",
            "account_type",
            "account_type_display",
            "initial_balance",
            "balance",
            "icon",
            "color",
            "sort_order",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]

        # 当前 Serializer 仅用于返回，
        # 所有字段设置为只读。
        read_only_fields = fields


class AccountUpdateSerializer(serializers.Serializer):
    """
    修改账户序列化器。

    允许修改：
    - 账户名称
    - 账户类型
    - 图标
    - 颜色
    - 排序
    - 是否默认账户
    - 是否启用

    不允许直接修改：
    - initial_balance
    - balance
    """

    name = serializers.CharField(
        max_length=50,
        required=False,
        trim_whitespace=True,
        error_messages={
            "blank": "账户名称不能为空",
            "max_length": "账户名称长度不能超过50个字符",
        },
    )

    account_type = serializers.ChoiceField(
        choices=Account.AccountType.choices,
        required=False,
        error_messages={
            "invalid_choice": "账户类型不正确",
        },
    )

    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    sort_order = serializers.IntegerField(
        required=False,
        min_value=0,
    )

    is_default = serializers.BooleanField(
        required=False,
    )

    is_active = serializers.BooleanField(
        required=False,
    )

    def __init__(self, *args, **kwargs):
        """
        获取当前用户以及待修改账户。
        """

        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        self.user = request.user if request else None

        self.account = self.context.get("account")

    def validate_name(self, value):
        """
        校验账户名称是否与当前用户其他账户重复。
        """

        if self.user is None or self.account is None:
            return value

        queryset = Account.objects.filter(
            user=self.user,
            name=value,
            is_deleted=False,
        ).exclude(id=self.account.id)

        if queryset.exists():
            raise serializers.ValidationError("已存在同名账户")

        return value

    def validate(self, attrs):
        """
        至少需要传入一个可修改字段。
        """

        if not attrs:
            raise serializers.ValidationError("请至少提供一个需要修改的字段")

        return attrs


class AccountBalanceAdjustSerializer(serializers.Serializer):
    """
    账户余额校准参数序列化器。

    负责校验：
    1. 新的真实余额；
    2. 校准说明。
    """

    # 用户输入的账户真实余额。
    balance = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=True,
        error_messages={
            "required": "请输入账户实际余额",
            "invalid": "账户余额格式不正确",
            "max_digits": "账户余额超出允许范围",
            "max_decimal_places": "账户余额最多保留两位小数",
        },
    )

    # 校准原因。
    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        default="",
        error_messages={
            "max_length": "校准说明不能超过255个字符",
        },
    )


class AccountBalanceAdjustmentSerializer(serializers.ModelSerializer):
    """
    账户余额校准记录序列化器。

    用于返回账户历史余额校准记录。
    """

    class Meta:
        # 对应账户余额校准记录模型。
        model = AccountBalanceAdjustment

        # 返回字段。
        fields = [
            "id",
            "old_balance",
            "new_balance",
            "difference",
            "note",
            "created_at",
        ]

        # 所有字段仅用于读取。
        read_only_fields = fields


class TransferCreateSerializer(serializers.Serializer):
    """
    创建转账记录参数序列化器。
    """

    # 转出账户 ID。
    source_account_id = serializers.IntegerField(
        min_value=1,
        required=True,
    )

    # 转入账户 ID。
    target_account_id = serializers.IntegerField(
        min_value=1,
        required=True,
    )

    # 转账金额。
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=True,
    )

    # 手续费。
    fee = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        default=Decimal("0.00"),
    )

    # 实际转账时间。
    transfer_time = serializers.DateTimeField(
        required=True,
    )

    # 备注。
    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):
        """
        跨字段校验。
        """

        source_account_id = attrs["source_account_id"]

        target_account_id = attrs["target_account_id"]

        # 不允许自己转给自己。
        if source_account_id == target_account_id:
            raise serializers.ValidationError("转出账户和转入账户不能相同")

        return attrs


class TransferSerializer(serializers.ModelSerializer):
    """
    转账记录返回序列化器。
    """

    source_account_name = serializers.CharField(
        source="source_account.name",
        read_only=True,
    )

    target_account_name = serializers.CharField(
        source="target_account.name",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Transfer

        fields = [
            "id",
            "source_account",
            "source_account_name",
            "target_account",
            "target_account_name",
            "amount",
            "fee",
            "transfer_time",
            "note",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
