from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    TagCreateSerializer,
    TagSerializer,
    TagUpdateSerializer,
)
from .services import TagService


class TagListCreateView(APIView):
    """
    标签列表 / 创建标签。

    GET：
        查询标签列表。

    POST：
        创建标签。
    """

    def get(
        self,
        request,
    ):
        """
        查询标签列表。
        """

        tags = TagService.get_tag_list(
            user=request.user,
        )

        serializer = TagSerializer(
            tags,
            many=True,
        )

        return ApiResponse.success(
            message="获取标签列表成功",
            data=serializer.data,
        )

    def post(
        self,
        request,
    ):
        """
        创建标签。
        """

        serializer = TagCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        tag = TagService.create_tag(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        response_serializer = TagSerializer(tag)

        return ApiResponse.success(
            message="创建标签成功",
            data=response_serializer.data,
        )


class TagDetailView(APIView):
    """
    标签详情操作。

    GET：查询详情。
    PUT：修改名称、颜色，未传字段保持原值。
    DELETE：逻辑删除。
    """

    def get(self, request, tag_id):
        """查询标签详情。"""
        tag = TagService.get_tag_detail(
            user=request.user,
            tag_id=tag_id,
        )
        return ApiResponse.success(
            message="获取标签详情成功",
            data=TagSerializer(tag).data,
        )

    def put(self, request, tag_id):
        """修改标签。"""
        serializer = TagUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = TagService.update_tag(
            user=request.user,
            tag_id=tag_id,
            validated_data=serializer.validated_data,
        )
        return ApiResponse.success(
            message="修改标签成功",
            data=TagSerializer(tag).data,
        )

    def delete(
        self,
        request,
        tag_id,
    ):
        """
        删除标签。
        """

        TagService.delete_tag(
            user=request.user,
            tag_id=tag_id,
        )

        return ApiResponse.success(
            message="删除标签成功",
            data=None,
        )
