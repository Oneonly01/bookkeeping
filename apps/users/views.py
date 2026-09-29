from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.users.password_reset_service import PasswordResetService
from common.response import ApiResponse

from .serializers import (
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetSendCodeSerializer,
    PasswordResetSerializer,
    PasswordResetVerifyCodeSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    UpdateUserProfileSerializer,
)
from .services import AuthService, UserService


class LoginView(APIView):
    """
    用户登录接口。

    请求方式：
        POST

    请求地址：
        /api/v1/auth/login/

    请求参数：
        {
            "username": "admin",
            "password": "123456"
        }
    """

    # 登录接口必须允许匿名用户访问。
    permission_classes = [AllowAny]

    def post(self, request):
        """
        用户登录。
        """

        # 1. 参数校验 + 用户身份认证
        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # 2. 获取认证成功的用户对象
        user = serializer.validated_data["user"]

        # 3. 统一通过 Service 生成 JWT
        tokens = AuthService.generate_tokens(user)

        # 4. 返回用户基础信息
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }

        # 如果已经存在 UserProfile，
        # 就同时返回用户业务资料。
        if hasattr(user, "profile"):
            user_data.update(
                {
                    "nickname": (user.profile.nickname),
                    "phone": user.profile.phone,
                    "avatar": (
                        user.profile.avatar.url if user.profile.avatar else None
                    ),
                }
            )

        # 5. 使用系统统一响应格式
        return ApiResponse.success(
            message="登录成功",
            data={
                **tokens,
                "user": user_data,
            },
        )


# 定义 Refresh Token 刷新接口。
class RefreshTokenView(APIView):
    """
    JWT Refresh Token 刷新接口。

    请求方式：
        POST

    请求地址：
        /api/v1/auth/refresh/

    主要职责：
        使用 Refresh Token
        获取新的 Access Token。
    """

    # Refresh Token 接口不依赖 Access Token。
    #
    # 例如：
    # Access Token 已经过期时，
    # 前端仍然需要调用这个接口获取新的 Access Token。
    #
    # 因此这里必须允许匿名访问。
    permission_classes = [AllowAny]

    # 定义 POST 请求处理方法。
    def post(self, request):
        """
        使用 Refresh Token 获取新的 Token。
        """

        # 创建 RefreshTokenSerializer。
        serializer = RefreshTokenSerializer(
            # 将客户端请求数据传入序列化器。
            data=request.data
        )

        # 校验客户端传入的 Refresh Token。
        #
        # 如果 Token：
        # - 为空
        # - 格式错误
        # - 签名错误
        # - 已经过期
        #
        # 序列化器会抛出异常，
        # 再由全局异常处理器统一返回。
        serializer.is_valid(raise_exception=True)

        # 使用系统统一响应结构返回刷新结果。
        return ApiResponse.success(
            # 返回成功提示。
            message="Token 刷新成功",
            # 返回刷新后的 Token 数据。
            data={
                # 从序列化器校验后的数据中
                # 获取新生成的 Access Token。
                "access_token": (serializer.validated_data["access_token"]),
                # 获取 Refresh Token。
                #
                # 如果以后开启 Refresh Token 轮换，
                # 这里可以返回新的 Refresh Token。
                "refresh_token": (serializer.validated_data["refresh_token"]),
                # Token 类型固定使用 Bearer。
                #
                # 前端请求其他受保护接口时：
                #
                # Authorization: Bearer <access_token>
                "token_type": "Bearer",
            },
        )


# 定义用户注册接口。
class RegisterView(APIView):
    """
    用户注册接口。

    请求方式：
        POST

    请求地址：
        /api/v1/auth/register/
    """

    # 注册接口必须允许未登录用户访问。
    permission_classes = [AllowAny]

    # 处理 POST 请求。
    def post(self, request):
        """
        创建新用户。
        """

        # 创建注册序列化器。
        serializer = RegisterSerializer(
            # 将前端提交的数据传进去。
            data=request.data
        )

        # 执行参数校验。
        #
        # 校验失败会自动抛异常，
        # 交给全局异常处理器统一返回。
        serializer.is_valid(raise_exception=True)

        # 调用序列化器 create() 创建用户。
        user = serializer.save()

        # 注册成功后直接生成 JWT。
        #
        # 这样用户注册完成后不用再登录一次。
        tokens = AuthService.generate_tokens(user)

        # 返回统一响应。
        return ApiResponse.success(
            # 提示信息。
            message="注册成功",
            # 返回业务数据。
            data={
                # 展开 JWT 数据。
                **tokens,
                # 返回用户基础信息。
                "user": {
                    # 用户ID。
                    "id": user.id,
                    # 用户名。
                    "username": user.username,
                    # 邮箱。
                    "email": user.email,
                    # 用户昵称。
                    "nickname": (user.profile.nickname),
                    # 用户手机号。
                    "phone": user.profile.phone,
                },
            },
        )


