from rest_framework.views import APIView

from apps.accounts.services import AccountService
from common.pagination.pagination import StandardPagination
from common.response import ApiResponse

from .serializers import (
    TransactionCategoryStatisticsQuerySerializer,
    TransactionCreateSerializer,
    TransactionMonthlyStatisticsQuerySerializer,
    TransactionQuerySerializer,
    TransactionSerializer,
    TransactionSummaryQuerySerializer,
    TransactionTrendQuerySerializer,
    TransactionUpdateSerializer,
    TransactionYearlyStatisticsQuerySerializer,
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


class TransactionSummaryView(APIView):
    """
    账单汇总统计接口。
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户账单汇总。

        支持参数：

        start_date
        end_date
        """

        # ==============================
        # 校验 Query 参数
        # ==============================

        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)

        query_serializer.is_valid(raise_exception=True)

        # ==============================
        # 获取汇总数据
        # ==============================

        summary = TransactionService.get_transaction_summary(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ==============================
        # Decimal 转字符串
        # ==============================

        data = {
            "total_income": (f"{summary['total_income']:.2f}"),
            "total_expense": (f"{summary['total_expense']:.2f}"),
            "balance": (f"{summary['balance']:.2f}"),
            "income_count": (summary["income_count"]),
            "expense_count": (summary["expense_count"]),
            "total_count": (summary["total_count"]),
        }

        return ApiResponse.success(
            message="获取账单汇总成功",
            data=data,
        )


class TransactionTrendView(APIView):
    """
    账单趋势统计接口。
    """

    def get(
        self,
        request,
    ):
        """
        获取账单趋势。

        支持：
        start_date
        end_date
        """

        # ==============================
        # 校验 Query 参数
        # ==============================

        query_serializer = TransactionTrendQuerySerializer(data=request.query_params)

        query_serializer.is_valid(raise_exception=True)

        # ==============================
        # 查询趋势数据
        # ==============================

        trend_data = TransactionService.get_transaction_trend(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ==============================
        # Decimal 转字符串
        # ==============================

        data = []

        for item in trend_data:
            data.append(
                {
                    "date": (item["date"].strftime("%Y-%m-%d")),
                    "income": (f"{item['income']:.2f}"),
                    "expense": (f"{item['expense']:.2f}"),
                    "balance": (f"{item['balance']:.2f}"),
                }
            )

        return ApiResponse.success(
            message="获取账单趋势成功",
            data=data,
        )


class TransactionCategoryStatisticsView(APIView):
    """
    账单分类统计接口。

    用于：
    1. 分类饼图；
    2. 分类排行；
    3. 分类金额占比。
    """

    def get(
        self,
        request,
    ):
        """
        获取分类统计数据。

        Query 参数：

        transaction_type：
            expense / income

        start_date：
            开始日期，可选。

        end_date：
            结束日期，可选。
        """

        # ==============================
        # 校验 Query 参数
        # ==============================

        query_serializer = TransactionCategoryStatisticsQuerySerializer(
            data=request.query_params
        )

        # 参数不合法时，
        # DRF 会直接抛出 ValidationError。
        query_serializer.is_valid(raise_exception=True)

        # ==============================
        # 调用 Service
        # ==============================

        statistics = TransactionService.get_category_statistics(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ==============================
        # 格式化返回结果
        # ==============================

        categories = []

        # Decimal 不建议直接交给前端处理，
        # 金额统一转为两位小数字符串。
        for item in statistics["categories"]:
            categories.append(
                {
                    "category_id": (item["category_id"]),
                    "category_name": (item["category_name"]),
                    "amount": (f"{item['amount']:.2f}"),
                    "count": (item["count"]),
                    "percentage": (f"{item['percentage']:.2f}"),
                }
            )

        # 构造接口 data。
        data = {
            "transaction_type": (statistics["transaction_type"]),
            "total_amount": (f"{statistics['total_amount']:.2f}"),
            "categories": categories,
        }

        # 返回统一响应结构。
        return ApiResponse.success(
            message="获取分类统计成功",
            data=data,
        )


class AccountStatisticsView(APIView):
    """
    账户资金分布统计接口。

    用于：
    1. 首页资产统计；
    2. 账户资产分布图；
    3. 各账户余额占比展示。
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户账户资金统计。
        """

        # ==============================
        # 调用账户 Service
        # ==============================

        statistics = AccountService.get_account_statistics(
            user=request.user,
        )

        # ==============================
        # 格式化账户数据
        # ==============================

        accounts = []

        for item in statistics["accounts"]:
            accounts.append(
                {
                    # 账户 ID。
                    "account_id": (item["account_id"]),
                    # 账户名称。
                    "account_name": (item["account_name"]),
                    # 账户类型代码。
                    "account_type": (item["account_type"]),
                    # 账户类型中文名称。
                    "account_type_display": (item["account_type_display"]),
                    # 当前余额。
                    #
                    # 金额统一返回两位小数字符串。
                    "balance": (f"{item['balance']:.2f}"),
                    # 当前账户余额占比。
                    "percentage": (f"{item['percentage']:.2f}"),
                    # 是否默认账户。
                    "is_default": (item["is_default"]),
                }
            )

        # ==============================
        # 构造接口返回数据
        # ==============================

        data = {
            # 所有有效账户余额总和。
            "total_balance": (f"{statistics['total_balance']:.2f}"),
            # 各账户统计数据。
            "accounts": accounts,
        }

        # 返回统一响应格式。
        return ApiResponse.success(
            message="获取账户统计成功",
            data=data,
        )


class TransactionMonthlyStatisticsView(APIView):
    """
    月度收支统计接口。

    用于：
    1. 首页月度收支展示；
    2. 统计页月度对比；
    3. 收入环比；
    4. 支出环比。
    """

    def get(
        self,
        request,
    ):
        """
        获取月度统计数据。

        Query 参数：

        month：
            可选。

            格式：
            YYYY-MM

            不传时默认当前月份。
        """

        # ======================================
        # 校验 Query 参数
        # ======================================

        query_serializer = TransactionMonthlyStatisticsQuerySerializer(
            data=request.query_params
        )

        query_serializer.is_valid(raise_exception=True)

        # ======================================
        # 调用 Service
        # ======================================

        statistics = TransactionService.get_monthly_statistics(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ======================================
        # 获取环比数据
        # ======================================

        income_rate = statistics["comparison"]["income_rate"]

        expense_rate = statistics["comparison"]["expense_rate"]

        # ======================================
        # 构造接口返回数据
        # ======================================

        data = {
            # 当前月份。
            "current_month": (statistics["current_month"]),
            # 上一个月份。
            "previous_month": (statistics["previous_month"]),
            # 当前月份统计。
            "current": {
                "income": (f"{statistics['current']['income']:.2f}"),
                "expense": (f"{statistics['current']['expense']:.2f}"),
                "balance": (f"{statistics['current']['balance']:.2f}"),
            },
            # 上一个月份统计。
            "previous": {
                "income": (f"{statistics['previous']['income']:.2f}"),
                "expense": (f"{statistics['previous']['expense']:.2f}"),
                "balance": (f"{statistics['previous']['balance']:.2f}"),
            },
            # 环比。
            "comparison": {
                # 如果上个月没有收入，
                # 返回 null。
                "income_rate": (
                    f"{income_rate:.2f}" if income_rate is not None else None
                ),
                # 如果上个月没有支出，
                # 返回 null。
                "expense_rate": (
                    f"{expense_rate:.2f}" if expense_rate is not None else None
                ),
            },
        }

        # ======================================
        # 返回统一响应结构
        # ======================================

        return ApiResponse.success(
            message="获取月度统计成功",
            data=data,
        )


class TransactionYearlyStatisticsView(APIView):
    """
    年度收支统计接口。

    用于：
    1. 年度收支趋势；
    2. 年度柱状图；
    3. 年度收入统计；
    4. 年度支出统计。
    """

    def get(
        self,
        request,
    ):
        """
        获取年度统计数据。

        Query 参数：

        year：
            可选。

            示例：
            2026

            不传时默认当前年份。
        """

        # ======================================
        # 校验 Query 参数
        # ======================================

        query_serializer = TransactionYearlyStatisticsQuerySerializer(
            data=request.query_params
        )

        # 参数错误时，
        # 自动抛出 ValidationError。
        query_serializer.is_valid(raise_exception=True)

        # ======================================
        # 获取年度统计数据
        # ======================================

        statistics = TransactionService.get_yearly_statistics(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ======================================
        # 格式化月份数据
        # ======================================

        months = []

        for item in statistics["months"]:
            months.append(
                {
                    # 月份数字。
                    "month": (item["month"]),
                    # YYYY-MM。
                    "month_text": (item["month_text"]),
                    # 月收入。
                    "income": (f"{item['income']:.2f}"),
                    # 月支出。
                    "expense": (f"{item['expense']:.2f}"),
                    # 月结余。
                    "balance": (f"{item['balance']:.2f}"),
                }
            )

        # ======================================
        # 构造接口 data
        # ======================================

        data = {
            # 统计年份。
            "year": statistics["year"],
            # 全年收入。
            "total_income": (f"{statistics['total_income']:.2f}"),
            # 全年支出。
            "total_expense": (f"{statistics['total_expense']:.2f}"),
            # 全年结余。
            "total_balance": (f"{statistics['total_balance']:.2f}"),
            # 1～12 月数据。
            "months": months,
        }

        # ======================================
        # 返回统一响应
        # ======================================

        return ApiResponse.success(
            message="获取年度统计成功",
            data=data,
        )
