from django.urls import path

from .views import (
    PreferenceView,
)

urlpatterns = [
    # ==========================================
    # 用户偏好设置
    # ==========================================
    #
    # GET：
    # 获取当前用户偏好。
    #
    # PUT：
    # 修改当前用户偏好。
    #
    # 说明：
    # 1. 每个用户只有一份偏好配置；
    # 2. 首次访问自动创建默认配置。
    #
    path(
        "",
        PreferenceView.as_view(),
        name="preference",
    ),
]
