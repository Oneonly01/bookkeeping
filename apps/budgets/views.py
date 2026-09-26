from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    BudgetCreateSerializer,
    BudgetSerializer,
)
from .services import BudgetService


class BudgetListCreateView(APIView):
    """
    预算列表 / 创建预算接口。

    GET：
        获取当前用户预算列表。

    POST：
        创建预算。
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户预算列表。
        """

        # 调用 Service 查询预算。
        budgets = BudgetService.get_budget_list(
            user=request.user,
        )

        # 序列化预算列表。
        serializer = BudgetSerializer(
            budgets,
            many=True,
        )

        # 返回统一响应结构。
        return ApiResponse.success(
            message="获取预算列表成功",
            data=serializer.data,
        )

    def post(
        self,
        request,
    ):
        """
        创建预算。
        """

        # ======================================
        # 校验请求参数
        # ======================================

        serializer = BudgetCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用 Service 创建预算
        # ======================================

        budget = BudgetService.create_budget(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 序列化创建结果
        # ======================================

        response_serializer = BudgetSerializer(budget)

        # 返回创建结果。
        return ApiResponse.success(
            message="创建预算成功",
            data=response_serializer.data,
        )
