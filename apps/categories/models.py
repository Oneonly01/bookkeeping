from django.db import models

# Create your models here.
from django.conf import settings


class Category(models.Model):
    """
    收入 / 支出分类模型。

    支持两种分类：

    1. 系统分类
       例如：餐饮、交通、工资、奖金

    2. 用户自定义分类
       例如：健身、宠物、副业等
    """

    class CategoryType(models.TextChoices):
        """
        分类类型。
        """

        # 支出分类。
        EXPENSE = "expense", "支出"

        # 收入分类。
        INCOME = "income", "收入"

    # ==============================
    # 用户关联
    # ==============================

    # 所属用户。
    #
    # 系统默认分类 user=NULL。
    #
    # 用户自定义分类则关联具体用户。
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
        verbose_name="所属用户",
        db_comment=("分类所属用户，NULL表示系统默认分类"),
    )

    # ==============================
    # 分类基础信息
    # ==============================

    # 分类名称。
    name = models.CharField(
        max_length=50,
        verbose_name="分类名称",
        db_comment="收入或支出分类名称",
    )

    # 分类类型。
    category_type = models.CharField(
        max_length=20,
        choices=CategoryType.choices,
        verbose_name="分类类型",
        db_comment=("分类类型：expense支出、income收入"),
    )

    # ==============================
    # 前端展示
    # ==============================

    # 分类图标。
    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="图标",
        db_comment="分类图标标识",
    )

    # 分类颜色。
    color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="颜色",
        db_comment="分类展示颜色",
    )

    # 排序值。
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="排序",
        db_comment="分类排序，值越小越靠前",
    )

    # ==============================
    # 状态字段
    # ==============================

    # 是否为系统默认分类。
    is_system = models.BooleanField(
        default=False,
        verbose_name="系统分类",
        db_comment="是否为系统内置分类",
    )

    # 是否启用。
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否启用",
        db_comment="分类是否启用",
    )

    # 是否逻辑删除。
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否删除",
        db_comment="分类逻辑删除标记",
    )

    # ==============================
    # 时间字段
    # ==============================

    # 创建时间。
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
        db_comment="分类创建时间",
    )

    # 更新时间。
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
        db_comment="分类最后更新时间",
    )

    class Meta:
        """
        Category 数据库配置。
        """

        # 数据库表名。
        db_table = "categories"

        # MySQL 表注释。
        db_table_comment = "收入支出分类表"

        verbose_name = "分类"
        verbose_name_plural = "分类"

        # 常用查询索引。
        indexes = [
            models.Index(
                fields=[
                    "user",
                    "category_type",
                    "is_deleted",
                    "sort_order",
                ],
                name="idx_category_user_list",
            ),
            models.Index(
                fields=[
                    "is_system",
                    "category_type",
                    "is_deleted",
                ],
                name="idx_category_system",
            ),
        ]

    def __str__(self) -> str:
        """
        返回分类名称。
        """

        return self.name
