from datetime import datetime, time
from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, ExtractMonth
from django.utils import timezone
from apps.tags.models import Tag
from common.exceptions import BusinessException

from apps.accounts.models import Account
from apps.categories.models import Category

from .models import Transaction, TransactionImage


class TransactionService:
    """
    账单业务服务。
    """

    @staticmethod
    @transaction.atomic
    def create_transaction(
        user,
        validated_data: dict,
    ) -> Transaction:
        """
        创建收入 / 支出账单。

        规则：
        1. 账户必须属于当前用户；
        2. 分类必须是系统分类或当前用户自己的分类；
        3. 分类类型必须和账单类型一致；
        4. 标签必须属于当前用户且未删除；
        5. 支出扣减账户余额；
        6. 收入增加账户余额；
        7. 余额更新、账单创建、标签绑定必须在同一事务。
        """

        # ==========================================
        # 拷贝请求参数
        # ==========================================
        #
        # 不直接修改 serializer.validated_data，
        # 避免对后续代码产生副作用。
        # ==========================================

        data = validated_data.copy()

        # ==========================================
        # 取出标签 ID
        # ==========================================
        #
        # tag_ids 不是 Transaction 普通数据库字段，
        # 需要单独处理。
        #
        # 新增账单未传 tag_ids 时默认没有标签。
        # ==========================================

        tag_ids = data.pop(
            "tag_ids",
            [],
        )

        # ==========================================
        # 获取基础参数
        # ==========================================

        account_id = data["account_id"]

        category_id = data["category_id"]

        transaction_type = data["transaction_type"]

        amount = data["amount"]

        # ==========================================
        # 锁定账户
        # ==========================================

        try:
            account = Account.objects.select_for_update().get(
                id=account_id,
                user=user,
                is_deleted=False,
                is_active=True,
            )

        except Account.DoesNotExist:
            raise BusinessException("账户不存在")

        # ==========================================
        # 查询分类
        # ==========================================

        category_filter = Q(
            id=category_id,
            user__isnull=True,
            is_system=True,
        ) | Q(
            id=category_id,
            user=user,
            is_system=False,
        )

        try:
            category = Category.objects.filter(
                category_filter,
                is_deleted=False,
                is_active=True,
            ).get()

        except Category.DoesNotExist:
            raise BusinessException("分类不存在")

        # ==========================================
        # 分类类型校验
        # ==========================================

        if category.category_type != transaction_type:
            raise BusinessException("分类类型与账单类型不一致")

        # ==========================================
        # 校验标签
        # ==========================================
        #
        # 标签只能使用：
        #
        # 1. 当前登录用户自己的标签；
        # 2. 未逻辑删除的标签。
        #
        # 如果 tag_ids = []，
        # 则表示该账单不绑定标签。
        # ==========================================

        tags = []

        if tag_ids:
            tags = list(
                Tag.objects.filter(
                    id__in=tag_ids,
                    user=user,
                    is_deleted=False,
                )
            )

            # Serializer 已经做了 ID 去重，
            # 这里再次 set() 属于防御性处理。
            #
            # 如果数量不同，说明存在：
            # - 不存在的标签；
            # - 已删除标签；
            # - 其他用户的标签。
            if len(tags) != len(set(tag_ids)):
                raise BusinessException("存在无效标签")

        # ==========================================
        # 处理账户余额
        # ==========================================

        if transaction_type == Transaction.TransactionType.EXPENSE:
            # ======================================
            # 支出
            # ======================================
            #
            # 非信用卡账户余额不足时禁止支出。
            # 信用卡允许出现负余额。
            # ======================================

            is_credit_card = account.account_type == Account.AccountType.CREDIT_CARD

            if not is_credit_card and account.balance < amount:
                raise BusinessException("账户余额不足")

            account.balance -= amount

        else:
            # ======================================
            # 收入
            # ======================================

            account.balance += amount

        # ==========================================
        # 保存账户余额
        # ==========================================

        account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # ==========================================
        # 创建账单
        # ==========================================

        transaction_record = Transaction.objects.create(
            user=user,
            account=account,
            category=category,
            transaction_type=(transaction_type),
            amount=amount,
            transaction_time=(data["transaction_time"]),
            merchant=data.get(
                "merchant",
                "",
            ),
            note=data.get(
                "note",
                "",
            ),
        )

        # ==========================================
        # 绑定账单标签
        # ==========================================
        #
        # ManyToManyField 必须等 Transaction
        # 保存并获得主键之后才能调用 set()。
        # ==========================================

        if tags:
            transaction_record.tags.set(tags)

        return transaction_record

    @staticmethod
    def get_transaction_list(
        user,
        query_params: dict,
    ):
        """
        获取当前用户账单列表。

        支持：
        1. 收入 / 支出筛选；
        2. 账户筛选；
        3. 分类筛选；
        4. 日期范围筛选；
        5. 商户 / 备注关键字搜索。
        """

        # 只查询当前用户正常账单。
        queryset = Transaction.objects.filter(
            user=user,
            status=Transaction.Status.NORMAL,
        ).select_related(
            "account",
            "category",
        )

        # ==============================
        # 账单类型
        # ==============================

        transaction_type = query_params.get("transaction_type")

        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        # ==============================
        # 账户
        # ==============================

        account_id = query_params.get("account_id")

        if account_id:
            queryset = queryset.filter(account_id=account_id)

        # ==============================
        # 分类
        # ==============================

        category_id = query_params.get("category_id")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # ==============================
        # 开始日期
        # ==============================

        start_date = query_params.get("start_date")

        if start_date:
            # 转成当天 00:00:00。
            start_datetime = datetime.combine(
                start_date,
                time.min,
            )

            # 转成当前 Django 时区。
            start_datetime = timezone.make_aware(start_datetime)

            queryset = queryset.filter(transaction_time__gte=(start_datetime))

        # ==============================
        # 结束日期
        # ==============================

        end_date = query_params.get("end_date")

        if end_date:
            # 转成当天 23:59:59.999999。
            end_datetime = datetime.combine(
                end_date,
                time.max,
            )

            end_datetime = timezone.make_aware(end_datetime)

            queryset = queryset.filter(transaction_time__lte=(end_datetime))

        # ==============================
        # 关键字搜索
        # ==============================

        keyword = query_params.get("keyword")

        if keyword:
            # 搜索商户或备注。
            keyword_filter = Q(merchant__icontains=keyword) | Q(note__icontains=keyword)

            queryset = queryset.filter(keyword_filter)

        # 最新账单优先。
        return queryset.order_by(
            "-transaction_time",
            "-id",
        )

    @staticmethod
    def get_transaction_detail(
        user,
        transaction_id: int,
    ) -> Transaction:
        """
        获取当前用户账单详情。
        """

        try:
            transaction_record = Transaction.objects.select_related(
                "account",
                "category",
            ).get(
                id=transaction_id,
                user=user,
                status=Transaction.Status.NORMAL,
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        return transaction_record

    @staticmethod
    @transaction.atomic
    def update_transaction(
        user,
        transaction_id: int,
        validated_data: dict,
    ) -> Transaction:
        """
        修改账单。

        核心流程：

        1. 锁定原账单；
        2. 处理标签修改参数；
        3. 校验标签；
        4. 锁定涉及账户；
        5. 回滚原账单余额影响；
        6. 校验新账户、新分类；
        7. 应用新账单余额影响；
        8. 更新账单记录；
        9. 更新账单标签。

        标签规则：

        不传 tag_ids：
            保持原标签不变。

        tag_ids = []：
            清空全部标签。

        tag_ids = [1, 2]：
            替换为标签 1、2。
        """

        # ==========================================
        # 拷贝请求参数
        # ==========================================
        #
        # 不直接修改 serializer.validated_data。
        # ==========================================

        data = validated_data.copy()

        # ==========================================
        # 判断本次是否修改标签
        # ==========================================

        has_tag_update = "tag_ids" in data

        # tag_ids 不是 Transaction 普通字段，
        # 单独取出。
        tag_ids = data.pop(
            "tag_ids",
            None,
        )

        # ==========================================
        # 锁定原账单
        # ==========================================

        try:
            old_transaction = Transaction.objects.select_for_update().get(
                id=transaction_id,
                user=user,
                status=(Transaction.Status.NORMAL),
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        # ==========================================
        # 校验新标签
        # ==========================================
        #
        # tags = None：
        # 本次没有修改标签。
        #
        # tags = []：
        # 本次清空标签。
        #
        # tags = [Tag, Tag]：
        # 替换为新的标签。
        # ==========================================

        tags = None

        if has_tag_update:
            # ======================================
            # tag_ids = []
            # 表示清空全部标签
            # ======================================

            if not tag_ids:
                tags = []

            else:
                # ==================================
                # 查询当前用户合法标签
                # ==================================

                tags = list(
                    Tag.objects.filter(
                        id__in=tag_ids,
                        user=user,
                        is_deleted=False,
                    )
                )

                # ==================================
                # 标签数量校验
                # ==================================
                #
                # 如果传：
                #
                # [1, 2, 999]
                #
                # 但数据库只能找到：
                #
                # [1, 2]
                #
                # 则说明存在：
                #
                # 1. 不存在的标签；
                # 2. 已删除标签；
                # 3. 其他用户标签。
                # ==================================

                if len(tags) != len(set(tag_ids)):
                    raise BusinessException("存在无效标签")

        # ==========================================
        # 获取修改后的数据
        # ==========================================

        # 修改后的账户 ID。
        new_account_id = data.get(
            "account_id",
            old_transaction.account_id,
        )

        # 修改后的分类 ID。
        new_category_id = data.get(
            "category_id",
            old_transaction.category_id,
        )

        # 修改后的账单类型。
        new_transaction_type = data.get(
            "transaction_type",
            old_transaction.transaction_type,
        )

        # 修改后的金额。
        new_amount = data.get(
            "amount",
            old_transaction.amount,
        )

        # ==========================================
        # 锁定旧账户和新账户
        # ==========================================

        account_ids = sorted(
            set(
                [
                    old_transaction.account_id,
                    new_account_id,
                ]
            )
        )

        accounts = (
            Account.objects.select_for_update()
            .filter(
                id__in=account_ids,
                user=user,
                is_deleted=False,
            )
            .order_by("id")
        )

        account_map = {account.id: account for account in accounts}

        old_account_missing = old_transaction.account_id not in account_map

        new_account_missing = new_account_id not in account_map

        if old_account_missing or new_account_missing:
            raise BusinessException("账户不存在")

        old_account = account_map[old_transaction.account_id]

        new_account = account_map[new_account_id]

        # ==========================================
        # 回滚原账单余额影响
        # ==========================================

        if old_transaction.transaction_type == Transaction.TransactionType.EXPENSE:
            # 原账单是支出。
            #
            # 创建账单时扣除了余额，
            # 修改前先加回来。
            old_account.balance += old_transaction.amount

        else:
            # 原账单是收入。
            #
            # 创建时增加了余额，
            # 修改前先减回来。
            old_account.balance -= old_transaction.amount

        # ==========================================
        # 校验新分类
        # ==========================================

        category_filter = Q(
            id=new_category_id,
            user__isnull=True,
            is_system=True,
        ) | Q(
            id=new_category_id,
            user=user,
            is_system=False,
        )

        try:
            new_category = Category.objects.filter(
                category_filter,
                is_deleted=False,
                is_active=True,
            ).get()

        except Category.DoesNotExist:
            raise BusinessException("分类不存在")

        # ==========================================
        # 分类类型必须与账单类型一致
        # ==========================================

        if new_category.category_type != new_transaction_type:
            raise BusinessException("分类类型与账单类型不一致")

        # ==========================================
        # 应用修改后的账单余额影响
        # ==========================================

        if new_transaction_type == Transaction.TransactionType.EXPENSE:
            # ======================================
            # 支出
            # ======================================

            is_credit_card = new_account.account_type == Account.AccountType.CREDIT_CARD

            # 非信用卡余额不足时禁止支出。
            if not is_credit_card and new_account.balance < new_amount:
                raise BusinessException("账户余额不足")

            new_account.balance -= new_amount

        else:
            # ======================================
            # 收入
            # ======================================

            new_account.balance += new_amount

        # ==========================================
        # 保存账户余额
        # ==========================================

        # 如果是不同账户，
        # 分别保存两个账户。
        if new_account.id != old_account.id:
            old_account.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

            new_account.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

        else:
            # ======================================
            # 同一个账户
            # ======================================
            #
            # old_account 和 new_account
            # 实际是同一个 Python 对象。
            #
            # 此时余额已经完成：
            #
            # 回滚旧账单
            # +
            # 应用新账单
            #
            # 保存一次即可。
            # ======================================

            old_account.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

        # ==========================================
        # 更新账单主体数据
        # ==========================================

        old_transaction.account = new_account

        old_transaction.category = new_category

        old_transaction.transaction_type = new_transaction_type

        old_transaction.amount = new_amount

        # ==========================================
        # 修改交易时间
        # ==========================================

        if "transaction_time" in data:
            old_transaction.transaction_time = data["transaction_time"]

        # ==========================================
        # 修改商户
        # ==========================================

        if "merchant" in data:
            old_transaction.merchant = data["merchant"]

        # ==========================================
        # 修改备注
        # ==========================================

        if "note" in data:
            old_transaction.note = data["note"]

        # ==========================================
        # 保存账单
        # ==========================================

        old_transaction.save()

        # ==========================================
        # 更新标签
        # ==========================================
        #
        # 只有请求中真的传了 tag_ids
        # 才修改标签。
        #
        # 不传：
        # 原标签保持不变。
        #
        # []：
        # set([]) 会清空标签。
        #
        # [1, 2]：
        # 替换为指定标签。
        # ==========================================

        if has_tag_update:
            old_transaction.tags.set(tags)

        return old_transaction

    @staticmethod
    @transaction.atomic
    def delete_transaction(
        user,
        transaction_id: int,
    ) -> None:
        """
        删除账单。

        实际为逻辑删除，并回滚余额影响。
        """

        try:
            # 锁定账单。
            transaction_record = Transaction.objects.select_for_update().get(
                id=transaction_id,
                user=user,
                status=Transaction.Status.NORMAL,
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        try:
            # 锁定关联账户。
            account = Account.objects.select_for_update().get(
                id=transaction_record.account_id,
                user=user,
            )

        except Account.DoesNotExist:
            raise BusinessException("账单关联账户不存在")

        # 原账单是支出：
        # 删除时把钱加回来。
        if transaction_record.transaction_type == Transaction.TransactionType.EXPENSE:
            account.balance += transaction_record.amount

        # 原账单是收入：
        # 删除时把钱扣回来。
        else:
            account.balance -= transaction_record.amount

        account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 逻辑删除账单。
        transaction_record.status = Transaction.Status.DELETED

        transaction_record.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    @staticmethod
    def get_transaction_summary(
        user,
        query_params: dict,
    ):
        """
        获取当前用户账单汇总数据。

        支持按开始日期和结束日期进行统计。
        """

        # ==============================
        # 基础查询
        # ==============================

        # 只统计：
        # 1. 当前登录用户；
        # 2. 状态正常的账单。
        queryset = Transaction.objects.filter(
            user=user,
            status=Transaction.Status.NORMAL,
        )

        # ==============================
        # 开始日期筛选
        # ==============================

        start_date = query_params.get("start_date")

        if start_date:
            # 转换为当天 00:00:00。
            start_datetime = datetime.combine(
                start_date,
                time.min,
            )

            # 转换成 Django 当前时区时间。
            start_datetime = timezone.make_aware(start_datetime)

            queryset = queryset.filter(transaction_time__gte=start_datetime)

        # ==============================
        # 结束日期筛选
        # ==============================

        end_date = query_params.get("end_date")

        if end_date:
            # 转换为当天最后一刻。
            end_datetime = datetime.combine(
                end_date,
                time.max,
            )

            # 转换成 Django 当前时区时间。
            end_datetime = timezone.make_aware(end_datetime)

            queryset = queryset.filter(transaction_time__lte=end_datetime)

        # ==============================
        # 收入统计
        # ==============================

        income_summary = queryset.filter(
            transaction_type=(Transaction.TransactionType.INCOME)
        ).aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )

        # ==============================
        # 支出统计
        # ==============================

        expense_summary = queryset.filter(
            transaction_type=(Transaction.TransactionType.EXPENSE)
        ).aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )

        # ==============================
        # 处理空数据
        # ==============================

        # 如果没有收入，
        # Sum 会返回 None。
        total_income = income_summary["total"] or Decimal("0.00")

        # 如果没有支出，
        # Sum 会返回 None。
        total_expense = expense_summary["total"] or Decimal("0.00")

        income_count = income_summary["count"]

        expense_count = expense_summary["count"]

        # ==============================
        # 计算结余
        # ==============================

        balance = total_income - total_expense

        # ==============================
        # 返回汇总结果
        # ==============================

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
            "income_count": income_count,
            "expense_count": expense_count,
            "total_count": (income_count + expense_count),
        }

    @staticmethod
    def get_transaction_trend(
        user,
        query_params: dict,
    ):
        """
        获取当前用户账单趋势数据。

        按天统计：
        1. 收入；
        2. 支出；
        3. 当日结余。
        """

        # ==============================
        # 基础查询
        # ==============================

        # 只查询当前用户正常状态的账单。
        queryset = Transaction.objects.filter(
            user=user,
            status=Transaction.Status.NORMAL,
        )

        # ==============================
        # 开始日期
        # ==============================

        start_date = query_params.get("start_date")

        if start_date:
            # 转换为当天 00:00:00。
            start_datetime = datetime.combine(
                start_date,
                time.min,
            )

            # 转成 Django 当前时区。
            start_datetime = timezone.make_aware(start_datetime)

            queryset = queryset.filter(transaction_time__gte=start_datetime)

        # ==============================
        # 结束日期
        # ==============================

        end_date = query_params.get("end_date")

        if end_date:
            # 转换为当天最后一刻。
            end_datetime = datetime.combine(
                end_date,
                time.max,
            )

            # 转成 Django 当前时区。
            end_datetime = timezone.make_aware(end_datetime)

            queryset = queryset.filter(transaction_time__lte=end_datetime)

        # ==============================
        # 按日期聚合收入
        # ==============================

        income_queryset = (
            queryset.filter(transaction_type=(Transaction.TransactionType.INCOME))
            .annotate(date=TruncDate("transaction_time"))
            .values("date")
            .annotate(total=Sum("amount"))
            .order_by("date")
        )

        # ==============================
        # 按日期聚合支出
        # ==============================

        expense_queryset = (
            queryset.filter(transaction_type=(Transaction.TransactionType.EXPENSE))
            .annotate(date=TruncDate("transaction_time"))
            .values("date")
            .annotate(total=Sum("amount"))
            .order_by("date")
        )

        # ==============================
        # 转为日期 -> 金额字典
        # ==============================

        income_map = {
            item["date"]: (item["total"] or Decimal("0.00")) for item in income_queryset
        }

        expense_map = {
            item["date"]: (item["total"] or Decimal("0.00"))
            for item in expense_queryset
        }

        # ==============================
        # 合并所有存在账单的日期
        # ==============================

        all_dates = sorted(set(income_map.keys()) | set(expense_map.keys()))

        # ==============================
        # 生成趋势数据
        # ==============================

        trend_data = []

        for current_date in all_dates:
            # 当前日期收入。
            income = income_map.get(
                current_date,
                Decimal("0.00"),
            )

            # 当前日期支出。
            expense = expense_map.get(
                current_date,
                Decimal("0.00"),
            )

            # 当前日期结余。
            balance = income - expense

            trend_data.append(
                {
                    "date": current_date,
                    "income": income,
                    "expense": expense,
                    "balance": balance,
                }
            )

        return trend_data

    @staticmethod
    def get_category_statistics(
        user,
        query_params: dict,
    ):
        """
        获取当前用户的分类统计数据。

        统计内容：
        1. 每个分类的金额；
        2. 每个分类的账单数量；
        3. 每个分类金额占总金额的百分比。

        支持：
        1. 收入统计；
        2. 支出统计；
        3. 日期范围统计。
        """

        # ==============================
        # 获取查询参数
        # ==============================

        # 获取账单类型。
        #
        # expense：支出
        # income：收入
        transaction_type = query_params.get("transaction_type")

        # 获取开始日期。
        start_date = query_params.get("start_date")

        # 获取结束日期。
        end_date = query_params.get("end_date")

        # ==============================
        # 基础查询
        # ==============================

        # 只统计：
        # 1. 当前登录用户；
        # 2. 状态正常；
        # 3. 指定收入/支出类型。
        queryset = Transaction.objects.filter(
            user=user,
            status=Transaction.Status.NORMAL,
            transaction_type=transaction_type,
        )

        # ==============================
        # 开始日期筛选
        # ==============================

        if start_date:
            # 将日期转换成当天 00:00:00。
            #
            # 例如：
            # 2026-09-01
            #
            # 转成：
            # 2026-09-01 00:00:00
            start_datetime = datetime.combine(
                start_date,
                time.min,
            )

            # 转换成当前 Django 时区时间。
            start_datetime = timezone.make_aware(start_datetime)

            # 查询开始日期之后的账单。
            queryset = queryset.filter(transaction_time__gte=start_datetime)

        # ==============================
        # 结束日期筛选
        # ==============================

        if end_date:
            # 将结束日期转换成当天最后一刻。
            #
            # 例如：
            # 2026-09-30
            #
            # 转成：
            # 2026-09-30 23:59:59.999999
            end_datetime = datetime.combine(
                end_date,
                time.max,
            )

            # 转换成 Django 当前时区时间。
            end_datetime = timezone.make_aware(end_datetime)

            # 查询结束日期之前的账单。
            queryset = queryset.filter(transaction_time__lte=end_datetime)

        # ==============================
        # 计算总金额
        # ==============================

        # 汇总当前条件下全部账单金额。
        total_result = queryset.aggregate(total_amount=Sum("amount"))

        # 如果没有任何账单，
        # Sum 会返回 None。
        #
        # 因此这里统一转成 Decimal("0.00")。
        total_amount = total_result["total_amount"] or Decimal("0.00")

        # ==============================
        # 按分类分组统计
        # ==============================

        # 按 category_id 和 category__name 分组。
        #
        # 每组计算：
        # 1. amount：总金额；
        # 2. count：账单数量。
        category_queryset = (
            queryset.values(
                "category_id",
                "category__name",
            )
            .annotate(
                amount=Sum("amount"),
                count=Count("id"),
            )
            .order_by("-amount")
        )

        # ==============================
        # 构造结果
        # ==============================

        categories = []

        # 遍历每个分类的统计结果。
        for item in category_queryset:
            # 当前分类金额。
            amount = item["amount"] or Decimal("0.00")

            # 默认占比为 0。
            percentage = Decimal("0.00")

            # 总金额大于 0 时，
            # 才计算百分比。
            if total_amount > 0:
                percentage = amount / total_amount * Decimal("100")

            # 保留两位小数。
            percentage = percentage.quantize(Decimal("0.01"))

            # 加入最终结果。
            categories.append(
                {
                    "category_id": (item["category_id"]),
                    "category_name": (item["category__name"] or "未分类"),
                    "amount": amount,
                    "count": item["count"],
                    "percentage": percentage,
                }
            )

        # ==============================
        # 返回统计数据
        # ==============================

        return {
            "transaction_type": transaction_type,
            "total_amount": total_amount,
            "categories": categories,
        }

    @staticmethod
    def get_monthly_statistics(
        user,
        query_params: dict,
    ):
        """
        获取月度收支统计。

        统计内容：

        1. 当前月份收入；
        2. 当前月份支出；
        3. 当前月份结余；
        4. 上一个月份收入；
        5. 上一个月份支出；
        6. 上一个月份结余；
        7. 收入环比；
        8. 支出环比。

        如果没有传 month，
        默认使用当前月份。
        """

        # ==========================================
        # 获取目标月份
        # ==========================================

        month = query_params.get("month")

        # 如果前端没有传 month，
        # 默认获取当前系统日期。
        if not month:
            # timezone.localdate()
            # 会按照 Django 当前时区获取今天日期。
            current_date = timezone.localdate()

            # 例如：
            # 2026-09
            month = current_date.strftime("%Y-%m")

        # ==========================================
        # 解析当前月份
        # ==========================================

        # 例如：
        #
        # month = 2026-09
        #
        # 解析成：
        # datetime(2026, 9, 1)
        current_month_date = datetime.strptime(
            month,
            "%Y-%m",
        )

        # 当前年份。
        current_year = current_month_date.year

        # 当前月份。
        current_month = current_month_date.month

        # ==========================================
        # 计算上一个月份
        # ==========================================

        # 如果当前月份是 1 月，
        # 上个月就是上一年的 12 月。
        if current_month == 1:
            previous_year = current_year - 1
            previous_month = 12

        else:
            # 普通情况：
            # 年份不变，
            # 月份减 1。
            previous_year = current_year
            previous_month = current_month - 1

        # ==========================================
        # 当前月份基础 QuerySet
        # ==========================================

        current_queryset = Transaction.objects.filter(
            # 只统计当前登录用户。
            user=user,
            # 只统计正常账单。
            status=Transaction.Status.NORMAL,
            # 当前年份。
            transaction_time__year=current_year,
            # 当前月份。
            transaction_time__month=current_month,
        )

        # ==========================================
        # 上个月基础 QuerySet
        # ==========================================

        previous_queryset = Transaction.objects.filter(
            # 只统计当前登录用户。
            user=user,
            # 只统计正常账单。
            status=Transaction.Status.NORMAL,
            # 上一个月份所属年份。
            transaction_time__year=previous_year,
            # 上一个月份。
            transaction_time__month=previous_month,
        )

        # ==========================================
        # 当前月份收入
        # ==========================================

        current_income_result = current_queryset.filter(
            transaction_type=(Transaction.TransactionType.INCOME)
        ).aggregate(total=Sum("amount"))

        # 如果没有收入，
        # Sum 返回 None，
        # 因此统一转换成 0。
        current_income = current_income_result["total"] or Decimal("0.00")

        # ==========================================
        # 当前月份支出
        # ==========================================

        current_expense_result = current_queryset.filter(
            transaction_type=(Transaction.TransactionType.EXPENSE)
        ).aggregate(total=Sum("amount"))

        current_expense = current_expense_result["total"] or Decimal("0.00")

        # ==========================================
        # 上个月收入
        # ==========================================

        previous_income_result = previous_queryset.filter(
            transaction_type=(Transaction.TransactionType.INCOME)
        ).aggregate(total=Sum("amount"))

        previous_income = previous_income_result["total"] or Decimal("0.00")

        # ==========================================
        # 上个月支出
        # ==========================================

        previous_expense_result = previous_queryset.filter(
            transaction_type=(Transaction.TransactionType.EXPENSE)
        ).aggregate(total=Sum("amount"))

        previous_expense = previous_expense_result["total"] or Decimal("0.00")

        # ==========================================
        # 计算结余
        # ==========================================

        # 本月结余。
        current_balance = current_income - current_expense

        # 上月结余。
        previous_balance = previous_income - previous_expense

        # ==========================================
        # 计算收入环比
        # ==========================================

        # 默认收入环比为 None。
        #
        # None 表示：
        # 上个月收入为 0，
        # 无法正常计算百分比。
        income_rate = None

        if previous_income > 0:
            income_rate = (
                (current_income - previous_income) / previous_income * Decimal("100")
            )

            # 保留两位小数。
            income_rate = income_rate.quantize(Decimal("0.01"))

        # ==========================================
        # 计算支出环比
        # ==========================================

        expense_rate = None

        if previous_expense > 0:
            expense_rate = (
                (current_expense - previous_expense) / previous_expense * Decimal("100")
            )

            expense_rate = expense_rate.quantize(Decimal("0.01"))

        # ==========================================
        # 返回统计结果
        # ==========================================

        return {
            # 当前月份。
            "current_month": (f"{current_year:04d}-" f"{current_month:02d}"),
            # 上一个月份。
            "previous_month": (f"{previous_year:04d}-" f"{previous_month:02d}"),
            # 当前月份数据。
            "current": {
                "income": current_income,
                "expense": current_expense,
                "balance": current_balance,
            },
            # 上一个月份数据。
            "previous": {
                "income": previous_income,
                "expense": previous_expense,
                "balance": previous_balance,
            },
            # 环比数据。
            "comparison": {
                "income_rate": income_rate,
                "expense_rate": expense_rate,
            },
        }

    @staticmethod
    def get_yearly_statistics(
        user,
        query_params: dict,
    ):
        """
        获取年度收支统计。

        统计内容：

        1. 全年总收入；
        2. 全年总支出；
        3. 全年总结余；
        4. 1～12 月每月收入；
        5. 1～12 月每月支出；
        6. 1～12 月每月结余。

        如果未传 year，
        默认统计当前年份。
        """

        # ======================================
        # 获取统计年份
        # ======================================

        year = query_params.get("year")

        # 如果前端没有传 year，
        # 使用当前年份。
        if not year:
            year = timezone.localdate().year

        # ======================================
        # 查询当前用户指定年份账单
        # ======================================

        queryset = Transaction.objects.filter(
            # 只查询当前登录用户。
            user=user,
            # 只统计正常账单。
            status=Transaction.Status.NORMAL,
            # 指定年份。
            transaction_time__year=year,
        )

        # ======================================
        # 按月份统计收入
        # ======================================

        income_queryset = (
            queryset.filter(transaction_type=(Transaction.TransactionType.INCOME))
            # 从账单时间中提取月份。
            .annotate(month=ExtractMonth("transaction_time"))
            # 按月份进行分组。
            .values("month")
            # 汇总每个月收入。
            .annotate(total=Sum("amount")).order_by("month")
        )

        # ======================================
        # 按月份统计支出
        # ======================================

        expense_queryset = (
            queryset.filter(transaction_type=(Transaction.TransactionType.EXPENSE))
            # 从账单时间中提取月份。
            .annotate(month=ExtractMonth("transaction_time"))
            # 按月份分组。
            .values("month")
            # 汇总每个月支出。
            .annotate(total=Sum("amount")).order_by("month")
        )

        # ======================================
        # 转换成月份 -> 金额字典
        # ======================================

        # 例如：
        #
        # {
        #     1: Decimal("4400.00"),
        #     2: Decimal("4200.00"),
        # }
        income_map = {
            item["month"]: (item["total"] or Decimal("0.00"))
            for item in income_queryset
        }

        expense_map = {
            item["month"]: (item["total"] or Decimal("0.00"))
            for item in expense_queryset
        }

        # ======================================
        # 初始化全年统计数据
        # ======================================

        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")

        months = []

        # ======================================
        # 固定生成 1～12 月
        # ======================================

        for month in range(
            1,
            13,
        ):
            # 当前月份收入。
            #
            # 如果该月没有收入，
            # 默认返回 0。
            income = income_map.get(
                month,
                Decimal("0.00"),
            )

            # 当前月份支出。
            expense = expense_map.get(
                month,
                Decimal("0.00"),
            )

            # 当前月份结余。
            balance = income - expense

            # 累加全年收入。
            total_income += income

            # 累加全年支出。
            total_expense += expense

            # 保存当前月份统计数据。
            months.append(
                {
                    "month": month,
                    "month_text": (f"{year:04d}-" f"{month:02d}"),
                    "income": income,
                    "expense": expense,
                    "balance": balance,
                }
            )

        # ======================================
        # 计算全年结余
        # ======================================

        total_balance = total_income - total_expense

        # ======================================
        # 返回统计结果
        # ======================================

        return {
            "year": year,
            "total_income": total_income,
            "total_expense": total_expense,
            "total_balance": total_balance,
            "months": months,
        }

    @staticmethod
    @transaction.atomic
    def upload_transaction_image(
        user,
        transaction_id: int,
        image,
    ) -> TransactionImage:
        """
        上传账单图片。

        规则：
        1. 账单必须属于当前用户；
        2. 账单必须处于正常状态；
        3. 图片记录归属当前用户；
        4. 图片与账单建立关联；
        5. 整个过程放在事务中执行。
        """

        # ==========================================
        # 查询账单
        # ==========================================

        try:
            transaction_record = Transaction.objects.select_for_update().get(
                id=transaction_id,
                user=user,
                status=Transaction.Status.NORMAL,
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        # ==========================================
        # 创建账单图片记录
        # ==========================================

        image_record = TransactionImage.objects.create(
            transaction=transaction_record,
            user=user,
            image=image,
        )

        return image_record

    @staticmethod
    @transaction.atomic
    def delete_transaction_image(
        user,
        transaction_id: int,
        image_id: int,
    ) -> None:
        """
        删除账单图片。

        规则：
        1. 账单必须属于当前用户；
        2. 图片必须属于该账单；
        3. 图片必须属于当前用户；
        4. 删除数据库记录；
        5. 同时删除磁盘上的图片文件。
        """

        # ==========================================
        # 查询账单
        # ==========================================

        try:
            transaction_record = Transaction.objects.select_for_update().get(
                id=transaction_id,
                user=user,
                status=Transaction.Status.NORMAL,
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        # ==========================================
        # 查询账单图片
        # ==========================================

        try:
            image_record = TransactionImage.objects.select_for_update().get(
                id=image_id,
                transaction=transaction_record,
                user=user,
            )

        except TransactionImage.DoesNotExist:
            raise BusinessException("账单图片不存在")

        # ==========================================
        # 删除磁盘文件
        # ==========================================

        if image_record.image:
            image_record.image.delete(save=False)

        # ==========================================
        # 删除数据库记录
        # ==========================================

        image_record.delete()

    @staticmethod
    def list_transaction_images(
        user,
        transaction_id: int,
    ):
        """
        获取指定账单的图片列表。

        规则：
        1. 账单必须属于当前用户；
        2. 账单必须处于正常状态；
        3. 只返回该账单自己的图片。
        """

        # ==========================================
        # 查询账单
        # ==========================================

        try:
            transaction_record = Transaction.objects.get(
                id=transaction_id,
                user=user,
                status=Transaction.Status.NORMAL,
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        # ==========================================
        # 查询图片
        # ==========================================

        images = TransactionImage.objects.filter(
            transaction=transaction_record,
            user=user,
        ).order_by("-created_at")

        return images
