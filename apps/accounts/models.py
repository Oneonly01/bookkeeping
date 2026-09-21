from django.conf import settings
from django.db import models


class Account(models.Model):
    """
    用户资金账户模型。

    用于保存用户的现金、银行卡、微信、支付宝、
    信用卡及其他资金账户信息。

    后续收入、支出、转账等业务都会依赖该账户。
    """

    class AccountType(models.TextChoices):
        """
        账户类型枚举。
        """

        # 现金账户。
        CASH = "cash", "现金"

        # 微信账户。
        WECHAT = "wechat", "微信"

        # 支付宝账户。
        ALIPAY = "alipay", "支付宝"

        # 银行卡账户。
        BANK = "bank", "银行卡"

        # 信用卡账户。
        CREDIT_CARD = "credit_card", "信用卡"

        # 其他账户。
        OTHER = "other", "其他"

    # ==============================
    # 用户关联
    # ==============================

    # 当前账户所属用户。
    user = models.ForeignKey(
        # 关联 Django 当前使用的用户模型。
        settings.AUTH_USER_MODEL,
        # 用户删除后，其账户数据一并删除。
        on_delete=models.CASCADE,
        # 允许通过 user.accounts 查询用户账户。
        related_name="accounts",
        # Django 后台显示名称。
        verbose_name="所属用户",
        # MySQL 字段注释。
        db_comment="账户所属用户",
    )

    # ==============================
    # 账户基础信息
    # ==============================

    # 用户自定义账户名称。
    name = models.CharField(
        # 最大长度 50。
        max_length=50,
        # Django 显示名称。
        verbose_name="账户名称",
        # MySQL 字段注释。
        db_comment="用户自定义账户名称",
    )

    # 账户类型。
    account_type = models.CharField(
        # 最大长度 20。
        max_length=20,
        # 使用上面定义的账户类型枚举。
        choices=AccountType.choices,
        # 默认账户类型为其他。
        default=AccountType.OTHER,
        # Django 显示名称。
        verbose_name="账户类型",
        # MySQL 字段注释。
        db_comment=(
            "账户类型：cash现金、wechat微信、"
            "alipay支付宝、bank银行卡、"
            "credit_card信用卡、other其他"
        ),
    )

    # ==============================
    # 余额字段
    # ==============================

    # 账户创建时录入的初始余额。
    initial_balance = models.DecimalField(
        # 总长度最多 14 位。
        max_digits=14,
        # 保留两位小数。
        decimal_places=2,
        # 默认 0 元。
        default=0,
        # Django 显示名称。
        verbose_name="初始余额",
        # MySQL 字段注释。
        db_comment="账户创建时的初始余额",
    )

    # 当前实际余额。
    balance = models.DecimalField(
        # 总长度最多 14 位。
        max_digits=14,
        # 保留两位小数。
        decimal_places=2,
        # 默认 0 元。
        default=0,
        # Django 显示名称。
        verbose_name="当前余额",
        # MySQL 字段注释。
        db_comment="账户当前实际余额",
    )

    # ==============================
    # 前端展示字段
    # ==============================

    # 账户图标标识。
    icon = models.CharField(
        # 最长 100 个字符。
        max_length=100,
        # 允许为空。
        blank=True,
        # 默认空字符串。
        default="",
        # Django 显示名称。
        verbose_name="图标",
        # MySQL 字段注释。
        db_comment="账户图标标识",
    )

    # 账户展示颜色。
    color = models.CharField(
        # 最大长度 20。
        max_length=20,
        # 允许为空。
        blank=True,
        # 默认空字符串。
        default="",
        # Django 显示名称。
        verbose_name="颜色",
        # MySQL 字段注释。
        db_comment="账户展示颜色",
    )

    # 账户排序值。
    sort_order = models.PositiveIntegerField(
        # 默认排序值 0。
        default=0,
        # Django 显示名称。
        verbose_name="排序",
        # MySQL 字段注释。
        db_comment="账户列表排序值，值越小越靠前",
    )

    # ==============================
    # 状态字段
    # ==============================

    # 是否为默认账户。
    is_default = models.BooleanField(
        # 默认不是默认账户。
        default=False,
        # Django 显示名称。
        verbose_name="默认账户",
        # MySQL 字段注释。
        db_comment="是否为用户默认账户",
    )

    # 账户是否启用。
    is_active = models.BooleanField(
        # 默认启用。
        default=True,
        # Django 显示名称。
        verbose_name="是否启用",
        # MySQL 字段注释。
        db_comment="账户是否启用",
    )

    # 逻辑删除标记。
    is_deleted = models.BooleanField(
        # 默认未删除。
        default=False,
        # Django 显示名称。
        verbose_name="是否删除",
        # MySQL 字段注释。
        db_comment="逻辑删除标记",
    )

    # ==============================
    # 时间字段
    # ==============================

    # 记录创建时间。
    created_at = models.DateTimeField(
        # 创建时自动写入当前时间。
        auto_now_add=True,
        # Django 显示名称。
        verbose_name="创建时间",
        # MySQL 字段注释。
        db_comment="记录创建时间",
    )

    # 记录更新时间。
    updated_at = models.DateTimeField(
        # 每次保存时自动更新时间。
        auto_now=True,
        # Django 显示名称。
        verbose_name="更新时间",
        # MySQL 字段注释。
        db_comment="记录最后更新时间",
    )

    class Meta:
        """
        Account 模型数据库配置。
        """

        # 数据库真实表名。
        db_table = "accounts"

        # MySQL 表注释。
        db_table_comment = "用户资金账户表"

        # Django 后台显示名称。
        verbose_name = "账户"

        # Django 后台复数显示名称。
        verbose_name_plural = "账户"

        # 创建账户列表查询索引。
        indexes = [
            models.Index(
                # 主要用于：
                # 根据用户 + 删除状态 + 排序值查询账户列表。
                fields=[
                    "user",
                    "is_deleted",
                    "sort_order",
                ],
                # 索引名称。
                name="idx_account_user_list",
            ),
        ]

    def __str__(self) -> str:
        """
        返回账户名称。

        Django Admin 等位置展示时使用。
        """

        return self.name


