from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from apps.categories.models import Category
from apps.transactions.models import Transaction
from common.exceptions import BusinessException

from .models import Budget


class BudgetService:
    """
    预算业务服务类。

    所有预算核心业务逻辑统一放在这里。
    """

    @staticmethod
    @transaction.atomic
    def create_budget(
        user,
        validated_data: dict,
    ):
        """
        创建预算。

        业务规则：

        1. 预算只能属于当前登录用户；
        2. 一个用户每月只能有一个总预算；
        3. 同一个月同一个分类只能有一个分类预算；
        4. 分类预算只能使用支出分类；
        5. 用户不能使用其他用户的自定义分类；
        6. 已删除或已停用分类不能使用。
        """

        # ======================================
        # 获取请求参数
        # ======================================

        # 获取预算类型：
        # overall：总预算
        # category：分类预算
        budget_type = validated_data["budget_type"]

        # 分类 ID。
        #
        # 总预算时为 None。
        # 分类预算时必须存在。
        category_id = validated_data.get("category_id")

        # 预算年份。
        year = validated_data["year"]

        # 预算月份。
        month = validated_data["month"]

        # 预算金额。
        amount = validated_data["amount"]

        # 预算提醒阈值。
        alert_threshold = validated_data.get("alert_threshold")

        # 预算备注。
        note = validated_data.get(
            "note",
            "",
        )

        # 分类对象默认设置为空。
        category = None

        # ======================================
        # 创建月度总预算
        # ======================================

        if budget_type == Budget.BudgetType.OVERALL:
            # 查询当前用户在当前年月
            # 是否已经存在未删除的总预算。
            exists = Budget.objects.filter(
                user=user,
                budget_type=(Budget.BudgetType.OVERALL),
                year=year,
                month=month,
                is_deleted=False,
            ).exists()

            # 一个用户同一个月
            # 只能存在一个有效总预算。
            if exists:
                raise BusinessException("该月份已经存在总预算")

        # ======================================
        # 创建分类预算
        # ======================================

        if budget_type == Budget.BudgetType.CATEGORY:
            # 查询对应分类。
            #
            # 分类必须满足：
            # 1. ID 正确；
            # 2. 未删除；
            # 3. 已启用；
            # 4. 系统分类或者当前用户自己的分类。
            category = (
                Category.objects.filter(
                    id=category_id,
                    is_deleted=False,
                    is_active=True,
                )
                .filter(Q(user__isnull=True) | Q(user=user))
                .first()
            )

            # 分类不存在或无权限访问。
            if not category:
                raise BusinessException("分类不存在")

            # 当前预算模块用于控制支出，
            # 因此分类预算只能选择支出分类。
            if category.category_type != Category.CategoryType.EXPENSE:
                raise BusinessException("预算只能选择支出分类")

            # 检查当前用户在当前年月
            # 是否已经给这个分类设置预算。
            exists = Budget.objects.filter(
                user=user,
                budget_type=(Budget.BudgetType.CATEGORY),
                category=category,
                year=year,
                month=month,
                is_deleted=False,
            ).exists()

            # 同年月同分类
            # 不允许重复创建预算。
            if exists:
                raise BusinessException("该月份已经存在此分类预算")

        # ======================================
        # 创建预算
        # ======================================

        budget = Budget.objects.create(
            # 当前登录用户。
            user=user,
            # 预算类型。
            budget_type=budget_type,
            # 分类。
            category=category,
            # 年份。
            year=year,
            # 月份。
            month=month,
            # 预算金额。
            amount=amount,
            # 提醒阈值。
            alert_threshold=alert_threshold,
            # 备注。
            note=note,
        )

        # 返回新创建的预算对象。
        return budget

    @staticmethod
    def get_budget_list(
        user,
        query_params: dict,
    ):
        """
        获取当前用户预算列表。

        支持筛选：

        1. year；
        2. month；
        3. budget_type；
        4. is_active；
        5. category_id。

        查询规则：

        1. 只查询当前登录用户；
        2. 只查询未逻辑删除预算。
        """

        # ======================================
        # 基础查询
        # ======================================

        queryset = Budget.objects.filter(
            # 只能查询当前用户自己的预算。
            user=user,
            # 已删除预算不展示。
            is_deleted=False,
        ).select_related(
            # 一次性查询分类，
            # 避免序列化时产生 N+1 查询。
            "category"
        )

        # ======================================
        # 年份筛选
        # ======================================

        year = query_params.get("year")

        if year is not None:
            queryset = queryset.filter(year=year)

        # ======================================
        # 月份筛选
        # ======================================

        month = query_params.get("month")

        if month is not None:
            queryset = queryset.filter(month=month)

        # ======================================
        # 预算类型筛选
        # ======================================

        budget_type = query_params.get("budget_type")

        if budget_type:
            queryset = queryset.filter(budget_type=budget_type)

        # ======================================
        # 启用状态筛选
        # ======================================

        is_active = query_params.get("is_active")

        # Boolean 值可能是 False，
        # 所以不能写：
        #
        # if is_active:
        #
        # 否则 false 会被跳过。
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        # ======================================
        # 分类筛选
        # ======================================

        category_id = query_params.get("category_id")

        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)

        # ======================================
        # 排序
        # ======================================
        return queryset.order_by(
            # 最新年份优先。
            "-year",
            # 最新月份优先。
            "-month",
            # 同月先按预算类型。
            "budget_type",
            # 保证排序稳定。
            "id",
        )

    @staticmethod
    def get_budget_detail(
        user,
        budget_id,
    ):
        """
        获取预算详情。

        查询规则：
        1. 只能查询当前登录用户自己的预算；
        2. 已逻辑删除预算不能查询。
        """

        # 查询当前用户指定预算。
        budget = (
            Budget.objects.filter(
                id=budget_id,
                user=user,
                is_deleted=False,
            )
            .select_related("category")
            .first()
        )

        # 查询不到时统一抛业务异常。
        if not budget:
            raise BusinessException("预算不存在")

        return budget

    @staticmethod
    @transaction.atomic
    def update_budget(
        user,
        budget_id,
        validated_data: dict,
    ):
        """
        修改预算。

        当前允许修改：
        1. 预算金额；
        2. 提醒阈值；
        3. 备注；
        4. 是否启用。
        """

        # ======================================
        # 锁定预算记录
        # ======================================

        # 修改过程中使用 select_for_update，
        # 防止两个请求同时修改同一条预算。
        budget = (
            Budget.objects.select_for_update()
            .filter(
                id=budget_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if not budget:
            raise BusinessException("预算不存在")

        # ======================================
        # 修改预算金额
        # ======================================

        if "amount" in validated_data:
            budget.amount = validated_data["amount"]

        # ======================================
        # 修改提醒阈值
        # ======================================

        if "alert_threshold" in validated_data:
            budget.alert_threshold = validated_data["alert_threshold"]

        # ======================================
        # 修改备注
        # ======================================

        if "note" in validated_data:
            budget.note = validated_data["note"]

        # ======================================
        # 修改启用状态
        # ======================================

        if "is_active" in validated_data:
            budget.is_active = validated_data["is_active"]

        # 保存修改结果。
        budget.save(
            update_fields=[
                "amount",
                "alert_threshold",
                "note",
                "is_active",
                "updated_at",
            ]
        )

        return budget

    @staticmethod
    @transaction.atomic
    def delete_budget(
        user,
        budget_id,
    ):
        """
        删除预算。

        采用逻辑删除，
        不物理删除数据库记录。
        """

        # 锁定目标预算。
        budget = (
            Budget.objects.select_for_update()
            .filter(
                id=budget_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if not budget:
            raise BusinessException("预算不存在")

        # 设置逻辑删除状态。
        budget.is_deleted = True

        # 删除后同时禁用，
        # 避免后续统计误使用。
        budget.is_active = False

        # 保存状态。
        budget.save(
            update_fields=[
                "is_deleted",
                "is_active",
                "updated_at",
            ]
        )

    @staticmethod
    def get_budget_progress(
        user,
        query_params: dict,
    ):
        """
        获取预算执行进度。

        业务规则：

        1. 只查询当前用户；
        2. 只查询未删除预算；
        3. 只统计启用预算；
        4. 总预算统计该月全部支出；
        5. 分类预算只统计对应分类支出；
        6. 已逻辑删除账单不参与统计。
        """

        # ======================================
        # 获取年月
        # ======================================

        year = query_params.get("year")

        month = query_params.get("month")

        # 如果前端没有传年月，
        # 默认使用当前年月。
        if year is None and month is None:
            current_date = timezone.localdate()

            year = current_date.year
            month = current_date.month

        # ======================================
        # 查询当前月份预算
        # ======================================

        budgets = (
            Budget.objects.filter(
                user=user,
                year=year,
                month=month,
                is_active=True,
                is_deleted=False,
            )
            .select_related("category")
            .order_by(
                "budget_type",
                "id",
            )
        )

        # ======================================
        # 计算该月时间范围
        # ======================================

        # 当前月第一天。
        start_date = datetime(
            year,
            month,
            1,
        )

        # 处理下个月第一天。
        if month == 12:
            next_month_date = datetime(
                year + 1,
                1,
                1,
            )

        else:
            next_month_date = datetime(
                year,
                month + 1,
                1,
            )

        # 转为 Django 当前时区。
        start_datetime = timezone.make_aware(start_date)

        next_month_datetime = timezone.make_aware(next_month_date)

        # ======================================
        # 查询本月全部支出账单
        # ======================================

        expense_queryset = Transaction.objects.filter(
            user=user,
            status=(Transaction.Status.NORMAL),
            transaction_type=(Transaction.TransactionType.EXPENSE),
            transaction_time__gte=(start_datetime),
            transaction_time__lt=(next_month_datetime),
        )

        # ======================================
        # 计算本月全部支出
        # ======================================

        total_expense_result = expense_queryset.aggregate(total=Sum("amount"))

        total_expense = total_expense_result["total"] or Decimal("0.00")

        # ======================================
        # 构造预算执行进度
        # ======================================

        progress_list = []

        for budget in budgets:
            # 默认已支出为 0。
            spent_amount = Decimal("0.00")

            # ==================================
            # 总预算
            # ==================================

            if budget.budget_type == Budget.BudgetType.OVERALL:
                # 总预算统计该月全部支出。
                spent_amount = total_expense

            # ==================================
            # 分类预算
            # ==================================

            elif budget.budget_type == Budget.BudgetType.CATEGORY:
                # 只统计该分类支出。
                category_result = expense_queryset.filter(
                    category=budget.category
                ).aggregate(total=Sum("amount"))

                spent_amount = category_result["total"] or Decimal("0.00")

            # ==================================
            # 计算剩余预算
            # ==================================

            remaining_amount = budget.amount - spent_amount

            # ==================================
            # 计算预算使用率
            # ==================================

            # 预算金额在数据库层已经保证 > 0，
            # 这里仍然做防御性处理。
            usage_percentage = Decimal("0.00")

            if budget.amount > 0:
                usage_percentage = spent_amount / budget.amount * Decimal("100")

                # 保留两位小数。
                usage_percentage = usage_percentage.quantize(Decimal("0.01"))

            # ==================================
            # 是否达到提醒阈值
            # ==================================

            is_alert = usage_percentage >= budget.alert_threshold

            # ==================================
            # 是否已经超出预算
            # ==================================

            is_over_budget = spent_amount > budget.amount

            # ==================================
            # 添加返回结果
            # ==================================

            progress_list.append(
                {
                    "budget_id": budget.id,
                    "budget_type": (budget.budget_type),
                    "budget_type_display": (budget.get_budget_type_display()),
                    "category_id": (budget.category_id),
                    "category_name": (
                        budget.category.name if budget.category else None
                    ),
                    "year": budget.year,
                    "month": budget.month,
                    "budget_amount": (budget.amount),
                    "spent_amount": (spent_amount),
                    "remaining_amount": (remaining_amount),
                    "usage_percentage": (usage_percentage),
                    "alert_threshold": (budget.alert_threshold),
                    "is_alert": is_alert,
                    "is_over_budget": (is_over_budget),
                }
            )

        # 返回当前年月以及预算进度。
        return {
            "year": year,
            "month": month,
            "budgets": progress_list,
        }

    @staticmethod
    def get_budget_overview(
        user,
        query_params: dict,
    ):
        """
        获取预算概览。

        注意：

        总预算和分类预算可能同时存在，
        因此“已支出”不能直接把每条预算
        的 spent_amount 全部相加，
        否则会重复统计支出。
        """

        # 获取预算执行进度。
        progress = BudgetService.get_budget_progress(
            user=user,
            query_params=query_params,
        )

        budgets = progress["budgets"]

        # ======================================
        # 初始化
        # ======================================

        # 总预算金额。
        #
        # 如果存在 overall 总预算，
        # 优先使用总预算作为月度总预算。
        total_budget = Decimal("0.00")

        # 月度真实支出。
        total_spent = Decimal("0.00")

        # 提醒预算数量。
        alert_count = 0

        # 超支预算数量。
        over_budget_count = 0

        # 是否已经找到总预算。
        has_overall_budget = False

        # ======================================
        # 第一次遍历：
        # 查找总预算
        # ======================================

        for item in budgets:
            if item["budget_type"] == Budget.BudgetType.OVERALL:
                # 总预算作为当月总体预算金额。
                total_budget = item["budget_amount"]

                # 总预算的 spent_amount
                # 就是本月真实全部支出。
                total_spent = item["spent_amount"]

                has_overall_budget = True

                # 正常情况下一个月只有一个总预算。
                break

        # ======================================
        # 如果没有总预算
        # ======================================

        if not has_overall_budget:
            # 没有总预算时，
            # 才使用分类预算金额之和作为预算总额。
            for item in budgets:
                total_budget += item["budget_amount"]

            # 分类预算之间对应不同分类，
            # 可以累加分类支出。
            for item in budgets:
                total_spent += item["spent_amount"]

        # ======================================
        # 统计预警和超支数量
        # ======================================

        for item in budgets:
            if item["is_alert"]:
                alert_count += 1

            if item["is_over_budget"]:
                over_budget_count += 1

        # ======================================
        # 剩余预算
        # ======================================

        total_remaining = total_budget - total_spent

        # ======================================
        # 总预算使用率
        # ======================================

        usage_percentage = Decimal("0.00")

        if total_budget > 0:
            usage_percentage = total_spent / total_budget * Decimal("100")

            usage_percentage = usage_percentage.quantize(Decimal("0.01"))

        # ======================================
        # 返回结果
        # ======================================

        return {
            "year": progress["year"],
            "month": progress["month"],
            "total_budget": total_budget,
            "total_spent": total_spent,
            "total_remaining": (total_remaining),
            "usage_percentage": (usage_percentage),
            "budget_count": len(budgets),
            "alert_count": alert_count,
            "over_budget_count": (over_budget_count),
        }

    @staticmethod
    @transaction.atomic
    def copy_budgets(
        user,
        validated_data: dict,
    ):
        """
        复制月度预算。

        业务规则：

        1. 只能复制当前用户自己的预算；
        2. 只复制未删除预算；
        3. 来源月份没有预算时返回业务异常；
        4. 目标月份已存在相同预算时跳过；
        5. 总预算按“总预算”唯一判断；
        6. 分类预算按“分类”唯一判断；
        7. 保留预算金额、提醒阈值、备注、启用状态。
        """

        # ======================================
        # 获取参数
        # ======================================

        source_year = validated_data["source_year"]

        source_month = validated_data["source_month"]

        target_year = validated_data["target_year"]

        target_month = validated_data["target_month"]

        # ======================================
        # 查询来源月份预算
        # ======================================

        source_budgets = (
            Budget.objects.filter(
                user=user,
                year=source_year,
                month=source_month,
                is_deleted=False,
            )
            .select_related("category")
            .order_by("id")
        )

        # 如果来源月份没有任何预算，
        # 不执行复制。
        if not source_budgets.exists():
            raise BusinessException("来源月份没有可复制的预算")

        # ======================================
        # 初始化统计
        # ======================================

        created_budgets = []

        skipped_count = 0

        # ======================================
        # 遍历来源预算
        # ======================================

        for source_budget in source_budgets:
            # 默认目标月份不存在相同预算。
            exists = False

            # ==================================
            # 总预算重复判断
            # ==================================

            if source_budget.budget_type == Budget.BudgetType.OVERALL:
                exists = Budget.objects.filter(
                    user=user,
                    budget_type=(Budget.BudgetType.OVERALL),
                    year=target_year,
                    month=target_month,
                    is_deleted=False,
                ).exists()

            # ==================================
            # 分类预算重复判断
            # ==================================

            elif source_budget.budget_type == Budget.BudgetType.CATEGORY:
                exists = Budget.objects.filter(
                    user=user,
                    budget_type=(Budget.BudgetType.CATEGORY),
                    category=(source_budget.category),
                    year=target_year,
                    month=target_month,
                    is_deleted=False,
                ).exists()

            # ==================================
            # 已存在则跳过
            # ==================================

            if exists:
                skipped_count += 1
                continue

            # ==================================
            # 创建目标月份预算
            # ==================================

            new_budget = Budget.objects.create(
                # 当前用户。
                user=user,
                # 保留预算类型。
                budget_type=(source_budget.budget_type),
                # 保留分类。
                category=(source_budget.category),
                # 使用目标年月。
                year=target_year,
                month=target_month,
                # 保留预算金额。
                amount=(source_budget.amount),
                # 保留提醒阈值。
                alert_threshold=(source_budget.alert_threshold),
                # 保留备注。
                note=(source_budget.note),
                # 保留启用状态。
                is_active=(source_budget.is_active),
            )

            created_budgets.append(new_budget)

        # ======================================
        # 返回复制结果
        # ======================================

        return {
            "source_year": source_year,
            "source_month": source_month,
            "target_year": target_year,
            "target_month": target_month,
            "created_count": len(created_budgets),
            "skipped_count": skipped_count,
            "created_budgets": (created_budgets),
        }
