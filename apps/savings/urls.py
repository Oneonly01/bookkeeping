from django.urls import path

from .views import (
    SavingsGoalDepositView,
    SavingsGoalDetailView,
    SavingsGoalListCreateView,
    SavingsGoalRecordListView,
    SavingsGoalWithdrawView,
)

urlpatterns = [
    # ==========================================
    # 储蓄目标列表 / 创建
    # ==========================================
    # GET：
    # 查询储蓄目标列表。
    #
    # POST：
    # 创建储蓄目标。
    path(
        "goals/",
        SavingsGoalListCreateView.as_view(),
        name="savings-goal-list-create",
    ),
    # ==========================================
    # 存入资金
    # ==========================================
    path(
        "goals/<int:goal_id>/deposit/",
        SavingsGoalDepositView.as_view(),
        name="savings-goal-deposit",
    ),
    # ==========================================
    # 取出资金
    # ==========================================
    path(
        "goals/<int:goal_id>/withdraw/",
        SavingsGoalWithdrawView.as_view(),
        name="savings-goal-withdraw",
    ),
    # ==========================================
    # 储蓄流水
    # ==========================================
    path(
        "goals/<int:goal_id>/records/",
        SavingsGoalRecordListView.as_view(),
        name="savings-goal-record-list",
    ),
    # ==========================================
    # 详情 / 修改 / 删除
    # ==========================================
    path(
        "goals/<int:goal_id>/",
        SavingsGoalDetailView.as_view(),
        name="savings-goal-detail",
    ),
]
