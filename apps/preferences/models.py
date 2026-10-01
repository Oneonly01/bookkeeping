from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """
    用户系统偏好设置。
    """

    class ThemeChoice(models.TextChoices):
        LIGHT = "light", "浅色"

        DARK = "dark", "深色"

        SYSTEM = "system", "跟随系统"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preference",
        verbose_name="用户",
    )

    # 默认货币
    currency = models.CharField(
        max_length=10,
        default="CNY",
        verbose_name="默认货币",
    )

    # 主题模式
    theme = models.CharField(
        max_length=20,
        choices=ThemeChoice.choices,
        default=ThemeChoice.SYSTEM,
        verbose_name="主题模式",
    )

    # 每页显示数量
    page_size = models.PositiveIntegerField(
        default=20,
        verbose_name="分页数量",
    )

    # 是否开启预算提醒
    budget_reminder_enabled = models.BooleanField(
        default=True,
        verbose_name="预算提醒开关",
    )

    # 预算提醒阈值
    budget_reminder_threshold = models.PositiveIntegerField(
        default=80,
        verbose_name="预算提醒阈值",
    )

    # 默认账户
    default_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_users",
        verbose_name="默认账户",
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
        db_table = "user_preference"

        verbose_name = "用户偏好"

        verbose_name_plural = "用户偏好"

    def __str__(self):
        return f"{self.user} preference"
