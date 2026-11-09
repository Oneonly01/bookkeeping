from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.accounts.services import AccountService
from apps.categories.models import Category
from apps.dashboard.asset_services import AssetSnapshotService
from apps.dashboard.models import UserAssetMonthlySnapshot
from apps.transactions.models import Transaction
from apps.transactions.services import TransactionService
from common.exceptions import BusinessException
from common.utils.comparison import calculate_amount_comparison


class AmountComparisonTests(SimpleTestCase):
    """校验收支和资产共用的环比规则，尤其是零、负数和缺失数据。"""

    def test_change_direction_and_percentage(self):
        cases = (
            ("1500", "1000", "up", "50.00"),
            ("800", "1000", "down", "-20.00"),
            ("0", "1000", "down", "-100.00"),
            ("1000", "1000", "unchanged", "0.00"),
            ("500", "0", "new", None),
            ("0", "0", "unchanged", None),
            ("-500", "0", "down", None),
            ("500", "-1000", "up", None),
            ("-1500", "-1000", "down", None),
        )
        for current, previous, trend, rate in cases:
            with self.subTest(current=current, previous=previous):
                result = calculate_amount_comparison(Decimal(current), Decimal(previous))
                self.assertEqual(result["trend"], trend)
                self.assertEqual(result["change_amount"], Decimal(current) - Decimal(previous))
                self.assertEqual(result["change_rate"], Decimal(rate) if rate else None)

    def test_missing_history_is_not_zero(self):
        result = calculate_amount_comparison(Decimal("500"), None)
        self.assertEqual(result, {"change_amount": None, "change_rate": None, "trend": "unknown"})

    def test_tiny_decrease_does_not_return_negative_zero(self):
        result = calculate_amount_comparison(Decimal("999999.99"), Decimal("1000000"))
        self.assertEqual(result["trend"], "down")
        self.assertEqual(str(result["change_rate"]), "0.00")


