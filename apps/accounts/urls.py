# 导入 Django path。
from django.urls import path

# 导入账户视图。
from .views import (
    AccountAssetSummaryView,
    AccountBalanceAdjustmentListView,
    AccountBalanceAdjustmentView,
    AccountDetailView,
    AccountListCreateView,
    AccountStatisticsView,
    AccountTransferDetailView,
    AccountTransferListCreateView,
)

# 当前应用路由命名空间。
app_name = "accounts"


# 账户模块路由。
urlpatterns = [
    # ==========================================
    # 账户列表 / 新增账户
    # ==========================================
    # GET：
    # 获取当前用户账户列表。
    #
    # POST：
    # 新增资金账户。
    path(
        "",
        AccountListCreateView.as_view(),
        name="account-list-create",
    ),
    # ==========================================
    # 账户统计
    # ==========================================
    # GET：
    # 获取当前用户账户资金分布统计。
    #
    # 返回：
    # 1. 总余额；
    # 2. 每个账户余额；
    # 3. 每个账户占比；
    # 4. 是否默认账户。
    path(
        "statistics/",
        AccountStatisticsView.as_view(),
        name="account-statistics",
    ),
    # ==========================================
    # 账户转账列表 / 创建转账
    # ==========================================
    # GET：
    # 获取当前用户的账户转账记录。
    #
    # POST：
    # 创建账户之间的资金转账。
    path(
        "transfers/",
        AccountTransferListCreateView.as_view(),
        name="account-transfer-list-create",
    ),
    # ==========================================
    # 单笔转账详情 / 撤销转账
    # ==========================================
    # GET：
    # 获取指定转账记录详情。
    #
    # DELETE：
    # 撤销转账。
    #
    # 撤销时会反向恢复来源账户和目标账户余额，
    # 转账记录本身不会物理删除。
    path(
        "transfers/<int:transfer_id>/",
        AccountTransferDetailView.as_view(),
        name="account-transfer-detail",
    ),
    # ==========================================
    # 账户详情 / 修改 / 删除
    # ==========================================
    # GET：
    # 获取指定账户详情。
    #
    # PUT：
    # 修改指定账户。
    #
    # DELETE：
    # 逻辑删除指定账户。
    path(
        "<int:account_id>/",
        AccountDetailView.as_view(),
        name="account-detail",
    ),
    # ==========================================
    # 余额校准
    # ==========================================
    # POST：
    # 手动校准指定账户余额。
    #
    # 系统会：
    # 1. 记录调整前余额；
    # 2. 记录调整后余额；
    # 3. 记录调整差额；
    # 4. 保存余额调整审计记录。
    path(
        "<int:account_id>/adjust-balance/",
        AccountBalanceAdjustmentView.as_view(),
        name="account-adjust-balance",
    ),
    # ==========================================
    # 余额调整记录
    # ==========================================
    # GET：
    # 查询指定账户的余额调整历史。
    path(
        "<int:account_id>/balance-adjustments/",
        AccountBalanceAdjustmentListView.as_view(),
        name="account-balance-adjustments",
    ),
    # ==========================================
    # 资产概览
    # ==========================================
    # GET：
    # 获取：
    # 1. 总资产；
    # 2. 总负债；
    # 3. 净资产；
    # 4. 有效账户数量。
    path(
        "asset-summary/",
        AccountAssetSummaryView.as_view(),
        name="account-asset-summary",
    ),
]
