# 导入 Django path。
from django.urls import path

# 导入账户视图。
from .views import (
    AccountBalanceAdjustView,
    AccountBalanceAdjustmentListView,
    AccountDetailView,
    AccountListCreateView,
    TransferDetailView,
    TransferListCreateView,
)

# 当前应用路由命名空间。
app_name = "accounts"


# 账户模块路由。
urlpatterns = [
    # 账户列表 / 新增账户。
    #
    # GET  /api/v1/accounts/
    # POST /api/v1/accounts/
    path(
        "",
        AccountListCreateView.as_view(),
        name="account-list-create",
    ),
    # 账户详情。
    # 账户详情 / 修改 / 删除。
    # GET /api/v1/accounts/1/
    path(
        "<int:account_id>/",
        AccountDetailView.as_view(),
        name="account-detail",
    ),
    # 账户余额校准。
    path(
        "<int:account_id>/adjust-balance/",
        AccountBalanceAdjustView.as_view(),
        name="account-adjust-balance",
    ),
    # 查询账户余额校准历史。
    path(
        "<int:account_id>/balance-adjustments/",
        AccountBalanceAdjustmentListView.as_view(),
        name="account-balance-adjustments",
    ),
    # 转账列表 / 新建转账。
    path(
        "transfers/",
        TransferListCreateView.as_view(),
        name="transfer-list-create",
    ),
    # 转账详情。
    path(
        "transfers/<int:transfer_id>/",
        TransferDetailView.as_view(),
        name="transfer-detail",
    ),
]
