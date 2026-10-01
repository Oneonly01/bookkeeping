from rest_framework import serializers

from .models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    用户偏好设置返回序列化器。

    用于：

    1. 获取用户当前偏好；
    2. 修改用户偏好。

    包含：

    - 默认货币；
    - 主题模式；
    - 分页数量；
    - 预算提醒开关；
    - 预算提醒阈值；
    - 默认账户。
    """

    # ==========================================
    # 主题显示名称
    # ==========================================
    #
    # 数据库存储：
    #
    # light
    # dark
    # system
    #
    # 返回时额外提供中文名称。
    # ==========================================

    theme_display = serializers.CharField(
        source="get_theme_display",
        read_only=True,
    )

    # ==========================================
    # 默认账户名称
    # ==========================================
    #
    # 方便前端直接展示，
    # 避免再次请求账户详情。
    # ==========================================

    default_account_name = serializers.CharField(
        source="default_account.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = UserPreference

        fields = [
            # 用户偏好 ID
            "id",
            # 默认货币
            "currency",
            # 主题模式
            "theme",
            # 主题中文名称
            "theme_display",
            # 分页数量
            "page_size",
            # 预算提醒开关
            "budget_reminder_enabled",
            # 预算提醒阈值
            "budget_reminder_threshold",
            # 默认账户
            "default_account",
            "default_account_name",
            # 时间字段
            "created_at",
            "updated_at",
        ]

        # ======================================
        # 只读字段
        # ======================================
        #
        # 用户不能直接修改：
        #
        # id
        # 创建时间
        # 更新时间
        #
        # ======================================

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    # ==========================================
    # 校验预算提醒阈值
    # ==========================================
    #
    # 示例：
    #
    # 80
    # 表示预算使用 80% 时提醒。
    #
    # 限制：
    #
    # 1~100
    #
    # ==========================================

    def validate_budget_reminder_threshold(
        self,
        value,
    ):

        if value < 1 or value > 100:
            raise serializers.ValidationError("预算提醒阈值必须在1-100之间")

        return value

    # ==========================================
    # 校验分页数量
    # ==========================================
    #
    # 防止用户设置过大分页，
    # 导致接口返回数据压力过大。
    #
    # ==========================================

    def validate_page_size(
        self,
        value,
    ):

        if value < 5 or value > 100:
            raise serializers.ValidationError("分页数量必须在5-100之间")

        return value
