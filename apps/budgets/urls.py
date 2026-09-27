from django.urls import path

from .views import (
    BudgetCopyView,
    BudgetDetailView,
    BudgetListCreateView,
    BudgetOverviewView,
    BudgetProgressView,
)

urlpatterns = [
    # ==========================================
    # 预算列表 / 创建预算
    # ==========================================
    # GET：
    # 查询当前用户预算列表。
    #
    # POST：
    # 创建预算。
    path(
        "",
        BudgetListCreateView.as_view(),
        name="budget-list-create",
    ),
    # ==========================================
    # 预算详情 / 修改 / 删除
    # ==========================================
    # GET：
    # 获取指定预算详情。
    #
    # PUT：
    # 修改指定预算。
    #
    # DELETE：
    # 逻辑删除指定预算。
    path(
        "<int:budget_id>/",
        BudgetDetailView.as_view(),
        name="budget-detail",
    ),
    # ==========================================
    # 预算执行进度
    # ==========================================
    # GET：
    # 查询预算金额、已支出、剩余金额、
    # 使用比例、提醒状态、超支状态。
    path(
        "progress/",
        BudgetProgressView.as_view(),
        name="budget-progress",
    ),
    # ==========================================
    # 预算概览
    # ==========================================
    path(
        "overview/",
        BudgetOverviewView.as_view(),
        name="budget-overview",
    ),
    # ==========================================
    # 月度预算复制
    # ==========================================
    # POST：
    # 把一个月份的预算复制到目标月份。
    path(
        "copy/",
        BudgetCopyView.as_view(),
        name="budget-copy",
    ),
]
