from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """
    用户扩展资料。

    Django 默认 User 负责认证、密码和权限；
    UserProfile 保存记账系统相关的用户业务资料。
    """

    class Gender(models.IntegerChoices):
        UNKNOWN = 0, "未知"
        MALE = 1, "男"
        FEMALE = 2, "女"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="用户",
        db_comment="关联的系统用户",
    )

    nickname = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="昵称",
        db_comment="用户昵称",
    )

    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="手机号",
        db_comment="用户手机号，唯一",
    )

    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="头像",
        db_comment="用户头像文件路径",
    )

    gender = models.PositiveSmallIntegerField(
        choices=Gender.choices,
        default=Gender.UNKNOWN,
        verbose_name="性别",
        db_comment="性别：0未知，1男，2女",
    )

    birthday = models.DateField(
        null=True,
        blank=True,
        verbose_name="生日",
        db_comment="用户出生日期",
    )

    currency = models.CharField(
        max_length=10,
        default="CNY",
        verbose_name="默认货币",
        db_comment="用户默认货币，例如 CNY",
    )

    timezone = models.CharField(
        max_length=50,
        default="Asia/Shanghai",
        verbose_name="时区",
        db_comment="用户默认时区",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
        db_comment="记录创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
        db_comment="记录最后更新时间",
    )

    class Meta:
        db_table = "user_profile"
        db_table_comment = "用户扩展资料表"
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"

    def __str__(self) -> str:
        return self.nickname or self.user.username
