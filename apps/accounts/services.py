# 导入 Django 数据库事务工具。
from decimal import Decimal
from django.db import transaction

from common.exceptions.business import BusinessException

# 导入账户模型。
from .models import Account, AccountBalanceAdjustment, Transfer


class AccountService:
    """
    账户业务服务。

    负责处理账户相关业务逻辑。
    """

    @staticmethod
    @transaction.atomic
    def create_account(
        user,
        validated_data: dict,
    ) -> Account:
        """
        创建用户账户。

        业务规则：
        1. 初始余额 = 创建时余额；
        2. 如果设置为默认账户，
           则取消当前用户其他默认账户；
        3. 创建过程使用数据库事务保证一致性。

        :param user:
            当前登录用户。

        :param validated_data:
            Serializer 校验后的账户数据。

        :return:
            创建成功的 Account 对象。
        """

        # 获取是否设置为默认账户。
        is_default = validated_data.get(
            "is_default",
            False,
        )

        # 如果当前新账户需要设为默认账户。
        if is_default:

            # 将当前用户其他未删除账户
            # 的默认状态取消。
            Account.objects.filter(
                user=user,
                is_default=True,
                is_deleted=False,
            ).update(is_default=False)

        # 获取初始余额。
        initial_balance = validated_data.get(
            "initial_balance",
            0,
        )

        # 创建账户。
        account = Account.objects.create(
            # 绑定当前登录用户。
            user=user,
            # 账户名称。
            name=validated_data["name"],
            # 账户类型。
            account_type=validated_data["account_type"],
            # 初始余额。
            initial_balance=initial_balance,
            # 创建账户时，
            # 当前余额与初始余额保持一致。
            balance=initial_balance,
            # 账户图标。
            icon=validated_data.get(
                "icon",
                "",
            ),
            # 账户颜色。
            color=validated_data.get(
                "color",
                "",
            ),
            # 排序值。
            sort_order=validated_data.get(
                "sort_order",
                0,
            ),
            # 是否默认账户。
            is_default=is_default,
        )

        # 返回账户对象。
        return account

    @staticmethod
    def get_account(
        user,
        account_id: int,
    ) -> Account:
        """
        获取当前用户指定账户。

        业务规则：
        1. 只能查询当前登录用户自己的账户；
        2. 已逻辑删除的账户不能查询；
        3. 不允许通过 account_id 越权查看其他用户账户。

        :param user:
            当前登录用户。

        :param account_id:
            账户主键 ID。

        :return:
            Account 对象。
        """

        try:
            # 查询账户时同时限制：
            # 当前用户 + 未删除。
            account = Account.objects.get(
                id=account_id,
                user=user,
                is_deleted=False,
            )

        except Account.DoesNotExist:
            # 无论账户不存在，
            # 还是账户属于其他用户，
            # 都统一返回“账户不存在”。
            #
            # 不向客户端泄露其他用户账户是否存在。
            raise BusinessException("账户不存在")

        # 返回账户对象。
        return account

    @staticmethod
    @transaction.atomic
    def update_account(
        user,
        account_id: int,
        validated_data: dict,
    ) -> Account:
        """
        修改当前用户账户。

        业务规则：
        1. 只能修改当前用户自己的账户；
        2. 不允许修改已删除账户；
        3. 设置新默认账户时，
           自动取消其他账户的默认状态；
        4. 不允许通过本接口修改账户余额。
        """

        # 先通过统一方法获取当前用户账户。
        account = AccountService.get_account(
            user=user,
            account_id=account_id,
        )

        # 获取是否传入 is_default。
        new_is_default = validated_data.get("is_default")

        # 如果明确设置当前账户为默认账户。
        if new_is_default is True:

            # 取消当前用户其他账户的默认状态。
            Account.objects.filter(
                user=user,
                is_default=True,
                is_deleted=False,
            ).exclude(id=account.id).update(is_default=False)

        # 修改账户名称。
        if "name" in validated_data:
            account.name = validated_data["name"]

        # 修改账户类型。
        if "account_type" in validated_data:
            account.account_type = validated_data["account_type"]

        # 修改图标。
        if "icon" in validated_data:
            account.icon = validated_data["icon"]

        # 修改颜色。
        if "color" in validated_data:
            account.color = validated_data["color"]

        # 修改排序值。
        if "sort_order" in validated_data:
            account.sort_order = validated_data["sort_order"]

        # 修改默认状态。
        if "is_default" in validated_data:
            account.is_default = validated_data["is_default"]

        # 修改启用状态。
        if "is_active" in validated_data:
            account.is_active = validated_data["is_active"]

        # 保存修改。
        account.save()

        return account

    @staticmethod
    @transaction.atomic
    def delete_account(
        user,
        account_id: int,
    ) -> None:
        """
        逻辑删除当前用户账户。

        业务规则：
        1. 只能删除当前用户自己的账户；
        2. 账户余额必须为 0；
        3. 使用逻辑删除；
        4. 如果删除的是默认账户，
        自动设置其他账户为新的默认账户。
        """

        # 获取当前用户自己的账户。
        account = AccountService.get_account(
            user=user,
            account_id=account_id,
        )

        # 账户仍有余额时不允许删除。
        if account.balance != Decimal("0.00"):
            raise BusinessException("账户余额不为0，无法删除")

        # 记录当前账户是否为默认账户。
        was_default = account.is_default

        # 执行逻辑删除。
        account.is_deleted = True

        # 删除后账户同时设为停用。
        account.is_active = False

        # 删除账户不再作为默认账户。
        account.is_default = False

        # 保存状态。
        account.save(
            update_fields=[
                "is_deleted",
                "is_active",
                "is_default",
                "updated_at",
            ]
        )

        # 如果被删除的是默认账户，
        # 自动选择另一个未删除账户作为默认账户。
        if was_default:

            # 按排序值和 ID 查找第一个可用账户。
            new_default_account = (
                Account.objects.filter(
                    user=user,
                    is_deleted=False,
                    is_active=True,
                )
                .order_by(
                    "sort_order",
                    "id",
                )
                .first()
            )

            # 如果还存在其他账户，
            # 将其设置为默认账户。
            if new_default_account:
                new_default_account.is_default = True

                new_default_account.save(
                    update_fields=[
                        "is_default",
                        "updated_at",
                    ]
                )

    @staticmethod
    @transaction.atomic
    def adjust_balance(
        user,
        account_id: int,
        new_balance,
        note: str = "",
    ) -> Account:
        """
        校准账户余额。

        业务规则：
        1. 只能校准当前用户自己的账户；
        2. 已删除账户不能校准；
        3. 使用 select_for_update 锁定账户记录；
        4. 修改余额和创建校准记录必须处于同一事务；
        5. 不修改 initial_balance。

        :param user:
            当前登录用户。

        :param account_id:
            要校准的账户 ID。

        :param new_balance:
            用户输入的真实余额。

        :param note:
            余额校准说明。

        :return:
            校准后的 Account 对象。
        """

        try:
            # 使用 select_for_update()
            # 对当前账户记录加数据库行锁。
            #
            # 防止两个请求同时修改余额，
            # 造成余额覆盖或数据不一致。
            account = Account.objects.select_for_update().get(
                id=account_id,
                user=user,
                is_deleted=False,
            )

        except Account.DoesNotExist:
            # 不区分账户不存在还是属于其他用户，
            # 避免泄露其他用户账户信息。
            raise BusinessException("账户不存在")

        # 保存修改前余额。
        old_balance = account.balance

        # 如果新余额与当前余额完全一致，
        # 没有必要创建一条无意义的校准记录。
        if old_balance == new_balance:
            raise BusinessException("新余额与当前余额一致，无需校准")

        # 计算余额变化差额。
        difference = new_balance - old_balance

        # 修改当前余额。
        account.balance = new_balance

        # 只更新余额和更新时间。
        account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 创建余额校准历史记录。
        #
        # 因为整个方法处于 transaction.atomic 中，
        # 账户余额修改和校准记录要么一起成功，
        # 要么一起回滚。
        AccountBalanceAdjustment.objects.create(
            user=user,
            account=account,
            old_balance=old_balance,
            new_balance=new_balance,
            difference=difference,
            note=note,
        )

        # 返回修改后的账户。
        return account

    @staticmethod
    def get_balance_adjustments(
        user,
        account_id: int,
    ):
        """
        获取指定账户的余额校准历史。

        业务规则：
        1. 只能查询当前用户自己的账户；
        2. 已删除账户不能通过正常接口查询；
        3. 按创建时间倒序返回，
           最新校准记录排在最前面。

        :param user:
            当前登录用户。

        :param account_id:
            账户 ID。

        :return:
            QuerySet
        """

        # 先验证账户是否属于当前用户。
        #
        # get_account() 内部已经处理：
        # 当前用户 + 未删除。
        account = AccountService.get_account(
            user=user,
            account_id=account_id,
        )

        # 查询该账户的余额校准历史。
        queryset = AccountBalanceAdjustment.objects.filter(
            user=user,
            account=account,
        ).order_by(
            "-created_at",
            "-id",
        )

        return queryset

    @staticmethod
    @transaction.atomic
    def create_transfer(
        user,
        validated_data: dict,
    ) -> Transfer:
        """
        创建账户转账记录。

        业务规则：
        1. 两个账户必须属于当前用户；
        2. 两个账户都必须未删除并启用；
        3. 转出、转入账户不能相同；
        4. 同时锁定两个账户；
        5. 转出账户扣除：金额 + 手续费；
        6. 转入账户增加：转账金额；
        7. 所有余额修改和转账记录必须同一事务完成。
        """

        source_account_id = validated_data["source_account_id"]

        target_account_id = validated_data["target_account_id"]

        amount = validated_data["amount"]

        fee = validated_data.get(
            "fee",
            Decimal("0.00"),
        )

        # 防御性校验。
        if source_account_id == target_account_id:
            raise BusinessException("转出账户和转入账户不能相同")

        # 固定按照账户 ID 排序加锁。
        #
        # 避免不同并发请求采用不同锁顺序，
        # 从而降低数据库死锁概率。
        account_ids = sorted(
            [
                source_account_id,
                target_account_id,
            ]
        )

        accounts = (
            Account.objects.select_for_update()
            .filter(
                id__in=account_ids,
                user=user,
                is_deleted=False,
                is_active=True,
            )
            .order_by("id")
        )

        account_map = {account.id: account for account in accounts}

        # 两个账户必须都存在。
        if len(account_map) != 2:
            raise BusinessException("转出账户或转入账户不存在")

        source_account = account_map[source_account_id]

        target_account = account_map[target_account_id]

        # 实际从转出账户扣除：
        # 转账金额 + 手续费。
        total_deduction = amount + fee

        # 普通资金账户不允许余额不足。
        #
        # 信用卡账户后续如果需要支持负余额，
        # 可以单独设计信用额度逻辑。
        is_credit_card = source_account.account_type == Account.AccountType.CREDIT_CARD

        is_balance_insufficient = source_account.balance < total_deduction

        if not is_credit_card and is_balance_insufficient:
            raise BusinessException("转出账户余额不足")

        # 转出账户扣款。
        source_account.balance -= total_deduction

        # 转入账户增加转账金额。
        target_account.balance += amount

        source_account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        target_account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 创建转账记录。
        transfer = Transfer.objects.create(
            user=user,
            source_account=source_account,
            target_account=target_account,
            amount=amount,
            fee=fee,
            transfer_time=validated_data["transfer_time"],
            note=validated_data.get(
                "note",
                "",
            ),
        )

        return transfer

    @staticmethod
    def get_transfer_list(
        user,
    ):
        """
        获取当前用户的转账记录列表。

        业务规则：
        1. 只查询当前登录用户的数据；
        2. 只查询正常状态的转账记录；
        3. 按转账时间倒序排列；
        4. 使用 select_related 减少账户关联查询次数。

        :param user:
            当前登录用户。

        :return:
            QuerySet
        """

        # 查询当前用户自己的转账记录。
        queryset = (
            Transfer.objects.filter(
                user=user,
                status=Transfer.Status.NORMAL,
            )
            .select_related(
                "source_account",
                "target_account",
            )
            .order_by(
                "-transfer_time",
                "-id",
            )
        )

        # 返回查询结果。
        return queryset

    @staticmethod
    def get_transfer_detail(
        user,
        transfer_id: int,
    ) -> Transfer:
        """
        获取指定转账记录详情。

        业务规则：
        1. 只能查询当前登录用户自己的转账记录；
        2. 默认只查询正常状态的转账记录；
        3. 不允许通过 transfer_id 越权查看其他用户数据；
        4. 使用 select_related 一次性加载转出账户和转入账户。

        :param user:
            当前登录用户。

        :param transfer_id:
            转账记录 ID。

        :return:
            Transfer 对象。
        """

        try:
            # 查询当前用户自己的转账记录。
            transfer = Transfer.objects.select_related(
                "source_account",
                "target_account",
            ).get(
                id=transfer_id,
                user=user,
                status=Transfer.Status.NORMAL,
            )

        except Transfer.DoesNotExist:
            # 无论记录不存在，
            # 还是记录属于其他用户，
            # 都统一返回“转账记录不存在”。
            raise BusinessException("转账记录不存在")

        # 返回转账记录。
        return transfer

    @staticmethod
    @transaction.atomic
    def delete_transfer(
        user,
        transfer_id: int,
    ) -> None:
        """
        撤销转账记录。

        注意：
        这里不是物理删除数据库记录，
        而是撤销该笔转账产生的余额变化，
        并将转账记录状态修改为 deleted。

        业务规则：
        1. 只能撤销当前用户自己的转账记录；
        2. 已撤销的转账不能重复撤销；
        3. 必须锁定转账记录；
        4. 必须同时锁定转出和转入账户；
        5. 转出账户恢复 amount + fee；
        6. 转入账户扣回 amount；
        7. 所有操作必须处于同一个数据库事务。
        """

        try:
            # 锁定转账记录。
            #
            # 这样两个并发请求同时撤销同一笔转账时，
            # 只能有一个请求真正执行余额恢复。
            transfer = Transfer.objects.select_for_update().get(
                id=transfer_id,
                user=user,
            )

        except Transfer.DoesNotExist:
            raise BusinessException("转账记录不存在")

        # 已经撤销过的转账，
        # 不允许再次执行。
        if transfer.status == Transfer.Status.DELETED:
            raise BusinessException("该转账记录已撤销")

        # 获取两个账户 ID。
        source_account_id = transfer.source_account_id

        target_account_id = transfer.target_account_id

        # 固定按照账户 ID 排序。
        #
        # 多账户并发操作统一锁顺序，
        # 可以降低数据库死锁风险。
        account_ids = sorted(
            [
                source_account_id,
                target_account_id,
            ]
        )

        # 锁定两个账户。
        #
        # 这里不限制 is_active 和 is_deleted。
        #
        # 原因：
        # 某个历史账户即使后来被停用或逻辑删除，
        # 历史转账依然可能需要撤销。
        accounts = (
            Account.objects.select_for_update()
            .filter(
                id__in=account_ids,
                user=user,
            )
            .order_by("id")
        )

        # 转换成字典。
        account_map = {account.id: account for account in accounts}

        # 理论上 Transfer 使用 PROTECT，
        # 两个账户应该始终存在。
        #
        # 这里继续做防御性校验。
        if len(account_map) != 2:
            raise BusinessException("转账关联账户不存在")

        # 获取原转出账户。
        source_account = account_map[source_account_id]

        # 获取原转入账户。
        target_account = account_map[target_account_id]

        # ==============================
        # 恢复转出账户
        # ==============================

        # 原转出时扣除了：
        #
        # amount + fee
        #
        # 所以撤销时全部加回来。
        source_account.balance += transfer.amount + transfer.fee

        # ==============================
        # 恢复转入账户
        # ==============================

        # 原转入账户增加了 amount，
        # 所以撤销时扣回来。
        target_account.balance -= transfer.amount

        # 保存转出账户。
        source_account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 保存转入账户。
        target_account.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        # 转账记录执行逻辑删除。
        transfer.status = Transfer.Status.DELETED

        # 保存状态。
        transfer.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )
