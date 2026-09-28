from django.db import transaction

from common.exceptions.business import BusinessException

from .models import SavingsGoal, SavingsRecord


class SavingsGoalService:
    """
    储蓄目标业务服务类。
    """

    @staticmethod
    @transaction.atomic
    def create_goal(
        user,
        validated_data: dict,
    ):
        """
        创建储蓄目标。

        创建时：

        1. 自动绑定当前登录用户；
        2. 当前已存金额固定为 0；
        3. 状态固定为进行中。
        """

        # ======================================
        # 创建储蓄目标
        # ======================================

        goal = SavingsGoal.objects.create(
            # 当前登录用户。
            user=user,
            # 目标名称。
            name=validated_data["name"],
            # 目标金额。
            target_amount=validated_data["target_amount"],
            # 创建时已存金额固定为 0。
            current_amount=0,
            # 截止日期。
            deadline=validated_data.get("deadline"),
            # 图标。
            icon=validated_data.get(
                "icon",
                "",
            ),
            # 颜色。
            color=validated_data.get(
                "color",
                "",
            ),
            # 备注。
            note=validated_data.get(
                "note",
                "",
            ),
            # 创建后默认进行中。
            status=(SavingsGoal.Status.ACTIVE),
        )

        return goal

    @staticmethod
    def get_goal_list(
        user,
    ):
        """
        获取当前用户储蓄目标列表。

        查询规则：

        1. 只查询当前登录用户；
        2. 不返回已逻辑删除目标。
        """

        return SavingsGoal.objects.filter(
            user=user,
            is_deleted=False,
        ).order_by(
            "-created_at",
            "-id",
        )

    @staticmethod
    def get_goal_detail(
        user,
        goal_id: int,
    ):
        """
        获取储蓄目标详情。

        只能查询：

        1. 当前登录用户自己的目标；
        2. 未逻辑删除的目标。
        """

        goal = SavingsGoal.objects.filter(
            id=goal_id,
            user=user,
            is_deleted=False,
        ).first()

        if goal is None:
            raise BusinessException("储蓄目标不存在")

        return goal

    @staticmethod
    @transaction.atomic
    def update_goal(
        user,
        goal_id: int,
        validated_data: dict,
    ):
        """
        修改储蓄目标。

        修改时对当前储蓄目标加行锁，
        避免后续存钱、取钱操作与修改目标并发执行时
        产生数据不一致问题。
        """

        # ======================================
        # 查询并锁定目标
        # ======================================

        goal = (
            SavingsGoal.objects.select_for_update()
            .filter(
                id=goal_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if goal is None:
            raise BusinessException("储蓄目标不存在")

        # ======================================
        # 修改目标名称
        # ======================================

        if "name" in validated_data:
            goal.name = validated_data["name"]

        # ======================================
        # 修改目标金额
        # ======================================

        if "target_amount" in validated_data:
            new_target_amount = validated_data["target_amount"]

            # 已存金额可以大于目标金额，
            # 例如用户已经超额储蓄。
            #
            # 所以这里不限制：
            # target_amount >= current_amount
            #
            # 后续由系统根据当前金额自动判断
            # 是否达到目标。
            goal.target_amount = new_target_amount

        # ======================================
        # 修改截止日期
        # ======================================

        if "deadline" in validated_data:
            goal.deadline = validated_data["deadline"]

        # ======================================
        # 修改图标
        # ======================================

        if "icon" in validated_data:
            goal.icon = validated_data["icon"]

        # ======================================
        # 修改颜色
        # ======================================

        if "color" in validated_data:
            goal.color = validated_data["color"]

        # ======================================
        # 修改备注
        # ======================================

        if "note" in validated_data:
            goal.note = validated_data["note"]

        # ======================================
        # 保存
        # ======================================

        goal.save(
            update_fields=[
                "name",
                "target_amount",
                "deadline",
                "icon",
                "color",
                "note",
                "updated_at",
            ]
        )

        return goal

    @staticmethod
    @transaction.atomic
    def delete_goal(
        user,
        goal_id: int,
    ):
        """
        删除储蓄目标。

        使用逻辑删除，
        不直接从数据库物理删除数据。

        后续储蓄记录仍然可以保留，
        方便审计和历史数据追踪。
        """

        # ======================================
        # 查询并锁定目标
        # ======================================

        goal = (
            SavingsGoal.objects.select_for_update()
            .filter(
                id=goal_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if goal is None:
            raise BusinessException("储蓄目标不存在")

        # ======================================
        # 逻辑删除
        # ======================================

        goal.is_deleted = True

        goal.save(
            update_fields=[
                "is_deleted",
                "updated_at",
            ]
        )

        return goal

    @staticmethod
    @transaction.atomic
    def deposit(
        user,
        goal_id: int,
        validated_data: dict,
    ):
        """
        向储蓄目标存入资金。

        业务规则：

        1. 只能操作当前用户自己的储蓄目标；
        2. 已删除目标不能操作；
        3. 已暂停目标不能存入；
        4. 金额必须大于 0；
        5. 使用 select_for_update 锁定目标；
        6. 修改 current_amount；
        7. 同时生成一条存入流水；
        8. 达到目标金额后自动标记为 completed。
        """

        # ======================================
        # 锁定储蓄目标
        # ======================================

        goal = (
            SavingsGoal.objects.select_for_update()
            .filter(
                id=goal_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if goal is None:
            raise BusinessException("储蓄目标不存在")

        # ======================================
        # 暂停状态不能继续存入
        # ======================================

        if goal.status == SavingsGoal.Status.PAUSED:
            raise BusinessException("储蓄目标已暂停，无法存入资金")

        # ======================================
        # 已完成目标不能继续存入
        # ======================================

        if goal.status == SavingsGoal.Status.COMPLETED:
            raise BusinessException("储蓄目标已完成，无法继续存入资金")

        amount = validated_data["amount"]

        note = validated_data.get(
            "note",
            "",
        )

        # ======================================
        # 记录变动前金额
        # ======================================

        before_amount = goal.current_amount

        # ======================================
        # 计算变动后金额
        # ======================================

        after_amount = before_amount + amount

        # ======================================
        # 更新储蓄金额
        # ======================================

        goal.current_amount = after_amount

        # ======================================
        # 自动完成目标
        # ======================================

        if after_amount >= goal.target_amount:
            goal.status = SavingsGoal.Status.COMPLETED

        # ======================================
        # 保存目标
        # ======================================

        goal.save(
            update_fields=[
                "current_amount",
                "status",
                "updated_at",
            ]
        )

        # ======================================
        # 创建资金流水
        # ======================================

        record = SavingsRecord.objects.create(
            user=user,
            goal=goal,
            record_type=(SavingsRecord.RecordType.DEPOSIT),
            amount=amount,
            before_amount=(before_amount),
            after_amount=(after_amount),
            note=note,
        )

        return goal, record

    @staticmethod
    @transaction.atomic
    def withdraw(
        user,
        goal_id: int,
        validated_data: dict,
    ):
        """
        从储蓄目标取出资金。

        业务规则：

        1. 只能操作当前用户自己的目标；
        2. 已删除目标不能操作；
        3. 暂停目标不能取出；
        4. 取出金额不能超过当前已存金额；
        5. 使用 select_for_update 保证并发安全；
        6. 当前金额和流水必须同一事务更新。
        """

        # ======================================
        # 锁定储蓄目标
        # ======================================

        goal = (
            SavingsGoal.objects.select_for_update()
            .filter(
                id=goal_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if goal is None:
            raise BusinessException("储蓄目标不存在")

        # ======================================
        # 暂停状态不能操作
        # ======================================

        if goal.status == SavingsGoal.Status.PAUSED:
            raise BusinessException("储蓄目标已暂停，无法取出资金")

        amount = validated_data["amount"]

        note = validated_data.get(
            "note",
            "",
        )

        # ======================================
        # 余额检查
        # ======================================

        if amount > goal.current_amount:
            raise BusinessException("取出金额不能超过当前已存金额")

        # ======================================
        # 变动前金额
        # ======================================

        before_amount = goal.current_amount

        # ======================================
        # 计算变动后金额
        # ======================================

        after_amount = before_amount - amount

        # ======================================
        # 更新储蓄金额
        # ======================================

        goal.current_amount = after_amount

        # ======================================
        # 如果原来已经完成，
        # 但取出后低于目标金额，
        # 自动恢复为进行中。
        # ======================================

        if (
            goal.status == SavingsGoal.Status.COMPLETED
            and after_amount < goal.target_amount
        ):
            goal.status = SavingsGoal.Status.ACTIVE

        # ======================================
        # 保存
        # ======================================

        goal.save(
            update_fields=[
                "current_amount",
                "status",
                "updated_at",
            ]
        )

        # ======================================
        # 创建取出流水
        # ======================================

        record = SavingsRecord.objects.create(
            user=user,
            goal=goal,
            record_type=(SavingsRecord.RecordType.WITHDRAW),
            amount=amount,
            before_amount=(before_amount),
            after_amount=(after_amount),
            note=note,
        )

        return goal, record

    @staticmethod
    def get_records(
        user,
        goal_id: int,
    ):
        """
        查询储蓄目标资金流水。

        只能查询当前用户自己的目标及流水。
        """

        # ======================================
        # 先验证目标是否存在
        # ======================================

        goal = SavingsGoal.objects.filter(
            id=goal_id,
            user=user,
            is_deleted=False,
        ).first()

        if goal is None:
            raise BusinessException("储蓄目标不存在")

        # ======================================
        # 查询资金流水
        # ======================================

        return SavingsRecord.objects.filter(
            user=user,
            goal=goal,
        ).order_by(
            "-created_at",
            "-id",
        )
