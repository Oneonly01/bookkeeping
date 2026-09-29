from datetime import datetime
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.savings.models import SavingsGoal
from apps.transactions.models import Transaction


class DashboardService:
    """
    首页数据聚合业务服务。

    Dashboard 本身不保存数据，
    只从其它业务模块聚合当前用户的数据。
    """

    @staticmethod
    def get_summary(
        user,
    ):
        """
        获取首页汇总数据。

        返回：

        1. 账户资产汇总；
        2. 本月收入 / 支出 / 结余；
        3. 本月预算情况；
        4. 储蓄目标情况；
        5. 最近账单。
        """

        # ======================================
        # 当前日期
        # ======================================

        today = timezone.localdate()

        year = today.year
        month = today.month

        # ======================================
        # 计算本月开始时间
        # ======================================
        month_start = timezone.make_aware(
            datetime(
                year=year,
                month=month,
                day=1,
            )
        )
        # 处理 12 月跨年。
        if month == 12:
            next_month_start = timezone.make_aware(
                datetime(
                    year=year + 1,
                    month=1,
                    day=1,
                )
            )
        else:
            next_month_start = timezone.make_aware(
                datetime(
                    year=year,
                    month=month + 1,
                    day=1,
                )
            )

        # ======================================
        # 1. 账户资产汇总
        # ======================================

        accounts = Account.objects.filter(
            user=user,
            is_deleted=False,
            is_active=True,
        )

        total_assets = Decimal("0.00")

        total_liabilities = Decimal("0.00")

        for account in accounts:
            # 正数作为资产。
            if account.balance >= 0:
                total_assets += account.balance

            # 负数绝对值作为负债。
            else:
                total_liabilities += abs(account.balance)

        # 净资产。
        net_assets = total_assets - total_liabilities

        # ======================================
        # 2. 本月收入 / 支出
        # ======================================

        month_transactions = Transaction.objects.filter(
            user=user,
            status="normal",
            transaction_time__gte=(month_start),
            transaction_time__lt=(next_month_start),
        )

        income_result = month_transactions.filter(transaction_type="income").aggregate(
            total=Sum("amount")
        )

        expense_result = month_transactions.filter(
            transaction_type="expense"
        ).aggregate(total=Sum("amount"))

        month_income = income_result["total"] or Decimal("0.00")

        month_expense = expense_result["total"] or Decimal("0.00")

        # 本月结余。
        month_balance = month_income - month_expense

        # ======================================
        # 3. 本月预算
        # ======================================

        budgets = Budget.objects.filter(
            user=user,
            year=year,
            month=month,
            is_deleted=False,
            is_active=True,
        )

        # 优先查总预算。
        overall_budget = budgets.filter(budget_type=(Budget.BudgetType.OVERALL)).first()

        budget_amount = Decimal("0.00")

        budget_spent = Decimal("0.00")

        budget_remaining = Decimal("0.00")

        budget_usage_percentage = Decimal("0.00")

        # ======================================
        # 存在总预算
        # ======================================

        if overall_budget:
            budget_amount = overall_budget.amount

            # 总预算使用全部本月支出。
            budget_spent = month_expense

        # ======================================
        # 不存在总预算
        # 使用分类预算金额之和
        # ======================================

        else:
            # 获取当前月份所有启用的分类预算。
            category_budgets = budgets.filter(budget_type=Budget.BudgetType.CATEGORY)

            # 统计分类预算总金额。
            category_budget_result = category_budgets.aggregate(total=Sum("amount"))

            budget_amount = category_budget_result["total"] or Decimal("0.00")

            # 获取已经设置预算的分类 ID。
            budget_category_ids = category_budgets.exclude(
                category_id__isnull=True
            ).values_list(
                "category_id",
                flat=True,
            )

            # 只统计这些预算分类对应的支出。
            category_expense_result = month_transactions.filter(
                transaction_type="expense",
                category_id__in=budget_category_ids,
            ).aggregate(total=Sum("amount"))

            budget_spent = category_expense_result["total"] or Decimal("0.00")

        # ======================================
        # 预算剩余
        # ======================================

        budget_remaining = budget_amount - budget_spent

        if budget_remaining < 0:
            budget_remaining = Decimal("0.00")

        # ======================================
        # 预算使用率
        # ======================================

        if budget_amount > 0:
            budget_usage_percentage = budget_spent / budget_amount * Decimal("100")

            budget_usage_percentage = budget_usage_percentage.quantize(Decimal("0.01"))

        # ======================================
        # 4. 储蓄目标汇总
        # ======================================

        savings_goals = SavingsGoal.objects.filter(
            user=user,
            is_deleted=False,
        )

        savings_result = savings_goals.aggregate(
            total_target=Sum("target_amount"),
            total_current=Sum("current_amount"),
        )

        savings_target_amount = savings_result["total_target"] or Decimal("0.00")

        savings_current_amount = savings_result["total_current"] or Decimal("0.00")

        savings_remaining_amount = savings_target_amount - savings_current_amount

        if savings_remaining_amount < 0:
            savings_remaining_amount = Decimal("0.00")

        savings_progress_percentage = Decimal("0.00")

        if savings_target_amount > 0:
            savings_progress_percentage = (
                savings_current_amount / savings_target_amount * Decimal("100")
            )

            savings_progress_percentage = savings_progress_percentage.quantize(
                Decimal("0.01")
            )

        # ======================================
        # 储蓄状态数量
        # ======================================

        savings_total_count = savings_goals.count()

        savings_active_count = savings_goals.filter(
            status=(SavingsGoal.Status.ACTIVE)
        ).count()
        # ======================================
        # 暂停状态储蓄目标数量
        # ======================================

        savings_paused_count = savings_goals.filter(
            status=(SavingsGoal.Status.PAUSED)
        ).count()

        savings_completed_count = savings_goals.filter(
            status=(SavingsGoal.Status.COMPLETED)
        ).count()

        # ======================================
        # 5. 最近账单
        # ======================================

        recent_transactions = (
            Transaction.objects.filter(
                user=user,
                status="normal",
            )
            .select_related(
                "account",
                "category",
            )
            .order_by(
                "-transaction_time",
                "-id",
            )[:5]
        )

        recent_transaction_list = []

        for item in recent_transactions:
            recent_transaction_list.append(
                {
                    "id": item.id,
                    "transaction_type": (item.transaction_type),
                    "amount": (f"{item.amount:.2f}"),
                    "account_id": (item.account_id),
                    "account_name": (item.account.name if item.account else None),
                    "category_id": (item.category_id),
                    "category_name": (item.category.name if item.category else None),
                    "merchant": (item.merchant),
                    "note": (item.note),
                    "transaction_time": (
                        timezone.localtime(item.transaction_time).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    ),
                }
            )

        # ======================================
        # 最终返回
        # ======================================

        return {
            # 当前统计月份。
            "year": year,
            "month": month,
            # ==================================
            # 资产数据
            # ==================================
            "assets": {
                "total_assets": (f"{total_assets:.2f}"),
                "total_liabilities": (f"{total_liabilities:.2f}"),
                "net_assets": (f"{net_assets:.2f}"),
                "account_count": (accounts.count()),
            },
            # ==================================
            # 本月收支
            # ==================================
            "month_statistics": {
                "income": (f"{month_income:.2f}"),
                "expense": (f"{month_expense:.2f}"),
                "balance": (f"{month_balance:.2f}"),
            },
            # ==================================
            # 本月预算
            # ==================================
            "budget": {
                "amount": (f"{budget_amount:.2f}"),
                "spent_amount": (f"{budget_spent:.2f}"),
                "remaining_amount": (f"{budget_remaining:.2f}"),
                "usage_percentage": (f"{budget_usage_percentage:.2f}"),
                "has_budget": (budgets.exists()),
            },
            # ==================================
            # 储蓄目标
            # ==================================
            "savings": {
                "total_count": (savings_total_count),
                "active_count": (savings_active_count),
                "paused_count": (savings_paused_count),
                "completed_count": (savings_completed_count),
                "target_amount": (f"{savings_target_amount:.2f}"),
                "current_amount": (f"{savings_current_amount:.2f}"),
                "remaining_amount": (f"{savings_remaining_amount:.2f}"),
                "progress_percentage": (f"{savings_progress_percentage:.2f}"),
            },
            # ==================================
            # 最近账单
            # ==================================
            "recent_transactions": (recent_transaction_list),
        }
