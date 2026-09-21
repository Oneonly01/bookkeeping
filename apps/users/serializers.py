from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.users.models import UserProfile
from common.exceptions import BusinessException
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

# 导入 Django 官方密码强度校验器。
from django.contrib.auth.password_validation import validate_password

# 导入 Django 参数校验异常。
from django.core.exceptions import ValidationError as DjangoValidationError

# 导入 Django 内置用户模型获取方法。
from django.contrib.auth import get_user_model

# 导入数据库事务工具。
from django.db import transaction


class LoginSerializer(serializers.Serializer):
    """
    用户登录序列化器。

    职责：
    1. 校验用户名和密码参数；
    2. 调用 Django 官方认证体系进行身份验证；
    3. 返回验证成功的 User 对象。

    注意：
    当前版本使用 username + password 登录。
    后续可以扩展手机号、邮箱登录。
    """

    username = serializers.CharField(
        max_length=150,
        required=True,
        trim_whitespace=True,
        error_messages={
            "required": "请输入用户名",
            "blank": "用户名不能为空",
            "max_length": "用户名长度不能超过150个字符",
        },
    )

    password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "required": "请输入密码",
            "blank": "密码不能为空",
        },
    )

    def validate(self, attrs):
        """
        联合校验用户名和密码。
        """

        username = attrs["username"]
        password = attrs["password"]

        # 使用 Django authenticate 进行认证。
        #
        # 不允许自己读取 password 字段后直接比较，
        # 因为 Django 保存的是密码哈希值。
        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            raise BusinessException("用户名或密码错误")

        # 被禁用用户禁止登录。
        if not user.is_active:
            raise BusinessException("当前账号已被禁用")

        attrs["user"] = user

        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    """
    Refresh Token 刷新序列化器。

    职责：
    1. 校验 refresh_token 是否传入；
    2. 校验 Refresh Token 是否有效；
    3. 生成新的 Access Token；
    4. 根据配置决定是否返回新的 Refresh Token。
    """

    refresh_token = serializers.CharField(
        required=True,
        trim_whitespace=True,
        error_messages={
            "required": "请提供 Refresh Token",
            "blank": "Refresh Token 不能为空",
        },
    )

    def validate(self, attrs):
        """
        校验并刷新 Token。
        """

        refresh_token = attrs["refresh_token"]

        try:
            # 将字符串形式的 Refresh Token
            # 转换为 SimpleJWT 的 Token 对象。
            refresh = RefreshToken(refresh_token)

            # 生成新的 Access Token。
            access_token = str(refresh.access_token)

            attrs["access_token"] = access_token

            # 当前配置开启：
            # ROTATE_REFRESH_TOKENS = True
            #
            # 因此刷新后同时返回新的 Refresh Token。
            attrs["refresh_token"] = str(refresh)

        except TokenError:
            # Token 过期、格式错误或签名无效，
            # 统一作为业务异常返回。
            raise BusinessException("Refresh Token 无效或已过期")

        return attrs


# 获取当前项目实际使用的用户模型。
User = get_user_model()


