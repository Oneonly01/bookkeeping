from django.contrib.auth import (
    get_user_model,
)
from django.db import transaction
from django.db.models import Q

from common.exceptions import (
    BusinessException,
)
from common.utils.verification_code import (
    VerificationCodeService,
)

User = get_user_model()


class PasswordResetService:
    """
    找回密码业务服务。
    """

    @staticmethod
    def find_user(
        account: str,
    ):
        """
        根据账号或邮箱查询用户。

        当前项目使用 Django 默认 User，
        所以这里先支持：

        username
        email

        如果你的手机号存放在 UserProfile，
        后面可以继续把手机号查询条件加进来。
        """

        user = User.objects.filter(Q(username=account) | Q(email=account)).first()

        if user is None:
            raise BusinessException("用户不存在")

        if not user.is_active:
            raise BusinessException("当前用户已被禁用")

        return user

    @classmethod
    def send_code(
        cls,
        account: str,
    ):
        """
        生成并保存找回密码验证码。
        """

        user = cls.find_user(account)

        # 生成验证码。
        code = VerificationCodeService.generate_code()

        # 保存到 Redis。
        (
            VerificationCodeService.save_code(
                user_id=user.id,
                code=code,
            )
        )

        return user, code

    @classmethod
    def verify_code(
        cls,
        account: str,
        code: str,
    ):
        """
        验证找回密码验证码。

        成功后生成一次性 reset_token。
        """

        user = cls.find_user(account)

        valid = VerificationCodeService.verify_code(
            user_id=user.id,
            code=code,
        )

        if not valid:
            raise BusinessException("验证码错误或已过期")

        reset_token = VerificationCodeService.create_reset_token(
            user_id=user.id,
        )

        return reset_token

    @staticmethod
    @transaction.atomic
    def reset_password(
        reset_token: str,
        new_password: str,
    ):
        """
        重置用户密码。
        """

        user_id = VerificationCodeService.get_reset_user_id(reset_token)

        if user_id is None:
            raise BusinessException("重置凭证无效或已过期")

        # 锁定用户。
        user = (
            User.objects.select_for_update()
            .filter(
                id=user_id,
                is_active=True,
            )
            .first()
        )

        if user is None:
            raise BusinessException("用户不存在或已禁用")

        # Django set_password 会进行密码哈希。
        user.set_password(new_password)

        user.save(
            update_fields=[
                "password",
            ]
        )

        # Token 一次性使用。
        (VerificationCodeService.delete_reset_token(reset_token))

        return user