class AccountBalanceAdjustment(models.Model):
    """
    账户余额校准记录。

    每次人工修改账户余额都必须留下记录，
    用于后续审计、问题排查以及余额变化追踪。
    """

    # 关联被校准的账户。
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="balance_adjustments",
        verbose_name="账户",
        db_comment="被执行余额校准的账户",
    )

    # 记录所属用户。
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_balance_adjustments",
        verbose_name="所属用户",
        db_comment="执行余额校准的用户",
    )

    # 校准前余额。
    old_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="校准前余额",
        db_comment="余额校准前的账户余额",
    )

    # 校准后余额。
    new_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="校准后余额",
        db_comment="余额校准后的账户余额",
    )

    # 余额差额。
    difference = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="调整差额",
        db_comment="新余额减去旧余额的差额",
    )

    # 校准原因。
    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="校准说明",
        db_comment="账户余额校准原因或备注",
    )

    # 创建时间。
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
        db_comment="余额校准记录创建时间",
    )

    class Meta:
        # 数据库表名。
        db_table = "account_balance_adjustments"

        # MySQL 表注释。
        db_table_comment = "账户余额校准记录表"

        verbose_name = "账户余额校准记录"
        verbose_name_plural = "账户余额校准记录"

        # 后续查询某个账户的校准历史时使用。
        indexes = [
            models.Index(
                fields=[
                    "user",
                    "account",
                    "created_at",
                ],
                name="idx_balance_adjust_history",
            ),
        ]

    def __str__(self) -> str:
        """
        返回简单描述。
        """

        return f"{self.account.name}: " f"{self.old_balance} -> " f"{self.new_balance}"


class Transfer(models.Model):
    """
    账户转账记录。

    仅用于记录用户不同资金账户之间的内部资金流转，
    不代表真实银行或第三方支付平台发起了转账。
    """

    class Status(models.TextChoices):
        """
        转账状态。
        """

        NORMAL = "normal", "正常"
        DELETED = "deleted", "已删除"

    # 当前转账所属用户。
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transfers",
        verbose_name="所属用户",
        db_comment="转账记录所属用户",
    )

    # 转出账户。
    source_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
        verbose_name="转出账户",
        db_comment="资金转出的账户",
    )

    # 转入账户。
    target_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        verbose_name="转入账户",
        db_comment="资金转入的账户",
    )

    # 转账金额。
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="转账金额",
        db_comment="账户之间转移的金额",
    )

    # 手续费。
    fee = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="手续费",
        db_comment="本次转账产生的手续费",
    )

    # 转账时间。
    transfer_time = models.DateTimeField(
        verbose_name="转账时间",
        db_comment="用户实际发生转账的时间",
    )

    # 转账备注。
    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
        db_comment="转账备注",
    )

    # 转账状态。
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
        verbose_name="状态",
        db_comment="转账状态：normal正常、deleted已删除",
    )

    # 创建时间。
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
        db_comment="转账记录创建时间",
    )

    # 更新时间。
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
        db_comment="转账记录最后更新时间",
    )

    class Meta:
        db_table = "transfers"
        db_table_comment = "账户转账记录表"
        verbose_name = "账户转账"
        verbose_name_plural = "账户转账"

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "transfer_time",
                ],
                name="idx_transfer_user_time",
            ),
            models.Index(
                fields=[
                    "user",
                    "source_account",
                    "transfer_time",
                ],
                name="idx_transfer_source_time",
            ),
            models.Index(
                fields=[
                    "user",
                    "target_account",
                    "transfer_time",
                ],
                name="idx_transfer_target_time",
            ),
        ]

        constraints = [
            # 转账金额必须大于 0。
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ck_transfer_amount_positive",
            ),
            # 手续费不能小于 0。
            models.CheckConstraint(
                condition=models.Q(fee__gte=0),
                name="ck_transfer_fee_nonnegative",
            ),
            # 转出账户和转入账户不能相同。
            models.CheckConstraint(
                condition=~models.Q(source_account=models.F("target_account")),
                name="ck_transfer_accounts_different",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.source_account.name} -> "
            f"{self.target_account.name}: "
            f"{self.amount}"
        )