# 定义当前登录用户信息接口。
class CurrentUserView(APIView):
    """
    当前登录用户信息接口。

    请求方式：
        GET

    请求地址：
        /api/v1/users/me/

    注意：
        该接口必须携带有效 Access Token。
    """

    # 这里不用写 permission_classes。
    #
    # 因为 settings.py 中已经全局配置：
    #
    # DEFAULT_PERMISSION_CLASSES =
    # IsAuthenticated
    #
    # 所以默认情况下该接口必须登录。

    # 定义 GET 请求。
    def get(self, request):
        """
        获取当前登录用户资料。
        """

        # request.user 是 JWTAuthentication
        # 根据 Access Token 自动解析出的当前用户。
        user = request.user

        # 调用统一 UserService
        # 获取当前登录用户完整资料。
        user_data = UserService.get_current_user_data(user)

        # 返回系统统一响应结构。
        return ApiResponse.success(
            # 成功提示。
            message="获取用户信息成功",
            # 返回当前登录用户资料。
            data=user_data,
        )

    # ==============================
    # 修改当前用户资料
    # ==============================

    def put(self, request):
        """
        修改当前登录用户资料。
        """

        # 创建用户资料修改序列化器。
        serializer = UpdateUserProfileSerializer(
            # 接收前端提交的数据。
            data=request.data,
            # 将 request 放入 context。
            #
            # Serializer 后续需要通过 request.user
            # 判断邮箱、手机号是否属于当前用户。
            context={
                "request": request,
            },
        )

        # 执行参数校验。
        #
        # 如果参数错误，
        # 直接抛出 ValidationError，
        # 由全局异常处理器统一处理。
        serializer.is_valid(raise_exception=True)

        # 调用用户 Service。
        #
        # Service 负责真正的数据修改和数据库事务。
        user_data = UserService.update_current_user(
            # 当前登录用户。
            user=request.user,
            # Serializer 校验后的数据。
            validated_data=(serializer.validated_data),
        )

        # 返回统一成功响应。
        return ApiResponse.success(
            message="用户信息修改成功",
            data=user_data,
        )


# 定义修改密码接口。
class ChangePasswordView(APIView):
    """
    修改当前用户密码接口。

    请求方式：
        PUT

    请求地址：
        /api/v1/users/password/

    功能：
        1. 验证旧密码；
        2. 校验新密码；
        3. 修改密码；
        4. 废弃旧 JWT；
        5. 返回新的 JWT。
    """

    def put(self, request):
        """
        修改当前登录用户密码。
        """

        # 创建修改密码序列化器。
        serializer = ChangePasswordSerializer(
            # 接收前端请求参数。
            data=request.data,
            # 将当前 request 传给 Serializer。
            #
            # Serializer 需要通过 request.user
            # 验证旧密码。
            context={
                "request": request,
            },
        )

        # 执行参数校验。
        #
        # 包括：
        # - 旧密码是否正确
        # - 两次新密码是否一致
        # - 新旧密码是否相同
        # - 新密码是否符合 Django 密码规则
        serializer.is_valid(raise_exception=True)

        # 获取已经校验成功的新密码。
        new_password = serializer.validated_data["new_password"]

        # 调用 Service 修改密码。
        #
        # Service 修改密码成功以后，
        # 会基于新的密码状态重新生成 JWT。
        tokens = UserService.change_password(
            user=request.user,
            new_password=new_password,
        )

        # 返回修改成功以及新的 Token。
        return ApiResponse.success(
            message="密码修改成功,请使用新密码重新登录",
            data={
                # 新 Access Token。
                "access_token": tokens["access_token"],
                # 新 Refresh Token。
                "refresh_token": tokens["refresh_token"],
                # JWT 类型。
                "token_type": tokens["token_type"],
            },
        )


