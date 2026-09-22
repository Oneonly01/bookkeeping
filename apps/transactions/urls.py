from django.urls import path

from .views import TransactionDetailView, TransactionListCreateView

app_name = "transactions"


urlpatterns = [
    # 账单列表 / 新增账单。
    path(
        "",
        TransactionListCreateView.as_view(),
        name="transaction-list-create",
    ),
    # 账单详情 / 修改 / 删除。
    path(
        "<int:transaction_id>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
]
