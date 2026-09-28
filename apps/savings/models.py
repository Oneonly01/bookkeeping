from django.conf import settings
from django.db import models
from django.db.models import Q


class SavingsGoal(models.Model):
    """
    储蓄目标表。

    用于记录用户的存钱计划。

    例如：

    旅游基金：
        目标金额：10000 元
        当前已存：3000 元
        截止日期：2027-05-01

    买电脑：
        目标金额：15000 元
        当前已存：5000 元
    """

    class Status(models.TextChoices):
        """
        储蓄目标状态。
        """

        # 正常进行中。
        ACTIVE = "active", "进行中"

        # 用户主动暂停。
        PAUSED = "paused", "已暂停"

        # 已完成储蓄目标。
        COMPLETED = "completed", "已完成"

    # ==========================================
    # 用户
    # ==========================================

    # 每个储蓄目标必须属于某一个用户。
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="savings_goals",
        verbose_name="用户",
    )

    # ==========================================
    # 目标名称
    # ==========================================

    name = models.CharField(
        max_length=100,
        verbose_name="目标名称",
    )

    # ==========================================
    # 目标金额
    # ==========================================

    # 财务金额统一使用 DecimalField。
    target_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="目标金额",
    )

    # ==========================================
    # 当前已存金额
    # ==========================================

    # 创建目标时默认为 0。
    #
    # 后面通过“存入 / 取出”接口修改，
    # 普通修改目标接口不能直接修改该字段。
    current_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="当前已存金额",
    )

    # ==========================================
    # 截止日期
    # ==========================================

    # 截止日期可以为空。
    #
    # 有些用户可能只是长期储蓄，
    # 没有明确完成日期。
    deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name="截止日期",
    )

    # ==========================================
    # 图标
    # ==========================================

    # 后续前端可根据图标名称展示对应图标。
    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="图标",
    )

    # ==========================================
    # 颜色
    # ==========================================

    color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="颜色",
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

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="目标状态",
    )

    # ==========================================
    # 逻辑删除
    # ==========================================

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

        db_table = "savings_goals"

        verbose_name = "储蓄目标"

        verbose_name_plural = "储蓄目标"

        # 默认按照最新创建时间排序。
        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            # 查询当前用户目标列表。
            models.Index(
                fields=[
                    "user",
                    "status",
                    "is_deleted",
                ],
                name="saving_user_status_idx",
            ),
            # 查询截止日期。
            models.Index(
                fields=[
                    "user",
                    "deadline",
                ],
                name="saving_user_deadline_idx",
            ),
        ]

        constraints = [
            # ==================================
            # 目标金额必须大于 0
            # ==================================
            models.CheckConstraint(
                condition=Q(target_amount__gt=0),
                name="saving_target_positive_ck",
            ),
            # ==================================
            # 当前已存金额不能小于 0
            # ==================================
            models.CheckConstraint(
                condition=Q(current_amount__gte=0),
                name="saving_current_nonnegative_ck",
            ),
        ]

    def __str__(self):
        """
        Django Admin 等位置展示内容。
        """

        return f"{self.user_id} - " f"{self.name}"


class SavingsRecord(models.Model):
    """
    储蓄资金流水表。

    每一次存入、取出都必须生成一条流水记录，
    用于保证储蓄目标金额变化可追踪、可审计。
    """

    class RecordType(models.TextChoices):
        """
        流水类型。
        """

        # 存入资金。
        DEPOSIT = "deposit", "存入"

        # 取出资金。
        WITHDRAW = "withdraw", "取出"

    # ==========================================
    # 所属用户
    # ==========================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="savings_records",
        verbose_name="用户",
    )

    # ==========================================
    # 所属储蓄目标
    # ==========================================

    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.PROTECT,
        related_name="records",
        verbose_name="储蓄目标",
    )

    # ==========================================
    # 流水类型
    # ==========================================

    record_type = models.CharField(
        max_length=20,
        choices=RecordType.choices,
        verbose_name="流水类型",
    )

    # ==========================================
    # 本次金额
    # ==========================================

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="金额",
    )

    # ==========================================
    # 变动前金额
    # ==========================================

    before_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="变动前金额",
    )

    # ==========================================
    # 变动后金额
    # ==========================================

    after_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="变动后金额",
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
    # 创建时间
    # ==========================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        """
        数据库配置。
        """

        db_table = "savings_records"

        verbose_name = "储蓄流水"

        verbose_name_plural = "储蓄流水"

        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            # 查询某个目标的流水。
            models.Index(
                fields=[
                    "goal",
                    "created_at",
                ],
                name="saving_record_goal_idx",
            ),
            # 查询用户的储蓄流水。
            models.Index(
                fields=[
                    "user",
                    "created_at",
                ],
                name="saving_record_user_idx",
            ),
        ]

        constraints = [
            # 流水金额必须大于 0。
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="saving_record_amount_positive_ck",
            ),
            # 变动前金额不能小于 0。
            models.CheckConstraint(
                condition=Q(before_amount__gte=0),
                name="saving_record_before_nonnegative_ck",
            ),
            # 变动后金额不能小于 0。
            models.CheckConstraint(
                condition=Q(after_amount__gte=0),
                name="saving_record_after_nonnegative_ck",
            ),
        ]

    def __str__(self):
        """
        后台展示。
        """

        return f"{self.goal_id} - " f"{self.record_type} - " f"{self.amount}"
