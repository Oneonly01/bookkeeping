from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    UserPreferenceSerializer,
)

from .services import (
    PreferenceService,
)


class PreferenceView(APIView):
    """
    用户偏好设置接口。

    GET：
    获取当前用户偏好。

    PUT：
    修改当前用户偏好。
    """

    def get(
        self,
        request,
    ):
        """
        获取用户偏好。

        如果用户首次访问，
        Service 会自动创建默认配置。
        """

        # ======================================
        # 获取用户偏好
        # ======================================

        preference = PreferenceService.get_or_create_preference(
            user=request.user,
        )

        # ======================================
        # 序列化返回
        # ======================================

        serializer = UserPreferenceSerializer(
            preference,
        )

        return ApiResponse.success(
            data=serializer.data,
            message="获取用户偏好成功",
        )

    def put(
        self,
        request,
    ):
        """
        修改用户偏好。

        修改内容：

        1. 默认货币；
        2. 主题模式；
        3. 分页数量；
        4. 预算提醒；
        5. 默认账户。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = UserPreferenceSerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        # ======================================
        # 更新偏好
        # ======================================

        preference = PreferenceService.update_preference(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回最新数据
        # ======================================

        response_serializer = UserPreferenceSerializer(
            preference,
        )

        return ApiResponse.success(
            data=response_serializer.data,
            message="修改用户偏好成功",
        )
