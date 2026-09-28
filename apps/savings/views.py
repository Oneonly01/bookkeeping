from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    SavingsDepositSerializer,
    SavingsGoalCreateSerializer,
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

        # 调用 Service 查询当前用户目标。
        goals = SavingsGoalService.get_goal_list(
            user=request.user,
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