# 定义用户退出登录接口。
class LogoutView(APIView):
    """
    用户退出登录接口。

    请求方式：
        POST

    请求地址：
        /api/v1/auth/logout/

    功能：
        将当前 Refresh Token 加入黑名单，
        防止退出登录以后再次使用该 Token 刷新登录状态。
    """

    def post(self, request):
        """
        用户退出登录。
        """

        # 创建退出登录参数序列化器。
        serializer = LogoutSerializer(
            # 接收客户端请求 Body。
            data=request.data
        )

        # 执行参数校验。
        #
        # 参数错误时直接抛出异常，
        # 交给全局异常处理器。
        serializer.is_valid(raise_exception=True)

        # 获取已经校验后的 Refresh Token。
        refresh_token = serializer.validated_data["refresh_token"]

        # 调用统一认证 Service
        # 执行 Refresh Token 黑名单处理。
        AuthService.logout(refresh_token=refresh_token)

        # 返回统一成功响应。
        return ApiResponse.success(
            message="退出登录成功",
            data=None,
        )


class AvatarUploadView(APIView):
    """
    当前登录用户头像上传接口。

    请求方式：
        POST

    请求地址：
        /api/v1/users/avatar/

    请求格式：
        multipart/form-data
    """

    def post(self, request):
        """
        上传或者替换当前用户头像。
        """

        # 创建头像上传序列化器。
        serializer = AvatarUploadSerializer(data=request.data)

        # 执行图片校验。
        serializer.is_valid(raise_exception=True)

        # 获取经过校验的头像文件。
        avatar = serializer.validated_data["avatar"]

        # 调用用户 Service
        # 保存并替换当前用户头像。
        user_data = UserService.update_avatar(
            user=request.user,
            avatar=avatar,
        )

        # 返回系统统一响应。
        return ApiResponse.success(
            message="头像上传成功",
            data=user_data,
        )


class PasswordResetSendCodeView(APIView):
    """
    发送找回密码验证码。
    """

    # 用户忘记密码时没有 Token，
    # 所以该接口必须允许匿名访问。
    permission_classes = [AllowAny]

    def post(
        self,
        request,
    ):
        """
        发送验证码。
        """

        serializer = PasswordResetSendCodeSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user, code = PasswordResetService.send_code(
            account=(serializer.validated_data["account"])
        )

        data = {"account": (serializer.validated_data["account"])}

        # ======================================
        # 开发环境临时返回验证码
        # ======================================
        #
        # 注意：
        # 正式生产环境绝对不能返回验证码。
        #
        # 现在项目还没有接短信/邮件服务，
        # 为了方便 Apifox 调试，
        # 暂时返回 debug_code。
        #
        # 等后面部署时必须删除。
        # ======================================

        from django.conf import settings

        if settings.DEBUG:
            data["debug_code"] = code

        return ApiResponse.success(
            message="验证码发送成功",
            data=data,
        )


class PasswordResetVerifyCodeView(APIView):
    """
    校验找回密码验证码。
    """

    permission_classes = [AllowAny]

    def post(
        self,
        request,
    ):
        """
        验证验证码。
        """

        serializer = PasswordResetVerifyCodeSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        reset_token = PasswordResetService.verify_code(
            account=(serializer.validated_data["account"]),
            code=(serializer.validated_data["code"]),
        )

        return ApiResponse.success(
            message="验证码校验成功",
            data={"reset_token": (reset_token)},
        )


class PasswordResetView(APIView):
    """
    重置密码接口。
    """

    permission_classes = [AllowAny]

    def post(
        self,
        request,
    ):
        """
        使用临时凭证重置密码。
        """

        serializer = PasswordResetSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        PasswordResetService.reset_password(
            reset_token=(serializer.validated_data["reset_token"]),
            new_password=(serializer.validated_data["new_password"]),
        )

        return ApiResponse.success(
            message="密码重置成功",
            data=None,
        )
