from django.conf import settings
from django.db import models


class UserAssetMonthlySnapshot(models.Model):
    """
    用户月末资产快照。

    当前月份的记录用于标记已开始跟踪，不作为月末余额使用。
    跨月后在任何余额变更前结转，已结转记录不再随补记账单而变化。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asset_monthly_snapshots",
        verbose_name="所属用户",
        db_comment="资产快照所属用户",
    )

    # 统一保存所属月份的第一天，例如2026-11-01代表2026年11月。
    month = models.DateField(
        verbose_name="快照月份",
        db_comment="快照所属月份，统一保存每月第一天",
    )

    # 多账户金额相加后可能超过单账户上限，汇总字段保留更大的容量。
    total_assets = models.DecimalField(
        max_digits=24, decimal_places=2, default=0,
        verbose_name="总资产", db_comment="月末正余额账户金额合计",
    )
    total_liabilities = models.DecimalField(
        max_digits=24, decimal_places=2, default=0,
        verbose_name="总负债", db_comment="月末负余额账户金额绝对值合计",
    )
    net_assets = models.DecimalField(
        max_digits=24, decimal_places=2, default=0,
        verbose_name="净资产", db_comment="月末总资产减总负债",
    )
    account_count = models.PositiveIntegerField(
        default=0, verbose_name="账户数量", db_comment="纳入快照的有效账户数量",
    )

    # 未结转记录仅为跟踪起点，金额不能被当作已确认的月末余额。
    is_closed = models.BooleanField(
        default=False, verbose_name="是否已结转", db_comment="是否已确认月末余额",
    )
    closed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="结转时间",
        db_comment="实际执行结转的时间，不一定是月末零点",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user_asset_monthly_snapshot"
        db_table_comment = "用户月末资产快照表"
        verbose_name = "月末资产快照"
        verbose_name_plural = "月末资产快照"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "month"],
                name="uq_asset_snapshot_user_month",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.month:%Y-%m}"
