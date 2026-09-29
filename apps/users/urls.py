from django.urls import path

from .views import (
    AvatarUploadView,
    ChangePasswordView,
    CurrentUserView,
    LoginView,
    LogoutView,
    PasswordResetSendCodeView,
    PasswordResetVerifyCodeView,
    PasswordResetView,
    RefreshTokenView,
    RegisterView,
)

app_name = "users"


urlpatterns = [
    # 用户登录
    path(
        "auth/login/",
        LoginView.as_view(),
        name="login",
    ),
    # 刷新 JWT Token
    path(
        "auth/refresh/",
        RefreshTokenView.as_view(),
        name="refresh-token",
    ),
    path(
        # 最终地址：
        # /api/v1/auth/register/
        "auth/register/",
        # 注册视图。
        RegisterView.as_view(),
        # 路由名称。
        name="register",
    ),
    # 获取当前登录用户信息。
    path(
        # 最终访问地址：
        # /api/v1/users/me/
        "users/me/",
        # 当前用户视图。
        CurrentUserView.as_view(),
        # 路由名称。
        name="current-user",
    ),
    # 修改当前登录用户密码。
    path(
        # 最终地址：
        # PUT /api/v1/users/password/
        "users/password/",
        # 修改密码视图。
        ChangePasswordView.as_view(),
        # 路由名称。
        name="change-password",
    ),
    # 用户退出登录。
    path(
        # 最终地址：
        # POST /api/v1/auth/logout/
        "auth/logout/",
        # 退出登录视图。
        LogoutView.as_view(),
        # 路由名称。
        name="logout",
    ),
    # 当前用户头像上传。
    path(
        # 最终接口：
        # POST /api/v1/users/avatar/
        "users/avatar/",
        # 头像上传 View。
        AvatarUploadView.as_view(),
        # 路由名称。
        name="user-avatar",
    ),
    path(
        "password-reset/send-code/",
        PasswordResetSendCodeView.as_view(),
        name="password-reset-send-code",
    ),
    path(
        "password-reset/verify-code/",
        PasswordResetVerifyCodeView.as_view(),
        name="password-reset-verify-code",
    ),
    path(
        "password-reset/",
        PasswordResetView.as_view(),
        name="password-reset",
    ),
]
