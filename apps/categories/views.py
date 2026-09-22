from rest_framework.views import APIView

from common.exceptions.business import BusinessException
from common.response import ApiResponse

from .models import Category
from .serializers import (
    CategoryCreateSerializer,
    CategorySerializer,
    CategoryUpdateSerializer,
)
from .services import CategoryService


class CategoryListCreateView(APIView):
    """
    分类列表 / 新增分类接口。

    GET:
        查询当前用户可用分类。

    POST:
        创建当前用户自定义分类。

    地址：
        /api/v1/categories/
    """

    def get(
        self,
        request,
    ):
        """
        获取分类列表。
        """

        # 获取查询参数。
        category_type = request.query_params.get("category_type")

        # 如果传入了分类类型，
        # 先校验是否合法。
        if category_type and category_type not in Category.CategoryType.values:
            raise BusinessException("分类类型不正确")

        # 查询当前用户可用分类。
        categories = CategoryService.get_category_list(
            user=request.user,
            category_type=category_type,
        )

        # 序列化。
        serializer = CategorySerializer(
            categories,
            many=True,
        )

        # 返回统一响应。
        return ApiResponse.success(
            message="获取分类列表成功",
            data=serializer.data,
        )

    def post(
        self,
        request,
    ):
        """
        创建自定义分类。
        """

        # 参数校验。
        serializer = CategoryCreateSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(raise_exception=True)

        # 调用 Service 创建分类。
        category = CategoryService.create_category(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # 序列化返回。
        result = CategorySerializer(category)

        return ApiResponse.success(
            message="分类创建成功",
            data=result.data,
        )


class CategoryDetailView(APIView):
    """
    分类详情 / 修改 / 删除接口。

    GET:
        获取分类详情。

    PUT:
        修改用户自定义分类。

    DELETE:
        逻辑删除用户自定义分类。

    请求地址：
        /api/v1/categories/{id}/
    """

    def get(
        self,
        request,
        category_id,
    ):
        """
        获取分类详情。
        """

        # 查询分类。
        category = CategoryService.get_category_detail(
            user=request.user,
            category_id=category_id,
        )

        # 序列化。
        serializer = CategorySerializer(category)

        # 返回。
        return ApiResponse.success(
            message="获取分类详情成功",
            data=serializer.data,
        )

    def put(
        self,
        request,
        category_id,
    ):
        """
        修改用户自定义分类。
        """

        # 先获取分类。
        category = CategoryService.get_category_detail(
            user=request.user,
            category_id=category_id,
        )

        # 系统分类提前拦截。
        if category.is_system:
            raise BusinessException("系统分类不允许修改")

        # 参数校验。
        serializer = CategoryUpdateSerializer(
            data=request.data,
            context={
                "request": request,
                "category": category,
            },
        )

        serializer.is_valid(raise_exception=True)

        # 调用 Service 修改。
        updated_category = CategoryService.update_category(
            user=request.user,
            category_id=category_id,
            validated_data=(serializer.validated_data),
        )

        # 返回最新数据。
        result = CategorySerializer(updated_category)

        return ApiResponse.success(
            message="分类修改成功",
            data=result.data,
        )

    def delete(
        self,
        request,
        category_id,
    ):
        """
        删除用户自定义分类。
        """

        # 调用 Service 执行逻辑删除。
        CategoryService.delete_category(
            user=request.user,
            category_id=category_id,
        )

        return ApiResponse.success(
            message="分类删除成功",
            data=None,
        )
