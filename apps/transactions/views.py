from rest_framework.views import APIView

from common.pagination.pagination import StandardPagination
from common.response import ApiResponse

from .serializers import (
    TransactionCreateSerializer,
    TransactionQuerySerializer,
    TransactionSerializer,
    TransactionUpdateSerializer,
)
from .services import TransactionService


class TransactionListCreateView(APIView):
    """
    账单列表 / 新增账单接口。

    GET:
        获取账单列表。

    POST:
        新增收入或支出账单。

    地址：
        /api/v1/transactions/
    """

    def get(
        self,
        request,
    ):
        """
        获取账单列表。

        支持：
        1. 账单类型筛选；
        2. 账户筛选；
        3. 分类筛选；
        4. 日期范围筛选；
        5. 关键字搜索；
        6. 分页查询。
        """

        # ==============================
        # 校验筛选参数
        # ==============================

        query_serializer = TransactionQuerySerializer(data=request.query_params)

        query_serializer.is_valid(raise_exception=True)

        # ==============================
        # 查询账单
        # ==============================

        transactions = TransactionService.get_transaction_list(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ==============================
        # 分页
        # ==============================

        # 创建分页器。
        paginator = StandardPagination()

        # 根据 page / page_size
        # 对 QuerySet 进行分页。
        page = paginator.paginate_queryset(
            transactions,
            request,
            view=self,
        )

        # ==============================
        # 序列化当前页
        # ==============================

        serializer = TransactionSerializer(
            page,
            many=True,
        )

        # ==============================
        # 返回分页数据
        # ==============================

        return ApiResponse.success(
            message="获取账单列表成功",
            data={
                # 总记录数。
                "count": paginator.page.paginator.count,
                # 当前页。
                "page": paginator.page.number,
                # 每页数量。
                "page_size": paginator.get_page_size(request),
                # 总页数。
                "total_pages": (paginator.page.paginator.num_pages),
                # 是否存在下一页。
                "has_next": paginator.page.has_next(),
                # 是否存在上一页。
                "has_previous": (paginator.page.has_previous()),
                # 当前页数据。
                "results": serializer.data,
            },
        )

    def post(
        self,
        request,
    ):
        """
        新增账单。
        """

        serializer = TransactionCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        transaction_record = TransactionService.create_transaction(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        result = TransactionSerializer(transaction_record)

        return ApiResponse.success(
            message="账单创建成功",
            data=result.data,
        )


class TransactionDetailView(APIView):
    """
    账单详情 / 修改 / 删除接口。

    GET:
        获取账单详情。

    PUT:
        修改账单。

    DELETE:
        删除账单并回滚余额。

    地址：
        /api/v1/transactions/{id}/
    """

    def get(
        self,
        request,
        transaction_id,
    ):
        """
        获取账单详情。
        """

        transaction_record = TransactionService.get_transaction_detail(
            user=request.user,
            transaction_id=transaction_id,
        )

        serializer = TransactionSerializer(transaction_record)

        return ApiResponse.success(
            message="获取账单详情成功",
            data=serializer.data,
        )

    def put(
        self,
        request,
        transaction_id,
    ):
        """
        修改账单。
        """

        serializer = TransactionUpdateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        transaction_record = TransactionService.update_transaction(
            user=request.user,
            transaction_id=transaction_id,
            validated_data=(serializer.validated_data),
        )

        result = TransactionSerializer(transaction_record)

        return ApiResponse.success(
            message="账单修改成功",
            data=result.data,
        )

    def delete(
        self,
        request,
        transaction_id,
    ):
        """
        删除账单。
        """

        TransactionService.delete_transaction(
            user=request.user,
            transaction_id=transaction_id,
        )

        return ApiResponse.success(
            message="账单删除成功",
            data=None,
        )
