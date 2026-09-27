from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    BudgetCopySerializer,
    BudgetCreateSerializer,
    BudgetProgressQuerySerializer,
    BudgetQuerySerializer,
    BudgetSerializer,
    BudgetUpdateSerializer,
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

        支持筛选：

        year
        month
        budget_type
        is_active
        category_id
        """

        # ======================================
        # 校验 Query 参数
        # ======================================

        query_serializer = BudgetQuerySerializer(data=request.query_params.dict())

        query_serializer.is_valid(raise_exception=True)

        # ======================================
        # 查询预算
        # ======================================

        budgets = BudgetService.get_budget_list(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ======================================
        # 序列化列表
        # ======================================

        serializer = BudgetSerializer(
            budgets,
            many=True,
        )

        # ======================================
        # 返回统一响应
        # ======================================
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


class BudgetDetailView(APIView):
    """
    预算详情 / 修改 / 删除接口。

    GET：
        获取预算详情。

    PUT：
        修改预算。

    DELETE：
        删除预算。
    """

    def get(
        self,
        request,
        budget_id,
    ):
        """
        获取预算详情。
        """

        # 查询预算。
        budget = BudgetService.get_budget_detail(
            user=request.user,
            budget_id=budget_id,
        )

        # 序列化返回数据。
        serializer = BudgetSerializer(budget)

        return ApiResponse.success(
            message="获取预算详情成功",
            data=serializer.data,
        )

    def put(
        self,
        request,
        budget_id,
    ):
        """
        修改预算。
        """

        # ======================================
        # 校验修改参数
        # ======================================

        serializer = BudgetUpdateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 修改预算
        # ======================================

        budget = BudgetService.update_budget(
            user=request.user,
            budget_id=budget_id,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回修改结果
        # ======================================

        response_serializer = BudgetSerializer(budget)

        return ApiResponse.success(
            message="修改预算成功",
            data=response_serializer.data,
        )

    def delete(
        self,
        request,
        budget_id,
    ):
        """
        删除预算。
        """

        # 执行逻辑删除。
        BudgetService.delete_budget(
            user=request.user,
            budget_id=budget_id,
        )

        return ApiResponse.success(
            message="删除预算成功",
            data=None,
        )


class BudgetProgressView(APIView):
    """
    预算执行进度接口。

    用于查询：
    1. 预算金额；
    2. 已支出；
    3. 剩余预算；
    4. 使用比例；
    5. 是否预警；
    6. 是否超支。
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户预算执行进度。
        """

        # ======================================
        # 校验 Query 参数
        # ======================================

        serializer = BudgetProgressQuerySerializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用 Service
        # ======================================

        progress = BudgetService.get_budget_progress(
            user=request.user,
            query_params=(serializer.validated_data),
        )

        # ======================================
        # 格式化预算进度
        # ======================================

        budgets = []

        for item in progress["budgets"]:
            budgets.append(
                {
                    "budget_id": (item["budget_id"]),
                    "budget_type": (item["budget_type"]),
                    "budget_type_display": (item["budget_type_display"]),
                    "category_id": (item["category_id"]),
                    "category_name": (item["category_name"]),
                    "year": item["year"],
                    "month": item["month"],
                    # 金额统一返回字符串，
                    # 保证两位小数。
                    "budget_amount": (f"{item['budget_amount']:.2f}"),
                    "spent_amount": (f"{item['spent_amount']:.2f}"),
                    "remaining_amount": (f"{item['remaining_amount']:.2f}"),
                    "usage_percentage": (f"{item['usage_percentage']:.2f}"),
                    "alert_threshold": (f"{item['alert_threshold']:.2f}"),
                    # 是否达到提醒阈值。
                    "is_alert": (item["is_alert"]),
                    # 是否超预算。
                    "is_over_budget": (item["is_over_budget"]),
                }
            )

        # ======================================
        # 返回统一响应
        # ======================================

        return ApiResponse.success(
            message="获取预算执行进度成功",
            data={
                "year": progress["year"],
                "month": progress["month"],
                "budgets": budgets,
            },
        )


class BudgetOverviewView(APIView):
    """
    预算概览接口。

    用于首页或预算页面顶部展示：

    1. 总预算；
    2. 已支出；
    3. 剩余预算；
    4. 使用比例；
    5. 预算数量；
    6. 预警数量；
    7. 超支数量。
    """

    def get(
        self,
        request,
    ):
        """
        获取预算概览。
        """

        # ======================================
        # 校验年月参数
        # ======================================

        serializer = BudgetProgressQuerySerializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用 Service
        # ======================================

        overview = BudgetService.get_budget_overview(
            user=request.user,
            query_params=(serializer.validated_data),
        )

        # ======================================
        # 构造返回数据
        # ======================================

        data = {
            # 年份。
            "year": overview["year"],
            # 月份。
            "month": overview["month"],
            # 总预算金额。
            "total_budget": (f"{overview['total_budget']:.2f}"),
            # 已支出。
            "total_spent": (f"{overview['total_spent']:.2f}"),
            # 剩余预算。
            "total_remaining": (f"{overview['total_remaining']:.2f}"),
            # 使用比例。
            "usage_percentage": (f"{overview['usage_percentage']:.2f}"),
            # 当前有效预算数量。
            "budget_count": (overview["budget_count"]),
            # 达到提醒阈值数量。
            "alert_count": (overview["alert_count"]),
            # 已经超支数量。
            "over_budget_count": (overview["over_budget_count"]),
        }

        # ======================================
        # 返回统一响应
        # ======================================

        return ApiResponse.success(
            message="获取预算概览成功",
            data=data,
        )


class BudgetCopyView(APIView):
    """
    月度预算复制接口。

    用于把某个月预算批量复制到另一个月。
    """

    def post(
        self,
        request,
    ):
        """
        复制预算。
        """

        # ======================================
        # 校验请求参数
        # ======================================

        serializer = BudgetCopySerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用 Service
        # ======================================

        result = BudgetService.copy_budgets(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 序列化新创建预算
        # ======================================

        budget_serializer = BudgetSerializer(
            result["created_budgets"],
            many=True,
        )

        # ======================================
        # 返回复制结果
        # ======================================

        return ApiResponse.success(
            message="复制预算成功",
            data={
                "source_year": (result["source_year"]),
                "source_month": (result["source_month"]),
                "target_year": (result["target_year"]),
                "target_month": (result["target_month"]),
                "created_count": (result["created_count"]),
                "skipped_count": (result["skipped_count"]),
                "budgets": (budget_serializer.data),
            },
        )
