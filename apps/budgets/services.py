from django.db import transaction
from django.db.models import Q

from apps.categories.models import Category
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
    ):
        """
        获取当前用户预算列表。

        查询规则：

        1. 只查询当前登录用户；
        2. 只查询未删除预算；
        3. 同时查询关联分类，减少数据库查询次数；
        4. 按年份、月份倒序排列。
        """

        # ======================================
        # 查询预算
        # ======================================

        queryset = (
            Budget.objects.filter(
                # 当前登录用户。
                user=user,
                # 只查询未删除记录。
                is_deleted=False,
            )
            # category 是外键，
            # 使用 select_related 避免列表序列化时
            # 每条预算都额外查询一次分类表。
            .select_related("category").order_by(
                # 最新年份优先。
                "-year",
                # 最新月份优先。
                "-month",
                # 同月情况下按照预算类型排列。
                "budget_type",
                # 最后使用 ID 保证排序稳定。
                "id",
            )
        )

        # 返回 QuerySet。
        return queryset
