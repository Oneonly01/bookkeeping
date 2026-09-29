import hashlib
import random
import secrets

from django.core.cache import cache


class VerificationCodeService:
    """
    验证码业务工具。

    用途：

    1. 生成验证码；
    2. Redis 临时存储验证码；
    3. 校验验证码；
    4. 生成密码重置临时 Token。
    """

    # 验证码有效时间：5 分钟。
    CODE_TIMEOUT = 5 * 60

    # 重置密码 Token 有效时间：10 分钟。
    RESET_TOKEN_TIMEOUT = 10 * 60

    # 验证码长度。
    CODE_LENGTH = 6

    @staticmethod
    def _hash_value(
        value: str,
    ):
        """
        对验证码进行 SHA256 哈希。

        Redis 中不直接存储明文验证码。
        """

        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def generate_code(
        cls,
    ):
        """
        生成 6 位数字验证码。
        """

        start = 10 ** (cls.CODE_LENGTH - 1)

        end = (10**cls.CODE_LENGTH) - 1

        return str(
            random.SystemRandom().randint(
                start,
                end,
            )
        )

    @classmethod
    def save_code(
        cls,
        user_id: int,
        code: str,
    ):
        """
        保存找回密码验证码。
        """

        cache_key = f"password_reset_code:{user_id}"

        cache.set(
            cache_key,
            cls._hash_value(code),
            timeout=cls.CODE_TIMEOUT,
        )

    @classmethod
    def verify_code(
        cls,
        user_id: int,
        code: str,
    ):
        """
        校验验证码。

        验证成功后立即删除验证码，
        防止重复使用。
        """

        cache_key = f"password_reset_code:{user_id}"

        saved_code = cache.get(cache_key)

        if saved_code is None:
            return False

        current_code = cls._hash_value(code)

        if not secrets.compare_digest(
            saved_code,
            current_code,
        ):
            return False

        # 验证码一次性使用。
        cache.delete(cache_key)

        return True

    @classmethod
    def create_reset_token(
        cls,
        user_id: int,
    ):
        """
        创建密码重置临时 Token。
        """

        token = secrets.token_urlsafe(32)

        cache_key = f"password_reset_token:{token}"

        cache.set(
            cache_key,
            user_id,
            timeout=(cls.RESET_TOKEN_TIMEOUT),
        )

        return token

    @classmethod
    def get_reset_user_id(
        cls,
        token: str,
    ):
        """
        根据重置 Token 获取用户 ID。
        """

        cache_key = f"password_reset_token:{token}"

        return cache.get(cache_key)

    @classmethod
    def delete_reset_token(
        cls,
        token: str,
    ):
        """
        删除已经使用的重置 Token。
        """

        cache_key = f"password_reset_token:{token}"

        cache.delete(cache_key)
