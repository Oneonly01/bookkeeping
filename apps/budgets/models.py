from django.conf import settings
from django.db import models
from django.db.models import Q


class Budget(models.Model):
    """
    用户预算表。

    V1.0 主要支持：

    1. 月度总预算；
    2. 月度分类预算。

    示例：

    总预算：
        2026年9月支出预算 3000 元。

    分类预算：
        2026年9月餐饮预算 1000 元。
    """

    class BudgetType(models.TextChoices):
        """
        预算类型。
        """

        # 整个月所有支出的总预算。
        OVERALL = "overall", "总预算"

        # 针对某个支出分类设置预算。
        CATEGORY = "category", "分类预算"

    # ==========================================
    # 用户
    # ==========================================

    # 每条预算必须属于某一个用户。
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
        verbose_name="用户",
    )

    # ==========================================
    # 预算类型
    # ==========================================

    # overall：
    # 月度总预算。
    #
    # category：
    # 分类预算。
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        verbose_name="预算类型",
    )

    # ==========================================
    # 分类
    # ==========================================

    # 总预算时：
    # category = NULL。
    #
    # 分类预算时：
    # category 必须指定分类。
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="budgets",
        verbose_name="预算分类",
    )

    # ==========================================
    # 年份 / 月份
    # ==========================================

    # 预算年份。
    year = models.PositiveSmallIntegerField(
        verbose_name="年份",
    )

    # 预算月份。
    month = models.PositiveSmallIntegerField(
        verbose_name="月份",
    )

    # ==========================================
    # 预算金额
    # ==========================================

    # 财务金额必须使用 Decimal。
    #
    # 不能使用 FloatField。
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="预算金额",
    )

    # ==========================================
    # 提醒比例
    # ==========================================

    # 达到预算多少百分比以后进行提醒。
    #
    # 默认：
    # 80.00%
    alert_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80,
        verbose_name="提醒阈值",
    )

    # ==========================================
    # 备注
    # ==========================================

    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    # ==========================================
    # 状态
    # ==========================================

    # 是否启用。
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    # 逻辑删除。
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否删除",
    )

    # ==========================================
    # 时间字段
    # ==========================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        """
        数据库配置。
        """

        db_table = "budgets"

        verbose_name = "预算"

        verbose_name_plural = "预算"

        # 默认：
        # 年份倒序
        # 月份倒序
        # ID倒序
        ordering = [
            "-year",
            "-month",
            "-id",
        ]

        indexes = [
            # 查询某个用户某个月预算时使用。
            models.Index(
                fields=[
                    "user",
                    "year",
                    "month",
                ],
                name="budget_user_month_idx",
            ),
            # 查询用户预算类型时使用。
            models.Index(
                fields=[
                    "user",
                    "budget_type",
                ],
                name="budget_user_type_idx",
            ),
            # 查询分类预算时使用。
            models.Index(
                fields=[
                    "user",
                    "category",
                    "year",
                    "month",
                ],
                name="budget_category_idx",
            ),
        ]

        constraints = [
            # ==================================
            # 月份必须是 1～12
            # ==================================
            models.CheckConstraint(
                condition=(Q(month__gte=1) & Q(month__lte=12)),
                name="budget_month_range_ck",
            ),
            # ==================================
            # 预算金额必须大于 0
            # ==================================
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="budget_amount_positive_ck",
            ),
            # ==================================
            # 提醒比例范围
            # ==================================
            # 允许：
            # 0 < threshold <= 100
            models.CheckConstraint(
                condition=(Q(alert_threshold__gt=0) & Q(alert_threshold__lte=100)),
                name="budget_alert_range_ck",
            ),
            # ==================================
            # 预算类型和分类必须匹配
            # ==================================
            # overall：
            # category 必须为空。
            #
            # category：
            # category 必须存在。
            models.CheckConstraint(
                condition=(
                    Q(
                        budget_type="overall",
                        category__isnull=True,
                    )
                    | Q(
                        budget_type="category",
                        category__isnull=False,
                    )
                ),
                name="budget_type_category_ck",
            ),
            # ==================================
            # 分类预算唯一
            # ==================================
            # 同一个用户：
            # 同一年
            # 同一个月
            # 同一个分类
            #
            # 只能创建一个分类预算。
            models.UniqueConstraint(
                fields=[
                    "user",
                    "category",
                    "year",
                    "month",
                ],
                name="budget_category_unique",
            ),
        ]

    def __str__(self):
        """
        Django Admin 等位置的显示内容。
        """

        return (
            f"{self.user_id} - "
            f"{self.year}-{self.month:02d} - "
            f"{self.get_budget_type_display()}"
        )
