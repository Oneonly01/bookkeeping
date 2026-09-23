from django.urls import path

from .views import (
    TransactionCategoryStatisticsView,
    TransactionDetailView,
    TransactionListCreateView,
    TransactionMonthlyStatisticsView,
    TransactionSummaryView,
    TransactionTrendView,
    TransactionYearlyStatisticsView,
)

app_name = "transactions"


urlpatterns = [
    # ==========================================
    # 账单列表 / 新增账单
    # ==========================================
    # GET：
    # 获取当前用户账单列表，
    # 支持类型、账户、分类、日期、关键字筛选和分页。
    #
    # POST：
    # 新增一笔收入或支出账单。
    path(
        "",
        TransactionListCreateView.as_view(),
        name="transaction-list-create",
    ),
    # ==========================================
    # 账单汇总统计
    # ==========================================
    # GET：
    # 获取指定时间范围内的：
    # 1. 总收入；
    # 2. 总支出；
    # 3. 结余；
    # 4. 收入笔数；
    # 5. 支出笔数；
    # 6. 总账单数。
    path(
        "summary/",
        TransactionSummaryView.as_view(),
        name="transaction-summary",
    ),
    # ==========================================
    # 账单趋势统计
    # ==========================================
    # GET：
    # 按日期统计：
    # 1. 每日收入；
    # 2. 每日支出；
    # 3. 每日结余。
    #
    # 后续主要用于统计页折线图。
    path(
        "trend/",
        TransactionTrendView.as_view(),
        name="transaction-trend",
    ),
    # ==========================================
    # 分类统计
    # ==========================================
    # GET：
    # 按收入或支出分类统计：
    # 1. 分类金额；
    # 2. 分类账单数量；
    # 3. 分类金额占比。
    #
    # 后续主要用于饼图和分类排行。
    path(
        "category-statistics/",
        TransactionCategoryStatisticsView.as_view(),
        name="transaction-category-statistics",
    ),
    # ==========================================
    # 单笔账单详情 / 修改 / 删除
    # ==========================================
    # GET：
    # 获取指定账单详情。
    #
    # PUT：
    # 修改指定账单，并同步处理账户余额。
    #
    # DELETE：
    # 逻辑删除账单，并恢复对应账户余额。
    path(
        "<int:transaction_id>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    # ==========================================
    # 月度收支统计
    # ==========================================
    # GET：
    # 获取：
    # 1. 本月收入；
    # 2. 本月支出；
    # 3. 本月结余；
    # 4. 上月收入；
    # 5. 上月支出；
    # 6. 上月结余；
    # 7. 收入环比；
    # 8. 支出环比。
    path(
        "monthly-statistics/",
        TransactionMonthlyStatisticsView.as_view(),
        name="transaction-monthly-statistics",
    ),
    # ==========================================
    # 年度收支统计
    # ==========================================
    # GET：
    # 按 1～12 月统计指定年份：
    # 1. 收入；
    # 2. 支出；
    # 3. 结余；
    # 4. 全年汇总。
    path(
        "yearly-statistics/",
        TransactionYearlyStatisticsView.as_view(),
        name="transaction-yearly-statistics",
    ),
]
