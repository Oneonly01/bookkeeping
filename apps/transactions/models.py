from django.conf import settings
from django.db import models

from apps.accounts.models import Account
from apps.categories.models import Category


class Transaction(models.Model):
    """
    收入 / 支出账单模型。

    注意：
    转账不放在这里，
    转账已经由 transfers 表单独管理。
    """

    class TransactionType(models.TextChoices):
        """
        账单类型。
        """

        EXPENSE = "expense", "支出"

        INCOME = "income", "收入"

    class Status(models.TextChoices):
        """
        账单状态。
        """

        NORMAL = "normal", "正常"

        DELETED = "deleted", "已删除"

    # ==============================
    # 用户
    # ==============================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="所属用户",
        db_comment="账单所属用户",
    )

    # ==============================
    # 账户和分类
    # ==============================

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="账户",
        db_comment="账单关联账户",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="分类",
        db_comment="账单关联分类",
    )
    # ==========================================
    # 账单标签
    # ==========================================

    tags = models.ManyToManyField(
        "tags.Tag",
        related_name="transactions",
        blank=True,
        verbose_name="标签",
    )

    # ==============================
    # 账单核心字段
    # ==============================

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="账单类型",
        db_comment=("账单类型：" "expense支出、income收入"),
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="金额",
        db_comment="账单金额，必须大于0",
    )

    transaction_time = models.DateTimeField(
        verbose_name="账单时间",
        db_comment="收入或支出实际发生时间",
    )

    # ==============================
    # 辅助信息
    # ==============================

    merchant = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="商户",
        db_comment="消费商户或收入来源",
    )

    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
        db_comment="账单备注",
    )

    # ==============================
    # 状态
    # ==============================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
        verbose_name="状态",
        db_comment="账单状态：normal正常、deleted已删除",
    )

    # ==============================
    # 时间
    # ==============================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
        db_comment="账单创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
        db_comment="账单最后更新时间",
    )

    class Meta:
        """
        Transaction 数据库配置。
        """

        db_table = "transactions"

        db_table_comment = "收入支出账单表"

        verbose_name = "账单"

        verbose_name_plural = "账单"

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "transaction_time",
                ],
                name="idx_tx_user_time",
            ),
            models.Index(
                fields=[
                    "user",
                    "transaction_type",
                    "transaction_time",
                ],
                name="idx_tx_user_type_time",
            ),
            models.Index(
                fields=[
                    "user",
                    "account",
                    "transaction_time",
                ],
                name="idx_tx_user_account_time",
            ),
            models.Index(
                fields=[
                    "user",
                    "category",
                    "transaction_time",
                ],
                name="idx_tx_user_category_time",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ck_tx_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        """
        返回账单简要信息。
        """

        return f"{self.get_transaction_type_display()} " f"{self.amount}"


class TransactionImage(models.Model):
    """
    账单图片。

    一条账单可以关联多张图片，
    例如：

    1. 消费小票；
    2. 支付截图；
    3. 发票照片；
    4. 其他记账凭证。
    """

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="账单",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transaction_images",
        verbose_name="用户",
    )

    image = models.ImageField(
        upload_to="transactions/%Y/%m/",
        verbose_name="账单图片",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        db_table = "transaction_image"

        verbose_name = "账单图片"

        verbose_name_plural = "账单图片"

        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "transaction",
                    "user",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"TransactionImage("
            f"transaction_id={self.transaction_id}, "
            f"id={self.id}"
            f")"
        )


class ApiIdempotencyRecord(models.Model):
    """
    金额操作的重复提交凭证。

    同一用户的同一个请求键只能成功执行一次。
    凭证和业务变更一起提交，避免扣款成功却未保存响应。
    """

    # ==========================================
    # 请求所属用户 / 请求唯一键
    # ==========================================
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
        verbose_name="用户",
    )
    request_key = models.CharField(
        max_length=128,
        verbose_name="请求唯一键",
    )
    fingerprint = models.CharField(
        max_length=64,
        verbose_name="请求内容摘要",
    )

    # 保存首次成功响应，重试直接返回原结果。
    response_data = models.JSONField(
        null=True,
        verbose_name="响应内容",
    )
    status_code = models.PositiveSmallIntegerField(
        default=200,
        verbose_name="HTTP状态码",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        db_table = "api_idempotency_record"
        verbose_name = "重复提交凭证"
        verbose_name_plural = "重复提交凭证"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "request_key"],
                name="unique_user_request_key",
            ),
        ]


class RecurringTransaction(models.Model):
    """
    周期账单模板。

    模板本身不改变余额；到期执行时复用新增账单业务。
    月末和闰日按起始日期计算，不因短月发生永久日期偏移。
    """

    class Frequency(models.TextChoices):
        DAILY = "daily", "每天"
        WEEKLY = "weekly", "每周"
        MONTHLY = "monthly", "每月"
        YEARLY = "yearly", "每年"

    # ==========================================
    # 用户 / 记账账户 / 分类 / 标签
    # ==========================================
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_transactions",
        verbose_name="用户",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="recurring_transactions",
        verbose_name="账户",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="recurring_transactions",
        verbose_name="分类",
    )
    tags = models.ManyToManyField(
        "tags.Tag",
        blank=True,
        related_name="recurring_transactions",
        verbose_name="标签",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="模板名称",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=Transaction.TransactionType.choices,
        verbose_name="账单类型",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="金额",
    )
    merchant = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="商户",
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    # ==========================================
    # 执行计划
    # ==========================================
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        verbose_name="周期类型",
    )
    interval = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="周期间隔",
    )
    start_date = models.DateField(
        verbose_name="起始日期",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="结束日期",
    )
    next_date = models.DateField(
        verbose_name="下次执行日期",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否删除",
    )
    last_error = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="最近执行错误",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        db_table = "recurring_transaction"
        verbose_name = "周期账单模板"
        verbose_name_plural = "周期账单模板"
        ordering = ["next_date", "id"]
        indexes = [
            models.Index(
                fields=["is_active", "is_deleted", "next_date"],
                name="recurring_due_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="recurring_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(interval__gte=1, interval__lte=365),
                name="recurring_interval_range",
            ),
        ]


class RecurringExecution(models.Model):
    """
    周期账单执行记录。

    同一模板、同一周期只能生成一条账单。
    账单逻辑删除后仍保留执行记录，防止定时任务重新生成。
    """

    template = models.ForeignKey(
        RecurringTransaction,
        on_delete=models.CASCADE,
        related_name="executions",
        verbose_name="模板",
    )
    scheduled_date = models.DateField(
        verbose_name="计划日期",
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name="recurring_execution",
        verbose_name="生成账单",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="执行时间",
    )

    class Meta:
        db_table = "recurring_execution"
        verbose_name = "周期账单执行记录"
        verbose_name_plural = "周期账单执行记录"
        ordering = ["-scheduled_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "scheduled_date"],
                name="unique_recurring_period",
            ),
        ]