# 定义用户注册序列化器。
class RegisterSerializer(serializers.Serializer):
    """
    用户注册序列化器。

    主要职责：
    1. 校验注册参数；
    2. 校验用户名、邮箱、手机号是否重复；
    3. 创建 Django User；
    4. 创建对应 UserProfile；
    5. 保证整个注册过程具有事务一致性。
    """

    # 用户名。
    username = serializers.CharField(
        # Django 默认用户名最大长度为 150。
        max_length=150,
        # 必填。
        required=True,
        # 自动去除首尾空格。
        trim_whitespace=True,
        # 自定义错误提示。
        error_messages={
            "required": "请输入用户名",
            "blank": "用户名不能为空",
            "max_length": "用户名长度不能超过150个字符",
        },
    )

    # 邮箱。
    email = serializers.EmailField(
        # 必填。
        required=True,
        # 自定义错误提示。
        error_messages={
            "required": "请输入邮箱",
            "blank": "邮箱不能为空",
            "invalid": "邮箱格式不正确",
        },
    )

    # 手机号。
    phone = serializers.CharField(
        # 当前按照中国大陆手机号长度设计。
        max_length=11,
        # 必填。
        required=True,
        # 去除首尾空格。
        trim_whitespace=True,
        # 自定义错误提示。
        error_messages={
            "required": "请输入手机号",
            "blank": "手机号不能为空",
            "max_length": "手机号格式不正确",
        },
    )

    # 昵称。
    nickname = serializers.CharField(
        # 最大长度与 UserProfile 模型一致。
        max_length=50,
        # 非必填。
        required=False,
        # 允许空字符串。
        allow_blank=True,
        # 去除首尾空格。
        trim_whitespace=True,
    )

    # 密码。
    password = serializers.CharField(
        # 密码只允许写入，不会返回给客户端。
        write_only=True,
        # 必填。
        required=True,
        # 不自动删除首尾空格。
        trim_whitespace=False,
        # 建议最低 8 位。
        min_length=8,
        # 自定义错误提示。
        error_messages={
            "required": "请输入密码",
            "blank": "密码不能为空",
            "min_length": "密码长度不能少于8位",
        },
    )

    # 确认密码。
    confirm_password = serializers.CharField(
        # 只写字段。
        write_only=True,
        # 必填。
        required=True,
        # 不删除首尾空格。
        trim_whitespace=False,
        # 自定义错误提示。
        error_messages={
            "required": "请再次输入密码",
            "blank": "确认密码不能为空",
        },
    )

    # 校验用户名。
    def validate_username(self, value):
        """
        校验用户名是否已存在。
        """

        # 判断用户名是否重复。
        if User.objects.filter(username=value).exists():

            # 重复则抛出参数校验异常。
            raise serializers.ValidationError("用户名已存在")

        # 返回校验后的用户名。
        return value

    # 校验邮箱。
    def validate_email(self, value):
        """
        校验邮箱是否已被注册。
        """

        # 使用 iexact 忽略邮箱大小写。
        if User.objects.filter(email__iexact=value).exists():

            # 邮箱重复。
            raise serializers.ValidationError("该邮箱已被注册")

        # 返回统一的小写邮箱。
        return value.lower()

    # 校验手机号。
    def validate_phone(self, value):
        """
        校验手机号格式及唯一性。
        """

        # 中国大陆手机号要求：
        # 11 位数字，并且以 1 开头。
        if len(value) != 11 or not value.isdigit() or not value.startswith("1"):
            raise serializers.ValidationError("手机号格式不正确")

        # 检查 UserProfile 是否已经存在相同手机号。
        if UserProfile.objects.filter(phone=value).exists():
            raise serializers.ValidationError("该手机号已被注册")

        # 返回手机号。
        return value

    # 对多个字段做联合校验。
    def validate(self, attrs):
        """
        校验两次输入的密码是否一致。
        """

        # 获取密码。
        password = attrs.get("password")

        # 获取确认密码。
        confirm_password = attrs.get("confirm_password")

        # 两次密码不一致。
        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": ("两次输入的密码不一致")}
            )

        # 返回校验后的数据。
        return attrs

    # 创建用户。
    @transaction.atomic
    def create(self, validated_data):
        """
        创建 User 和 UserProfile。

        transaction.atomic 保证：
        任意一步失败都会整体回滚。
        """

        # 从校验后的数据中移除确认密码。
        validated_data.pop("confirm_password")

        # 取出密码。
        password = validated_data.pop("password")

        # 取出手机号。
        phone = validated_data.pop("phone")

        # 取出昵称。
        nickname = validated_data.pop(
            "nickname",
            "",
        )

        # 使用 create_user 创建 Django 用户。
        #
        # create_user 会自动对密码进行安全哈希，
        # 不能使用 User.objects.create() 直接保存明文密码。
        user = User.objects.create_user(
            # 用户名。
            username=validated_data["username"],
            # 邮箱。
            email=validated_data["email"],
            # 原始密码。
            password=password,
        )

        # 创建用户扩展资料。
        UserProfile.objects.create(
            # 关联刚刚创建的 Django User。
            user=user,
            # 用户手机号。
            phone=phone,
            # 用户昵称。
            nickname=nickname,
        )

        # 返回创建成功的 User 对象。
        return user


