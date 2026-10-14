from rest_framework.views import APIView

from common.pagination.pagination import StandardPagination
from common.response import ApiResponse
from common.utils.idempotency import idempotent_request

from .models import RecurringTransaction
from .recurring_serializers import (
    RecurringExecutionSerializer,
    RecurringTransactionCreateSerializer,
    RecurringTransactionSerializer,
    RecurringTransactionUpdateSerializer,
)
from .recurring_services import RecurringTransactionService


class RecurringTransactionListCreateView(APIView):
    """周期账单列表 / 创建模板。"""

    def get(self, request):
        templates = RecurringTransaction.objects.filter(
            user=request.user, is_deleted=False,
        ).prefetch_related("tags")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request, view=self)
        return paginator.get_paginated_response(
            RecurringTransactionSerializer(page, many=True).data,
        )

    @idempotent_request
    def post(self, request):
        serializer = RecurringTransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = RecurringTransactionService.create_template(
            user=request.user,
            validated_data=serializer.validated_data,
        )
        return ApiResponse.success(
            message="周期账单模板创建成功",
            data=RecurringTransactionSerializer(template).data,
        )


class RecurringTransactionDetailView(APIView):
    """模板详情 / 修改 / 逻辑删除。"""

    def get(
        self,
        request,
        template_id,
    ):
        template = RecurringTransactionService.get_template(request.user, template_id)
        return ApiResponse.success(data=RecurringTransactionSerializer(template).data)

    @idempotent_request
    def put(
        self,
        request,
        template_id,
    ):
        template = RecurringTransactionService.get_template(request.user, template_id)
        serializer = RecurringTransactionUpdateSerializer(instance=template, data=request.data)
        serializer.is_valid(raise_exception=True)
        template = RecurringTransactionService.update_template(
            request.user, template_id, serializer.validated_data,
        )
        return ApiResponse.success(
            message="周期账单模板修改成功",
            data=RecurringTransactionSerializer(template).data,
        )

    def delete(
        self,
        request,
        template_id,
    ):
        RecurringTransactionService.delete_template(request.user, template_id)
        return ApiResponse.success(message="周期账单模板删除成功")


class RecurringTransactionRunView(APIView):
    """手动补执行到期周期；不会生成未来账单。"""

    def post(
        self,
        request,
        template_id,
    ):
        result = RecurringTransactionService.execute_due(request.user, template_id)
        return ApiResponse.success(message="周期账单执行结束", data=result)


class RecurringExecutionListView(APIView):
    """当前用户模板的历史执行记录，支持偏好分页。"""

    def get(
        self,
        request,
        template_id,
    ):
        template = RecurringTransactionService.get_template(request.user, template_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(template.executions.all(), request, view=self)
        return paginator.get_paginated_response(
            RecurringExecutionSerializer(page, many=True).data,
        )
