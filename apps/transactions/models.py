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
