from django.conf import settings
from django.db import models


class Tag(models.Model):
    """
    账单标签。

    标签用于对账单做辅助分类。

    例如：

    工作
    报销
    旅游
    家庭
    聚餐
    冲动消费

    标签与账单分类不同：

    分类：
        餐饮、交通、工资等主要分类。

    标签：
        用户自己定义的辅助标记。
    """

    # ==========================================
    # 所属用户
    # ==========================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
        verbose_name="用户",
    )

    # ==========================================
    # 标签名称
    # ==========================================

    name = models.CharField(
        max_length=50,
        verbose_name="标签名称",
    )

    # ==========================================
    # 标签颜色
    # ==========================================

    color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="标签颜色",
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
        db_table = "tags"

        verbose_name = "账单标签"

        verbose_name_plural = "账单标签"

        ordering = [
            "name",
            "id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "is_deleted",
                ],
                name="tag_user_deleted_idx",
            ),
        ]

    def __str__(self):
        """
        后台展示。
        """

        return f"{self.user_id} - " f"{self.name}"