class AssetSnapshotTests(APITestCase):
    """使用独立数据库验证跨月前结转、事务回滚及接口返回。"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="asset-owner")
        self.other = get_user_model().objects.create_user(username="asset-other")
        self.client.force_authenticate(user=self.user)

    def on_day(self, day):
        return patch("apps.dashboard.asset_services.timezone.localdate", return_value=day)

    def create_account(self, amount="1000.00", account_type="bank", name="储蓄卡"):
        return AccountService.create_account(self.user, {
            "name": name, "account_type": account_type,
            "initial_balance": Decimal(amount),
        })

    def test_first_use_has_no_fake_previous_balance(self):
        with self.on_day(date(2026, 10, 15)):
            self.create_account()
            result = AssetSnapshotService.get_comparison(self.user)
        self.assertEqual(result["current_net_assets"], "1000.00")
        self.assertIsNone(result["previous_net_assets"])
        self.assertIsNone(result["change_rate"])
        self.assertEqual(result["trend"], "unknown")
        self.assertFalse(result["has_previous_snapshot"])
        self.assertEqual(UserAssetMonthlySnapshot.objects.count(), 1)
        self.assertFalse(UserAssetMonthlySnapshot.objects.get().is_closed)

    def test_first_new_month_adjustment_closes_previous_balance(self):
        with self.on_day(date(2026, 10, 31)):
            account = self.create_account("1500")
            self.create_account("1000", "credit_card", "信用卡")
        with self.on_day(date(2026, 11, 2)):
            AccountService.adjust_balance(self.user, account.pk, Decimal("2000"))
            result = AssetSnapshotService.get_comparison(self.user)
        self.assertEqual(result["previous_net_assets"], "2500.00")
        self.assertEqual(result["current_net_assets"], "3000.00")
        self.assertEqual(result["change_amount"], "500.00")
        self.assertEqual(result["change_rate"], "20.00")
        self.assertEqual(result["trend"], "up")

    def test_credit_debt_is_subtracted(self):
        with self.on_day(date(2026, 10, 31)):
            self.create_account("1500")
            self.create_account("-1000", "credit_card", "欠款")
        with self.on_day(date(2026, 11, 1)):
            result = AssetSnapshotService.get_comparison(self.user)
        snapshot = UserAssetMonthlySnapshot.objects.get(month=date(2026, 10, 1))
        self.assertEqual(snapshot.total_assets, Decimal("1500"))
        self.assertEqual(snapshot.total_liabilities, Decimal("1000"))
        self.assertEqual(result["previous_net_assets"], "500.00")

    def test_idle_months_are_carried_forward_and_closing_is_idempotent(self):
        with self.on_day(date(2026, 10, 15)):
            self.create_account()
        with self.on_day(date(2027, 1, 3)):
            self.assertEqual(AssetSnapshotService.prepare_user(self.user), 3)
            self.assertEqual(AssetSnapshotService.prepare_user(self.user), 0)
            result = AssetSnapshotService.get_comparison(self.user)
        self.assertEqual(result["previous_month"], "2026-12")
        self.assertEqual(result["change_rate"], "0.00")
        self.assertEqual(UserAssetMonthlySnapshot.objects.filter(is_closed=True).count(), 3)

    def test_closed_history_does_not_change_after_balance_adjustment(self):
        with self.on_day(date(2026, 10, 31)):
            account = self.create_account()
        with self.on_day(date(2026, 11, 1)):
            AssetSnapshotService.get_comparison(self.user)
            AccountService.adjust_balance(self.user, account.pk, Decimal("2000"))
            result = AssetSnapshotService.get_comparison(self.user, month="2026-10")
        self.assertEqual(result["current_net_assets"], "1000.00")
        self.assertIsNone(result["previous_net_assets"])

    def test_history_before_tracking_and_future_month_are_unknown(self):
        with self.on_day(date(2026, 11, 3)):
            self.create_account()
            for month in ("2026-09", "2026-12"):
                with self.subTest(month=month):
                    result = AssetSnapshotService.get_comparison(self.user, month=month)
                    self.assertFalse(result["has_current_data"])
                    self.assertIsNone(result["current_net_assets"])
                    self.assertEqual(result["trend"], "unknown")

    def test_other_user_snapshot_is_not_used(self):
        with self.on_day(date(2026, 10, 31)):
            self.create_account()
        with self.on_day(date(2026, 11, 1)):
            result = AssetSnapshotService.get_comparison(self.other)
        self.assertFalse(result["has_previous_snapshot"])
        self.assertEqual(result["current_net_assets"], "0.00")

    def test_failed_transaction_rolls_back_snapshot_closing(self):
        with self.on_day(date(2026, 10, 31)):
            account = self.create_account()
        with self.on_day(date(2026, 11, 1)):
            with self.assertRaises(BusinessException):
                # 分类不存在，快照结转与失败业务应一起回滚。
                TransactionService.create_transaction(self.user, {
                    "account_id": account.pk, "category_id": 99999,
                    "transaction_type": "expense", "amount": Decimal("10"),
                })
        self.assertFalse(UserAssetMonthlySnapshot.objects.get().is_closed)
        self.assertEqual(UserAssetMonthlySnapshot.objects.count(), 1)

    def test_account_creation_and_activation_close_before_change(self):
        with self.on_day(date(2026, 10, 31)):
            account = self.create_account()
        with self.on_day(date(2026, 11, 1)):
            AccountService.update_account(self.user, account.pk, {"is_active": False})
            result = AssetSnapshotService.get_comparison(self.user)
        self.assertEqual(result["previous_net_assets"], "1000.00")
        self.assertEqual(result["current_net_assets"], "0.00")
        self.assertEqual(result["change_rate"], "-100.00")

    def test_transfer_fees_and_reversal_have_correct_month_end_balance(self):
        with self.on_day(date(2026, 10, 31)):
            source = self.create_account()
            target = self.create_account("0", "cash", "现金")
        with self.on_day(date(2026, 11, 1)):
            transfer = AccountService.create_transfer(self.user, {
                "source_account_id": source.pk, "target_account_id": target.pk,
                "amount": Decimal("200"), "fee": Decimal("10"),
                "transfer_time": timezone.now(),
            })
            result = AssetSnapshotService.get_comparison(self.user)
        self.assertEqual(result["change_amount"], "-10.00")
        self.assertEqual(result["change_rate"], "-1.00")
        with self.on_day(date(2026, 12, 1)):
            AccountService.delete_transfer(self.user, transfer.pk)
            result = AssetSnapshotService.get_comparison(self.user)
        self.assertEqual(result["previous_net_assets"], "990.00")
        self.assertEqual(result["current_net_assets"], "1000.00")

    def test_command_initializes_and_repeats_without_fabricating_history(self):
        with self.on_day(date(2026, 11, 3)):
            output = StringIO()
            call_command("close_asset_snapshots", user_id=self.user.pk, stdout=output)
            call_command("close_asset_snapshots", user_id=self.user.pk, stdout=output)
        self.assertEqual(UserAssetMonthlySnapshot.objects.count(), 1)
        self.assertFalse(UserAssetMonthlySnapshot.objects.get().is_closed)

    def test_dashboard_and_monthly_endpoint_expose_consistent_assets(self):
        with self.on_day(date(2026, 10, 31)):
            self.create_account("1500")
        with self.on_day(date(2026, 11, 3)):
            dashboard = self.client.get("/api/v1/dashboard/summary/")
            monthly = self.client.get("/api/v1/transactions/monthly-statistics/?month=2026-11")
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.assertEqual(monthly.status_code, 200, monthly.data)
        self.assertEqual(dashboard.data["data"]["assets"]["net_assets"], "1500.00")
        self.assertEqual(dashboard.data["data"]["asset_comparison"], monthly.data["data"]["asset_comparison"])
        self.assertEqual(len(dashboard.data["data"]["account_groups"]), 4)


    def test_selected_history_month_still_exposes_current_balance_without_snapshot(self):
        with self.on_day(date(2026, 11, 3)):
            self.create_account("1500")
            response = self.client.get("/api/v1/transactions/monthly-statistics/?month=2026-10")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["current_month"], "2026-10")
        asset = data["asset_comparison"]
        self.assertEqual(asset["current_month"], "2026-11")
        self.assertEqual(asset["previous_month"], "2026-10")
        self.assertEqual(asset["current_net_assets"], "1500.00")
        self.assertTrue(asset["has_current_data"])
        self.assertFalse(asset["has_previous_snapshot"])
        self.assertIsNone(asset["change_rate"])

    def test_changing_income_month_does_not_change_balance_or_its_baseline(self):
        with self.on_day(date(2026, 10, 31)):
            account = self.create_account("1000")
        with self.on_day(date(2026, 11, 3)):
            AccountService.adjust_balance(self.user, account.pk, Decimal("1500"))
            expected = AssetSnapshotService.get_comparison(self.user)
            for selected_month in ("2026-09", "2026-10", "2026-11", "2026-12"):
                with self.subTest(month=selected_month):
                    response = self.client.get(
                        "/api/v1/transactions/monthly-statistics/", {"month": selected_month}
                    )
                    self.assertEqual(response.status_code, 200, response.data)
                    self.assertEqual(response.data["data"]["current_month"], selected_month)
                    self.assertEqual(response.data["data"]["asset_comparison"], expected)
        self.assertEqual(expected["current_net_assets"], "1500.00")
        self.assertEqual(expected["previous_net_assets"], "1000.00")
        self.assertEqual(expected["change_rate"], "50.00")


class MonthlyComparisonApiTests(APITestCase):
    """验证已有返回字段兼容、新字段格式及自然月跨年。"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="monthly-owner")
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(user=self.user, name="现金", account_type="cash")

    def add_bill(self, amount, kind, year, month, status="normal"):
        Transaction.objects.create(
            user=self.user, account=self.account, transaction_type=kind,
            amount=Decimal(amount), status=status,
            transaction_time=timezone.make_aware(datetime(year, month, 10, 12)),
        )

    def test_monthly_income_and_expense_percentage_with_signed_changes(self):
        self.add_bill("4000", "income", 2026, 10)
        self.add_bill("1500", "expense", 2026, 10)
        self.add_bill("5180", "income", 2026, 11)
        self.add_bill("1100", "expense", 2026, 11)
        self.add_bill("999", "income", 2026, 11, "deleted")
        response = self.client.get("/api/v1/transactions/monthly-statistics/?month=2026-11")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["current"]["balance"], "4080.00")
        self.assertEqual(data["comparison"], {
            "income_rate": "29.50", "expense_rate": "-26.67",
            "income_change_amount": "1180.00", "expense_change_amount": "-400.00",
            "income_trend": "up", "expense_trend": "down",
        })

    def test_zero_previous_amount_uses_new_instead_of_fake_percentage(self):
        self.add_bill("500", "income", 2026, 11)
        response = self.client.get("/api/v1/transactions/monthly-statistics/?month=2026-11")
        comparison = response.data["data"]["comparison"]
        self.assertIsNone(comparison["income_rate"])
        self.assertEqual(comparison["income_trend"], "new")
        self.assertEqual(comparison["expense_trend"], "unchanged")

    def test_january_compares_with_previous_december(self):
        self.add_bill("1000", "income", 2026, 12)
        self.add_bill("800", "income", 2027, 1)
        response = self.client.get("/api/v1/transactions/monthly-statistics/?month=2027-01")
        data = response.data["data"]
        self.assertEqual(data["previous_month"], "2026-12")
        self.assertEqual(data["comparison"]["income_rate"], "-20.00")

    def test_anonymous_requests_are_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/transactions/monthly-statistics/")
        self.assertEqual(response.status_code, 401)
