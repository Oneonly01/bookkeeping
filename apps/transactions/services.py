from datetime import datetime, time
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from common.exceptions import BusinessException

from apps.accounts.models import Account
from apps.categories.models import Category

from .models import Transaction


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
        4. 支出扣减账户余额；
        5. 收入增加账户余额；
        6. 余额更新和账单创建必须在同一事务。
        """

        account_id = validated_data["account_id"]

        category_id = validated_data["category_id"]

        transaction_type = validated_data["transaction_type"]

        amount = validated_data["amount"]

        # 锁定账户。
        try:
            account = Account.objects.select_for_update().get(
                id=account_id,
                user=user,
                is_deleted=False,
                is_active=True,
            )

        except Account.DoesNotExist:
            raise BusinessException("账户不存在")

        # 查询分类。
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

        # 分类类型必须与账单类型一致。
        if category.category_type != transaction_type:
            raise BusinessException("分类类型与账单类型不一致")

        # 支出。
        if transaction_type == Transaction.TransactionType.EXPENSE:
            # 非信用卡账户余额不足时禁止支出。
            is_credit_card = account.account_type == Account.AccountType.CREDIT_CARD

            if not is_credit_card and account.balance < amount:
                raise BusinessException("账户余额不足")

            account.balance -= amount

        # 收入。
        else:
            account.balance += amount

        # 保存账户余额。
        account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 创建账单。
        transaction_record = Transaction.objects.create(
            user=user,
            account=account,
            category=category,
            transaction_type=(transaction_type),
            amount=amount,
            transaction_time=(validated_data["transaction_time"]),
            merchant=validated_data.get(
                "merchant",
                "",
            ),
            note=validated_data.get(
                "note",
                "",
            ),
        )

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
        2. 锁定涉及账户；
        3. 回滚原账单余额影响；
        4. 校验新账户、新分类；
        5. 应用新账单余额影响；
        6. 更新账单记录。
        """

        try:
            # 锁定原账单，防止并发修改。
            old_transaction = Transaction.objects.select_for_update().get(
                id=transaction_id,
                user=user,
                status=Transaction.Status.NORMAL,
            )

        except Transaction.DoesNotExist:
            raise BusinessException("账单不存在")

        # 修改后的账户 ID。
        new_account_id = validated_data.get(
            "account_id",
            old_transaction.account_id,
        )

        # 修改后的分类 ID。
        new_category_id = validated_data.get(
            "category_id",
            old_transaction.category_id,
        )

        # 修改后的账单类型。
        new_transaction_type = validated_data.get(
            "transaction_type",
            old_transaction.transaction_type,
        )

        # 修改后的金额。
        new_amount = validated_data.get(
            "amount",
            old_transaction.amount,
        )

        # 锁定旧账户和新账户。
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

        # ==============================
        # 回滚原账单
        # ==============================

        if old_transaction.transaction_type == Transaction.TransactionType.EXPENSE:
            # 原来是支出，
            # 当时扣了钱，现在先加回来。
            old_account.balance += old_transaction.amount

        else:
            # 原来是收入，
            # 当时加了钱，现在先扣回来。
            old_account.balance -= old_transaction.amount

        # ==============================
        # 校验新分类
        # ==============================

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

        if new_category.category_type != new_transaction_type:
            raise BusinessException("分类类型与账单类型不一致")

        # ==============================
        # 应用新账单
        # ==============================

        if new_transaction_type == Transaction.TransactionType.EXPENSE:
            is_credit_card = new_account.account_type == Account.AccountType.CREDIT_CARD

            if not is_credit_card and new_account.balance < new_amount:
                raise BusinessException("账户余额不足")

            new_account.balance -= new_amount

        else:
            new_account.balance += new_amount

        # 保存旧账户。
        old_account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 如果新旧账户不同，
        # 还需要保存新账户。
        if new_account.id != old_account.id:
            new_account.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

        # 如果是同一个账户，
        # 前面的 old_account 和 new_account
        # 实际上是同一个对象，
        # 再保存一次最终余额即可。
        else:
            old_account.save(
                update_fields=[
                    "balance",
                    "updated_at",
                ]
            )

        # ==============================
        # 更新账单
        # ==============================

        old_transaction.account = new_account

        old_transaction.category = new_category

        old_transaction.transaction_type = new_transaction_type

        old_transaction.amount = new_amount

        if "transaction_time" in validated_data:
            old_transaction.transaction_time = validated_data["transaction_time"]

        if "merchant" in validated_data:
            old_transaction.merchant = validated_data["merchant"]

        if "note" in validated_data:
            old_transaction.note = validated_data["note"]

        old_transaction.save()

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