# 定义当前用户信息序列化器。
class UserProfileSerializer(serializers.Serializer):
    """
    当前登录用户信息序列化器。

    主要用于：
    GET /api/v1/users/me/
    """

    # Django User 主键 ID。
    id = serializers.IntegerField(read_only=True)

    # 用户名。
    username = serializers.CharField(read_only=True)

    # 邮箱。
    email = serializers.EmailField(read_only=True)

    # 用户昵称。
    nickname = serializers.CharField(read_only=True)

    # 手机号。
    phone = serializers.CharField(read_only=True, allow_null=True)

    # 头像 URL。
    avatar = serializers.CharField(read_only=True, allow_null=True)

    # 性别。
    gender = serializers.IntegerField(read_only=True)

    # 性别中文名称。
    gender_display = serializers.CharField(read_only=True)

    # 生日。
    birthday = serializers.DateField(read_only=True, allow_null=True)

    # 默认货币。
    currency = serializers.CharField(read_only=True)

    # 默认时区。
    timezone = serializers.CharField(read_only=True)


# 定义当前用户资料修改序列化器。
class UpdateUserProfileSerializer(serializers.Serializer):
    """
    当前用户资料修改序列化器。

    主要职责：
    1. 校验邮箱格式；
    2. 校验手机号格式；
    3. 校验邮箱、手机号唯一性；
    4. 校验性别、生日等资料字段；
    5. 将校验后的数据交给 Service 层进行修改。
    """

    # 邮箱。
    email = serializers.EmailField(
        required=False,
        error_messages={
            "invalid": "邮箱格式不正确",
            "blank": "邮箱不能为空",
        },
    )

    # 用户昵称。
    nickname = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "max_length": "昵称长度不能超过50个字符",
        },
    )

    # 手机号。
    phone = serializers.CharField(
        max_length=11,
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=True,
    )

    # 性别。
    #
    # 与 UserProfile.Gender 对应：
    # 0 = 未知
    # 1 = 男
    # 2 = 女
    gender = serializers.ChoiceField(
        choices=UserProfile.Gender.choices,
        required=False,
    )

    # 生日。
    birthday = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "生日格式不正确，请使用 YYYY-MM-DD",
        },
    )

    # 默认货币。
    currency = serializers.CharField(
        max_length=10,
        required=False,
        trim_whitespace=True,
    )

    # 默认时区。
    timezone = serializers.CharField(
        max_length=50,
        required=False,
        trim_whitespace=True,
    )

    def __init__(self, *args, **kwargs):
        """
        初始化序列化器。

        这里保存当前登录用户，
        后续做邮箱、手机号唯一性校验时使用。
        """

        # 调用父类初始化方法。
        super().__init__(*args, **kwargs)

        # 从 serializer context 中获取当前 request。
        request = self.context.get("request")

        # 如果存在 request，
        # 保存当前登录用户。
        self.user = request.user if request else None

    def validate_email(self, value):
        """
        校验邮箱是否已被其他用户使用。
        """

        # 将邮箱统一转换为小写。
        value = value.lower()

        # 查询是否存在其他用户使用相同邮箱。
        queryset = User.objects.filter(email__iexact=value)

        # 排除当前登录用户自己。
        if self.user:
            queryset = queryset.exclude(id=self.user.id)

        # 如果仍然存在记录，
        # 说明邮箱已经被其他用户使用。
        if queryset.exists():
            raise serializers.ValidationError("该邮箱已被其他用户使用")

        # 返回校验后的邮箱。
        return value

    def validate_phone(self, value):
        """
        校验手机号格式和唯一性。
        """

        # 允许用户清空手机号。
        if value in ("", None):
            return None

        # 手机号必须：
        # 1. 长度为11位；
        # 2. 全部为数字；
        # 3. 以1开头。
        if len(value) != 11 or not value.isdigit() or not value.startswith("1"):
            raise serializers.ValidationError("手机号格式不正确")

        # 查询是否已经存在相同手机号。
        queryset = UserProfile.objects.filter(phone=value)

        # 排除当前登录用户自己的 UserProfile。
        if self.user:
            queryset = queryset.exclude(user=self.user)

        # 如果存在其他用户使用该手机号，
        # 则不允许修改。
        if queryset.exists():
            raise serializers.ValidationError("该手机号已被其他用户使用")

        # 返回校验后的手机号。
        return value


