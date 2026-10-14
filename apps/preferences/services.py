from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Account
from apps.users.models import UserProfile
from common.exceptions import BusinessException

from .models import UserPreference


class PreferenceService:
    """
    用户偏好设置业务服务。

    默认账户以有效账户的is_default为准；偏好中的外键同步保存。
    默认货币以偏好为准，并同步用户资料；仅影响展示，不做汇率换算。
    """

    @staticmethod
    def lock_user(user):
        """在事务中锁定用户，串行处理默认账户切换。"""
        get_user_model().objects.select_for_update().get(pk=user.pk)

    @staticmethod
    def get_or_create_preference(user) -> UserPreference:
        """
        获取偏好并修正默认账户快照。

        首次创建时继承已有用户资料的货币。
        默认账户只能属于当前用户且未删除、已启用。
        """
        # ======================================
        # 读取有效默认账户 / 默认货币
        # ======================================
        account = Account.objects.filter(
            user=user,
            is_default=True,
            is_deleted=False,
            is_active=True,
        ).order_by("id").first()
        currency = UserProfile.objects.filter(user=user).values_list(
            "currency", flat=True,
        ).first() or "CNY"

        preference, created = UserPreference.objects.get_or_create(
            user=user,
            defaults={
                "currency": currency,
                "default_account": account,
            },
        )
        account_id = account.id if account else None
        if preference.default_account_id != account_id:
            preference.default_account = account
            preference.save(update_fields=["default_account", "updated_at"])
        return preference

    @staticmethod
    def get_default_account(user):
        """新增账单未传账户时，使用当前有效默认账户。"""
        preference = PreferenceService.get_or_create_preference(user)
        if preference.default_account_id is None:
            raise BusinessException("请指定账户或先设置有效默认账户")
        return preference.default_account

    @staticmethod
    @transaction.atomic
    def update_preference(user, validated_data: dict) -> UserPreference:
        """
        修改偏好并同步账户和用户资料。

        传default_account=null时清除默认账户；
        未传字段保持原值。
        """
        PreferenceService.lock_user(user)
        data = validated_data.copy()
        if "currency" in data:
            currency = data["currency"].strip().upper()
            if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
                raise BusinessException("货币代码必须是三位字母，例如CNY")
            data["currency"] = currency
        preference = PreferenceService.get_or_create_preference(user)

        # ======================================
        # 设置默认账户，同时维护账户列表中的默认标识
        # ======================================
        if "default_account" in data:
            account = data["default_account"]
            if account is not None:
                account = Account.objects.filter(
                    pk=account.pk,
                    user=user,
                    is_deleted=False,
                    is_active=True,
                ).first()
                if account is None:
                    raise BusinessException("默认账户不存在或不可用")
            Account.objects.filter(user=user, is_default=True).update(
                is_default=False,
            )
            if account is not None:
                account.is_default = True
                account.save(update_fields=["is_default", "updated_at"])
            data["default_account"] = account

        # ======================================
        # 保存偏好 / 同步用户资料货币
        # ======================================
        for field, value in data.items():
            setattr(preference, field, value)
        preference.save()
        if "currency" in data:
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"currency": preference.currency},
            )
        return preference
