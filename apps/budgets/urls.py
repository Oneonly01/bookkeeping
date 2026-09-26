from django.urls import path

from .views import BudgetListCreateView

urlpatterns = [
    # ==========================================
    # 预算列表 / 创建预算
    # ==========================================
    # GET：
    # 获取当前用户预算列表。
    #
    # POST：
    # 创建月度总预算或分类预算。
    path(
        "",
        BudgetListCreateView.as_view(),
        name="budget-list-create",
    ),
]
