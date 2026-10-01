from django.db import transaction


from .models import UserPreference


class PreferenceService:
    """
    用户偏好设置业务服务。

    负责：

    1. 获取用户偏好；
    2. 自动创建默认偏好；
    3. 修改用户偏好。
    """

    @staticmethod
    def get_or_create_preference(
        user,
    ) -> UserPreference:
        """
        获取用户偏好。

        业务规则：

        1. 一个用户只有一份偏好配置；
        2. 如果首次访问不存在，
           自动创建默认配置。

        默认值：

        currency:
            CNY

        theme:
            system

        page_size:
            20

        budget_reminder_enabled:
            True

        budget_reminder_threshold:
            80
        """

        preference, created = UserPreference.objects.get_or_create(
            user=user,
            defaults={
                "currency": "CNY",
                "theme": (UserPreference.ThemeChoice.SYSTEM),
                "page_size": 20,
                "budget_reminder_enabled": True,
                "budget_reminder_threshold": 80,
            },
        )

        return preference

    @staticmethod
    @transaction.atomic
    def update_preference(
        user,
        validated_data: dict,
    ) -> UserPreference:
        """
        修改用户偏好。

        修改范围：

        1. 默认货币；
        2. 主题模式；
        3. 分页数量；
        4. 预算提醒开关；
        5. 预算提醒阈值；
        6. 默认账户。

        """

        # ======================================
        # 获取用户偏好
        # ======================================

        preference = PreferenceService.get_or_create_preference(
            user=user,
        )

        # ======================================
        # 更新字段
        # ======================================
        #
        # 使用 setattr，
        # 避免大量 if 判断。
        #
        # Serializer 已经负责字段校验。
        #
        # ======================================

        for field, value in validated_data.items():

            setattr(
                preference,
                field,
                value,
            )

        # ======================================
        # 保存修改
        # ======================================

        preference.save()

        return preference
