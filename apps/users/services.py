# 导入 Django 数据库事务工具。
from django.db import transaction

# 导入 Django 用户模型。
from django.contrib.auth.models import User

# 导入 SimpleJWT Refresh Token。
from rest_framework_simplejwt.tokens import RefreshToken

# 导入 SimpleJWT Token 异常。
from rest_framework_simplejwt.exceptions import TokenError

# 导入系统统一业务异常。
from common.exceptions.business import BusinessException

# 导入用户扩展资料模型。
from .models import UserProfile


class AuthService:
    """
    用户认证服务。

    负责封装与认证相关的通用业务逻辑，
    当前主要用于统一生成 JWT Token。
    """

    @staticmethod
    def generate_tokens(user: User) -> dict:
        """
         为用户生成 Access Token 和 Refresh Token。

        :param user: Django 用户对象
        :return: 包含 access_token、refresh_token、token_type 的字典
        """

        # 为当前用户生成 Refresh Token。
        # Access Token 可以通过 refresh.access_token 获取。
        refresh = RefreshToken.for_user(user)

        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "token_type": "Bearer",
        }

    @staticmethod
    def logout(refresh_token: str) -> None:
        """
        用户退出登录。

        将 Refresh Token 加入黑名单。
        """

        try:
            # 将字符串 Token 转换成 RefreshToken 对象。
            token = RefreshToken(refresh_token)

            # 将 Refresh Token 加入黑名单。
            token.blacklist()

        except TokenError:
            # Refresh Token 已过期、无效或者已进入黑名单。
            raise BusinessException("Refresh Token 无效或已失效")


class UserService:
    """
    用户业务服务。

    负责处理用户资料相关业务逻辑。
    """

    @staticmethod
    def get_current_user_data(user) -> dict:
        """
        获取当前登录用户完整资料。

        :param user: request.user
        :return: 用户资料字典
        """

        # 尝试获取当前用户关联的 UserProfile。
        profile = getattr(user, "profile", None)

        # 如果当前用户不存在 UserProfile，
        # 返回基础用户信息。
        #
        # 正常注册用户都会存在 UserProfile，
        # 主要用于兼容之前手动创建的超级管理员。
        if profile is None:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": "",
                "phone": None,
                "avatar": None,
                "gender": 0,
                "gender_display": "未知",
                "birthday": None,
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }

        # 如果用户上传了头像，
        # 获取头像 URL。
        avatar_url = profile.avatar.url if profile.avatar else None

        # 返回完整用户信息。
        return {
            # Django User ID。
            "id": user.id,
            # 用户名。
            "username": user.username,
            # 邮箱。
            "email": user.email,
            # 昵称。
            "nickname": profile.nickname,
            # 手机号。
            "phone": profile.phone,
            # 头像。
            "avatar": avatar_url,
            # 性别数字值。
            "gender": profile.gender,
            # 性别中文名称。
            # Django choices 字段会自动生成：
            # get_gender_display()
            "gender_display": (profile.get_gender_display()),
            # 生日。
            "birthday": profile.birthday,
            # 默认货币。
            "currency": profile.currency,
            # 时区。
            "timezone": profile.timezone,
        }

    @staticmethod
    @transaction.atomic
    def update_current_user(
        user,
        validated_data: dict,
    ) -> dict:
        """
        修改当前登录用户资料。

        修改涉及：
        1. auth_user 表；
        2. user_profile 表。

        使用 transaction.atomic 保证：
        任意一步失败，两张表的修改都会一起回滚。

        :param user: 当前登录用户 request.user
        :param validated_data: Serializer 校验后的数据
        :return: 修改后的用户资料
        """

        # 获取当前用户的 UserProfile。
        #
        # 正常通过注册接口创建的用户一定存在 Profile。
        # 对于之前手动创建的超级管理员，
        # 使用 get_or_create 进行兼容。
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # ==============================
        # 修改 auth_user 表
        # ==============================

        # 判断前端是否传入 email。
        if "email" in validated_data:

            # 修改 Django User 邮箱。
            user.email = validated_data["email"]

        # 保存 auth_user。
        #
        # update_fields 可以避免执行无意义字段更新。
        user.save(
            update_fields=[
                "email",
            ]
        )

        # ==============================
        # 修改 user_profile 表
        # ==============================

        # 如果传入 nickname，
        # 则修改昵称。
        if "nickname" in validated_data:
            profile.nickname = validated_data["nickname"]

        # 如果传入 phone，
        # 则修改手机号。
        if "phone" in validated_data:
            profile.phone = validated_data["phone"]

        # 如果传入 gender，
        # 则修改性别。
        if "gender" in validated_data:
            profile.gender = validated_data["gender"]

        # 如果传入 birthday，
        # 则修改生日。
        if "birthday" in validated_data:
            profile.birthday = validated_data["birthday"]

        # 如果传入 currency，
        # 则修改默认货币。
        if "currency" in validated_data:
            profile.currency = validated_data["currency"]

        # 如果传入 timezone，
        # 则修改时区。
        if "timezone" in validated_data:
            profile.timezone = validated_data["timezone"]

        # 保存用户扩展资料。
        profile.save()

        # 修改成功后，
        # 统一调用已经存在的获取用户资料方法，
        # 返回最新的数据。
        return UserService.get_current_user_data(user)

    @staticmethod
    @transaction.atomic
    def change_password(
        user,
        new_password: str,
    ) -> dict:
        """
        修改当前用户密码，并重新签发 JWT。

        修改密码以后：
        1. 旧 JWT 因密码哈希变化而失效；
        2. 基于新的用户密码状态重新生成 JWT；
        3. 将新 Token 返回给前端继续使用。

        :param user:
            当前登录用户。

        :param new_password:
            已通过 Serializer 校验的新密码。

        :return:
            新签发的 JWT Token。
        """

        # 使用 Django 官方 set_password()。
        #
        # set_password() 会按照 Django 当前配置的
        # 密码哈希算法安全处理原始密码。
        #
        # 绝对不能：
        # user.password = new_password
        user.set_password(new_password)

        # 只更新 password 字段。
        user.save(
            update_fields=[
                "password",
            ]
        )

        # 密码保存完成以后，
        # 此时 user.password 已经变成新的密码哈希。
        #
        # 再基于当前用户生成 JWT，
        # 新 Token 会携带新的密码撤销校验信息。
        tokens = AuthService.generate_tokens(user)

        # 返回新的 Token。
        return tokens

    @staticmethod
    @transaction.atomic
    def update_avatar(
        user,
        avatar,
    ) -> dict:
        """
        修改当前用户头像。

        :param user:
            当前登录用户。

        :param avatar:
            已通过 Serializer 校验的图片文件。

        :return:
            修改后的用户资料。
        """

        # 获取当前用户资料。
        #
        # 正常注册用户已经存在 UserProfile。
        # get_or_create 主要兼容之前手动创建的管理员。
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # 保存旧头像引用。
        #
        # 后面新头像保存成功以后，
        # 再删除旧文件。
        old_avatar = profile.avatar

        # 将新头像赋值给用户资料。
        profile.avatar = avatar

        # 保存头像字段。
        profile.save(
            update_fields=[
                "avatar",
                "updated_at",
            ]
        )

        # ==============================
        # 清理旧头像文件
        # ==============================

        # 当前用户之前存在头像时，
        # 将旧文件从存储系统中删除。
        if old_avatar:

            # save=False 表示：
            # 删除文件以后不要再次保存 Model。
            old_avatar.delete(save=False)

        # 返回修改后的完整用户资料。
        return UserService.get_current_user_data(user)