# 定义当前用户修改密码序列化器
class ChangePasswordSerializer(serializers.Serializer):
    """
    修改密码序列化器。

    主要职责：
    1. 校验旧密码；
    2. 校验新密码和确认密码；
    3. 调用 Django 官方密码强度校验；
    4. 禁止新密码与旧密码相同。
    """

    # 当前正在使用的旧密码。
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "required": "请输入旧密码",
            "blank": "旧密码不能为空",
        },
    )

    # 用户准备设置的新密码。
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "required": "请输入新密码",
            "blank": "新密码不能为空",
        },
    )

    # 再次输入新密码。
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "required": "请再次输入新密码",
            "blank": "确认密码不能为空",
        },
    )

    def __init__(self, *args, **kwargs):
        """
        初始化序列化器。

        从 context 中取得 request，
        方便获取当前登录用户。
        """

        # 调用父类初始化逻辑。
        super().__init__(*args, **kwargs)

        # 获取当前 HTTP 请求对象。
        request = self.context.get("request")

        # 获取当前登录用户。
        self.user = request.user if request else None

    def validate_old_password(self, value):
        """
        校验旧密码是否正确。
        """

        # 如果没有当前用户，
        # 直接判定校验失败。
        if self.user is None:
            raise serializers.ValidationError("无法获取当前登录用户")

        # 使用 Django check_password()
        # 校验旧密码。
        #
        # 不能直接：
        # value == self.user.password
        #
        # 因为数据库中的 password
        # 保存的是安全哈希值。
        if not self.user.check_password(value):
            raise serializers.ValidationError("旧密码错误")

        # 返回校验通过的旧密码。
        return value

    def validate(self, attrs):
        """
        对新密码进行联合校验。
        """

        # 获取旧密码。
        old_password = attrs["old_password"]

        # 获取新密码。
        new_password = attrs["new_password"]

        # 获取确认密码。
        confirm_password = attrs["confirm_password"]

        # ==============================
        # 两次新密码必须一致
        # ==============================

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": ("两次输入的新密码不一致")}
            )

        # ==============================
        # 新密码不能等于旧密码
        # ==============================

        if old_password == new_password:
            raise serializers.ValidationError(
                {"new_password": ("新密码不能与旧密码相同")}
            )

        # ==============================
        # Django 官方密码强度校验
        # ==============================

        try:
            # 调用 Django 官方校验器。
            #
            # 会读取 settings.py 中：
            # AUTH_PASSWORD_VALIDATORS
            #
            # 对密码长度、常见密码、
            # 与用户信息相似程度等进行校验。
            validate_password(
                password=new_password,
                user=self.user,
            )

        # Django 的 validate_password
        # 抛出的不是 DRF ValidationError，
        # 因此需要转换。
        except DjangoValidationError as exc:

            # 将 Django 的错误信息
            # 转换为 DRF 可以正常处理的格式。
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        # 所有校验通过后返回数据。
        return attrs


# 定义退出登录序列化器。
class LogoutSerializer(serializers.Serializer):
    """
    用户退出登录序列化器。

    主要职责：
    1. 接收 Refresh Token；
    2. 校验参数是否为空。

    Token 真正的黑名单处理交给 Service 层完成。
    """

    # 接收前端传来的 Refresh Token。
    refresh_token = serializers.CharField(
        # 必填。
        required=True,
        # Token 不允许为空字符串。
        allow_blank=False,
        # Token 只用于写入校验，
        # 不需要在响应中返回。
        write_only=True,
        # 不自动去除 Token 内容中的字符。
        trim_whitespace=True,
        # 自定义参数错误提示。
        error_messages={
            "required": "请提供 Refresh Token",
            "blank": "Refresh Token 不能为空",
        },
    )


class AvatarUploadSerializer(serializers.Serializer):
    """
    用户头像上传序列化器。

    负责：
    1. 校验是否上传图片；
    2. 校验图片大小；
    3. 校验图片格式。
    """

    # 接收上传的头像文件。
    avatar = serializers.ImageField(
        required=True,
        allow_null=False,
        error_messages={
            "required": "请选择头像文件",
            "null": "头像文件不能为空",
            "invalid_image": "上传的文件不是有效图片",
        },
    )

    def validate_avatar(self, value):
        """
        校验头像文件。
        """

        # ==============================
        # 文件大小限制
        # ==============================

        # 最大允许 5MB。
        max_size = 5 * 1024 * 1024

        # 如果文件超过限制，拒绝上传。
        if value.size > max_size:
            raise serializers.ValidationError("头像大小不能超过5MB")

        # ==============================
        # 图片格式限制
        # ==============================

        # 获取图片 MIME 类型。
        content_type = value.content_type

        # 系统允许的头像格式。
        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        }

        # 如果不是允许的图片格式，
        # 则拒绝上传。
        if content_type not in allowed_types:
            raise serializers.ValidationError("头像仅支持 JPG、PNG、WEBP、GIF 格式")

        # 校验通过。
        return value
