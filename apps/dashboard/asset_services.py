from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Account
from common.exceptions import BusinessException
from common.utils.comparison import calculate_amount_comparison

from .models import UserAssetMonthlySnapshot


class AssetSnapshotService:
    """
    月末资产快照及账户余额环比服务。

    与首页保持同一口径：只统计当前用户未删除、已启用的账户。
    在应用内每次账户变化前结转，避免定时任务停机造成月末数据丢失。
    """

    @staticmethod
    def _next_month(month):
        """获取下个月的第一天，处理12月跨年。"""
        if month.month == 12:
            return date(month.year + 1, 1, 1)
        return date(month.year, month.month + 1, 1)

    @staticmethod
    def _get_asset_totals(user):
        """
        在用户锁内读取当前资产。

        使用账户行锁执行当前读，避免外层事务已有旧读视图时，
        在MySQL默认隔离级别下读取到过期余额。
        所有相关业务入口统一先锁用户，再锁账户。
        """
        accounts = list(
            Account.objects.select_for_update().filter(
                user=user, is_deleted=False, is_active=True,
            ).order_by("id")
        )
        assets = Decimal("0.00")
        liabilities = Decimal("0.00")
        for account in accounts:
            if account.balance >= 0:
                assets += account.balance
            else:
                liabilities += abs(account.balance)
        return {
            "total_assets": assets,
            "total_liabilities": liabilities,
            "net_assets": assets - liabilities,
            "account_count": len(accounts),
        }

    @staticmethod
    @transaction.atomic
    def prepare_user(user, today=None):
        """
        在修改余额或读取首页之前结转已跟踪月份。

        首次调用只建立当月跟踪起点，不补造上线前的月末余额。
        若跨过多个无操作月份，余额没有变化，可逐月结转同一余额。
        返回本次新结转的月份数量；重复调用不会覆盖已结转快照。
        """
        today = today or timezone.localdate()
        current_month = today.replace(day=1)

        # 用户行始终存在，可同时串行化首次建档和跨月结转。
        get_user_model().objects.select_for_update().get(pk=user.pk)
        latest = (
            UserAssetMonthlySnapshot.objects.select_for_update()
            .filter(user=user).order_by("-month").first()
        )

        if latest is not None and latest.month > current_month:
            raise BusinessException("资产快照月份晚于当前日期，请检查服务器时间")

        if latest is not None and latest.month == current_month:
            return 0

        # 此时业务尚未修改余额，读取的就是上次操作后的最终状态。
        totals = AssetSnapshotService._get_asset_totals(user)
        if latest is None:
            UserAssetMonthlySnapshot.objects.create(
                user=user, month=current_month, **totals,
            )
            return 0

        closed_count = 0
        cursor = latest.month
        closed_at = timezone.now()

        while cursor < current_month:
            if cursor == latest.month:
                # 最后一个未结转月份，用变更前余额确认月末快照。
                # 已结转的历史记录保持不变。
                if not latest.is_closed:
                    for field, value in totals.items():
                        setattr(latest, field, value)
                    latest.is_closed = True
                    latest.closed_at = closed_at
                    latest.save(update_fields=[
                        *totals, "is_closed", "closed_at", "updated_at",
                    ])
                    closed_count += 1
            else:
                # 中间没有应用内账户操作，余额可原样结转。
                UserAssetMonthlySnapshot.objects.create(
                    user=user, month=cursor, is_closed=True,
                    closed_at=closed_at, **totals,
                )
                closed_count += 1
            cursor = AssetSnapshotService._next_month(cursor)

        # 新月份先建立未结转记录，金额不用于历史月末对比。
        UserAssetMonthlySnapshot.objects.create(
            user=user, month=current_month, **totals,
        )
        return closed_count

    @staticmethod
    @transaction.atomic
    def get_comparison(user, month=None, today=None):
        """
        返回账户净余额相对上月末的变化。

        当前月使用实时余额；历史月仅使用已结转快照。
        没有历史快照或查询未来月份时不使用当前余额冒充历史数据。
        """
        today = today or timezone.localdate()
        AssetSnapshotService.prepare_user(user, today=today)
        current_month = today.replace(day=1)
        target_month = (
            datetime.strptime(month, "%Y-%m").date().replace(day=1)
            if month else current_month
        )
        # 0001年1月没有可表示的上一月，按缺失历史处理。
        previous_month = (
            (target_month - timedelta(days=1)).replace(day=1)
            if target_month > date.min else None
        )

        current_assets = None
        if target_month == current_month:
            current_assets = AssetSnapshotService._get_asset_totals(user)["net_assets"]
        elif target_month < current_month:
            snapshot = UserAssetMonthlySnapshot.objects.select_for_update().filter(
                user=user, month=target_month, is_closed=True,
            ).first()
            if snapshot is not None:
                current_assets = snapshot.net_assets

        previous = None
        if previous_month is not None and target_month <= current_month:
            previous = UserAssetMonthlySnapshot.objects.select_for_update().filter(
                user=user, month=previous_month, is_closed=True,
            ).first()

        previous_assets = previous.net_assets if previous is not None else None
        comparison = calculate_amount_comparison(current_assets, previous_assets)

        # 与首页已有金额格式一致，统一返回两位小数字符串。
        def money(value):
            return f"{value:.2f}" if value is not None else None

        return {
            "current_month": target_month.strftime("%Y-%m"),
            "previous_month": (
                previous_month.strftime("%Y-%m") if previous_month else None
            ),
            "previous_net_assets": money(previous_assets),
            "current_net_assets": money(current_assets),
            "change_amount": money(comparison["change_amount"]),
            "change_rate": money(comparison["change_rate"]),
            "trend": comparison["trend"],
            "has_previous_snapshot": previous is not None,
            "has_current_data": current_assets is not None,
        }
