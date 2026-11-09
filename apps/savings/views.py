from common.utils.idempotency import idempotent_request

from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    SavingsDepositSerializer,
    SavingsGoalCreateSerializer,
    SavingsGoalListQuerySerializer,
    SavingsGoalSerializer,
    SavingsGoalUpdateSerializer,
    SavingsRecordSerializer,
    SavingsWithdrawSerializer,
)
from .services import SavingsGoalService


class SavingsGoalListCreateView(APIView):
    """
    储蓄目标列表 / 创建接口。

    GET：
        获取当前用户储蓄目标列表。

    POST：
        创建储蓄目标。
    """

    def get(
        self,
        request,
    ):
        """
        获取储蓄目标列表。
        """

        # 校验可选展示状态，错误状态返回统一400响应。
        # 转为普通字典，避免DRF按HTML表单规则将已传空金额/日期当作未传。
        query_serializer = SavingsGoalListQuerySerializer(data=request.query_params.dict())
        query_serializer.is_valid(raise_exception=True)

        # 用户身份只来自登录凭证，筛选不会扩大到其他用户或已删除目标。
        goals = SavingsGoalService.get_goal_list(
            user=request.user,
            query_params=query_serializer.validated_data,
        )

        # 序列化结果。
        serializer = SavingsGoalSerializer(
            goals,
            many=True,
        )

        # 返回统一响应。
        return ApiResponse.success(
            message="获取储蓄目标列表成功",
            data=serializer.data,
        )

    def post(
        self,
        request,
    ):
        """
        创建储蓄目标。
        """

        # ======================================
        # 校验请求参数
        # ======================================

        serializer = SavingsGoalCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 创建目标
        # ======================================

        goal = SavingsGoalService.create_goal(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 序列化创建结果
        # ======================================

        response_serializer = SavingsGoalSerializer(goal)

        return ApiResponse.success(
            message="创建储蓄目标成功",
            data=response_serializer.data,
        )


class SavingsGoalDetailView(APIView):
    """
    储蓄目标详情接口。

    GET：
        查询储蓄目标详情。

    PUT：
        修改储蓄目标。

    DELETE：
        删除储蓄目标。
    """

    def get(
        self,
        request,
        goal_id,
    ):
        """
        查询目标详情。
        """

        # ======================================
        # 查询储蓄目标
        # ======================================

        goal = SavingsGoalService.get_goal_detail(
            user=request.user,
            goal_id=goal_id,
        )

        # ======================================
        # 序列化
        # ======================================

        serializer = SavingsGoalSerializer(goal)

        return ApiResponse.success(
            message="获取储蓄目标详情成功",
            data=serializer.data,
        )

    def put(
        self,
        request,
        goal_id,
    ):
        """
        修改储蓄目标。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = SavingsGoalUpdateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用业务层
        # ======================================

        goal = SavingsGoalService.update_goal(
            user=request.user,
            goal_id=goal_id,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回修改结果
        # ======================================

        response_serializer = SavingsGoalSerializer(goal)

        return ApiResponse.success(
            message="修改储蓄目标成功",
            data=response_serializer.data,
        )

    def delete(
        self,
        request,
        goal_id,
    ):
        """
        删除储蓄目标。
        """

        SavingsGoalService.delete_goal(
            user=request.user,
            goal_id=goal_id,
        )

        return ApiResponse.success(
            message="删除储蓄目标成功",
            data=None,
        )


class SavingsGoalDepositView(APIView):
    """
    储蓄目标存入资金接口。
    """

    @idempotent_request
    def post(
        self,
        request,
        goal_id,
    ):
        """
        存入资金。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = SavingsDepositSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用业务层
        # ======================================

        goal, record = SavingsGoalService.deposit(
            user=request.user,
            goal_id=goal_id,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回结果
        # ======================================

        return ApiResponse.success(
            message="存入资金成功",
            data={
                "goal": (SavingsGoalSerializer(goal).data),
                "record": (SavingsRecordSerializer(record).data),
            },
        )


class SavingsGoalWithdrawView(APIView):
    """
    储蓄目标取出资金接口。
    """

    @idempotent_request
    def post(
        self,
        request,
        goal_id,
    ):
        """
        取出资金。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = SavingsWithdrawSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用业务层
        # ======================================

        goal, record = SavingsGoalService.withdraw(
            user=request.user,
            goal_id=goal_id,
            validated_data=(serializer.validated_data),
        )

        return ApiResponse.success(
            message="取出资金成功",
            data={
                "goal": (SavingsGoalSerializer(goal).data),
                "record": (SavingsRecordSerializer(record).data),
            },
        )


class SavingsGoalRecordListView(APIView):
    """
    储蓄目标资金流水列表接口。
    """

    def get(
        self,
        request,
        goal_id,
    ):
        """
        查询储蓄目标资金流水。
        """

        records = SavingsGoalService.get_records(
            user=request.user,
            goal_id=goal_id,
        )

        serializer = SavingsRecordSerializer(
            records,
            many=True,
        )

        return ApiResponse.success(
            message="获取储蓄流水成功",
            data=serializer.data,
        )


class SavingsGoalPauseView(APIView):
    """
    暂停储蓄目标接口。
    """

    def post(
        self,
        request,
        goal_id,
    ):
        """
        暂停储蓄目标。
        """

        goal = SavingsGoalService.pause_goal(
            user=request.user,
            goal_id=goal_id,
        )

        serializer = SavingsGoalSerializer(goal)

        return ApiResponse.success(
            message="暂停储蓄目标成功",
            data=serializer.data,
        )


class SavingsGoalResumeView(APIView):
    """
    恢复储蓄目标接口。
    """

    def post(
        self,
        request,
        goal_id,
    ):
        """
        恢复储蓄目标。
        """

        goal = SavingsGoalService.resume_goal(
            user=request.user,
            goal_id=goal_id,
        )

        serializer = SavingsGoalSerializer(goal)

        return ApiResponse.success(
            message="恢复储蓄目标成功",
            data=serializer.data,
        )


class SavingsSummaryView(APIView):
    """
    储蓄目标汇总统计接口。
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户储蓄汇总数据。
        """

        # ======================================
        # 调用业务层
        # ======================================

        summary = SavingsGoalService.get_summary(
            user=request.user,
        )

        # ======================================
        # 返回统一响应
        # ======================================

        return ApiResponse.success(
            message="获取储蓄汇总成功",
            data=summary,
        )
