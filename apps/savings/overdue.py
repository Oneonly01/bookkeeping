"""储蓄目标逾期判断，接口展示、筛选和统计共用同一业务口径。"""
from django.db.models import Q
from django.utils import timezone

from .models import SavingsGoal


def overdue_goal_filter(today=None):
    """只有进行中且截止日期早于今天的目标逾期，截止当天不算逾期。"""
    today = today or timezone.localdate()
    return Q(status=SavingsGoal.Status.ACTIVE, deadline__lt=today)


def goal_overdue_days(goal, today=None):
    """动态计算逾期天数，不修改状态或金额，也不依赖定时任务。"""
    if goal.is_deleted or goal.status != SavingsGoal.Status.ACTIVE or not goal.deadline:
        return 0
    today = today or timezone.localdate()
    return max((today - goal.deadline).days, 0)
