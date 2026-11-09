from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Account, Transfer
from apps.accounts.serializers import TransferSerializer
from apps.accounts.services import AccountService


class TransferBalanceSnapshotTests(APITestCase):
    """转账历史余额必须固定保存，不能随当前账户余额变化。"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="transfer-balance-owner")
        self.other = get_user_model().objects.create_user(username="transfer-balance-other")
        self.source = Account.objects.create(
            user=self.user, name="转出", account_type="bank",
            initial_balance="1000", balance="1000",
        )
        self.target = Account.objects.create(
            user=self.user, name="转入", account_type="cash",
            initial_balance="200", balance="200",
        )
        self.client.force_authenticate(user=self.user)

    def body(self, **changes):
        return {
            "source_account_id": self.source.pk,
            "target_account_id": self.target.pk,
            "amount": "100.00", "fee": "2.00",
            "transfer_time": timezone.now().isoformat(),
            **changes,
        }

    def create(self, **changes):
        response = self.client.post("/api/v1/accounts/transfers/", self.body(**changes), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["data"]

    def assert_snapshot(self, data, source_before="1000.00", source_after="898.00", target_before="200.00", target_after="300.00"):
        self.assertEqual(data["source_balance_before"], source_before)
        self.assertEqual(data["source_balance_after"], source_after)
        self.assertEqual(data["target_balance_before"], target_before)
        self.assertEqual(data["target_balance_after"], target_after)
        self.assertTrue(data["has_balance_snapshot"])

    def test_creation_saves_four_balances_and_accounts_with_fee(self):
        data = self.create()
        self.assert_snapshot(data)
        transfer = Transfer.objects.get(pk=data["id"])
        self.assertEqual(transfer.source_balance_after, Decimal("898"))
        self.assertEqual(transfer.target_balance_after, Decimal("300"))
        self.source.refresh_from_db()
        self.target.refresh_from_db()
        self.assertEqual(self.source.balance, Decimal("898"))
        self.assertEqual(self.target.balance, Decimal("300"))

    def test_detail_and_list_return_same_snapshot(self):
        data = self.create()
        detail = self.client.get(f"/api/v1/accounts/transfers/{data['id']}/")
        listing = self.client.get("/api/v1/accounts/transfers/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assert_snapshot(detail.data["data"])
        self.assert_snapshot(listing.data["data"][0])

    def test_zero_fee_and_zero_balance_are_real_snapshots(self):
        self.source.balance = Decimal("100")
        self.source.save(update_fields=["balance"])
        self.target.balance = Decimal("0")
        self.target.save(update_fields=["balance"])
        data = self.create(fee="0.00")
        self.assert_snapshot(data, "100.00", "0.00", "0.00", "100.00")

    def test_credit_card_negative_balance_is_preserved(self):
        self.source.account_type = "credit_card"
        self.source.balance = Decimal("-50")
        self.source.save(update_fields=["account_type", "balance"])
        data = self.create()
        self.assert_snapshot(data, source_before="-50.00", source_after="-152.00")

    def test_later_adjustment_and_transfer_do_not_rewrite_history(self):
        first = self.create()
        AccountService.adjust_balance(self.user, self.source.pk, Decimal("5000"))
        AccountService.adjust_balance(self.user, self.target.pk, Decimal("3000"))
        second = self.create()
        self.assert_snapshot(second, "5000.00", "4898.00", "3000.00", "3100.00")
        detail = self.client.get(f"/api/v1/accounts/transfers/{first['id']}/")
        self.assert_snapshot(detail.data["data"])

    def test_old_record_without_snapshots_returns_null_not_current_balance(self):
        transfer = Transfer.objects.create(
            user=self.user, source_account=self.source, target_account=self.target,
            amount="100", fee="0", transfer_time=timezone.now(),
        )
        response = self.client.get(f"/api/v1/accounts/transfers/{transfer.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        for name in ("source_balance_before", "source_balance_after", "target_balance_before", "target_balance_after"):
            self.assertIsNone(data[name])
        self.assertFalse(data["has_balance_snapshot"])

    def test_partial_snapshot_is_not_reported_as_complete(self):
        transfer = Transfer.objects.create(
            user=self.user, source_account=self.source, target_account=self.target,
            amount="100", fee="0", transfer_time=timezone.now(), source_balance_before="1000",
        )
        self.assertFalse(TransferSerializer(transfer).data["has_balance_snapshot"])

    def test_client_cannot_supply_fabricated_snapshot(self):
        data = self.create(
            source_balance_before="99999.00", source_balance_after="99999.00",
            target_balance_before="99999.00", target_balance_after="99999.00",
        )
        self.assert_snapshot(data)

    def test_reversal_keeps_original_snapshot(self):
        data = self.create()
        response = self.client.delete(f"/api/v1/accounts/transfers/{data['id']}/")
        self.assertEqual(response.status_code, 200, response.data)
        transfer = Transfer.objects.get(pk=data["id"])
        self.assertEqual(transfer.status, "deleted")
        self.assert_snapshot(TransferSerializer(transfer).data)
        self.source.refresh_from_db()
        self.target.refresh_from_db()
        self.assertEqual(self.source.balance, Decimal("1000"))
        self.assertEqual(self.target.balance, Decimal("200"))

    def test_failed_transfer_record_creation_rolls_back_balances(self):
        with patch("apps.accounts.services.Transfer.objects.create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                AccountService.create_transfer(self.user, {
                    "source_account_id": self.source.pk,
                    "target_account_id": self.target.pk,
                    "amount": Decimal("100"), "fee": Decimal("2"),
                    "transfer_time": timezone.now(),
                })
        self.source.refresh_from_db()
        self.target.refresh_from_db()
        self.assertEqual(self.source.balance, Decimal("1000"))
        self.assertEqual(self.target.balance, Decimal("200"))
        self.assertFalse(Transfer.objects.exists())

    def test_insufficient_funds_does_not_create_snapshot_record(self):
        response = self.client.post("/api/v1/accounts/transfers/", self.body(amount="1000"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transfer.objects.exists())

    def test_replayed_request_preserves_original_balances(self):
        body = self.body()
        response = self.client.post(
            "/api/v1/accounts/transfers/", body, format="json",
            HTTP_IDEMPOTENCY_KEY="transfer-snapshot-1",
        )
        self.assertEqual(response.status_code, 200, response.data)
        AccountService.adjust_balance(self.user, self.source.pk, Decimal("5000"))
        repeated = self.client.post(
            "/api/v1/accounts/transfers/", body, format="json",
            HTTP_IDEMPOTENCY_KEY="transfer-snapshot-1",
        )
        self.assertEqual(repeated.status_code, 200, repeated.data)
        self.assertEqual(repeated.data, response.data)
        self.assertEqual(Transfer.objects.count(), 1)
        self.assert_snapshot(repeated.data["data"])

    def test_other_user_cannot_read_transfer_balances(self):
        data = self.create()
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f"/api/v1/accounts/transfers/{data['id']}/")
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.data["data"])

    def test_backdated_transfer_uses_execution_balance(self):
        data = self.create(transfer_time=timezone.make_aware(datetime(2020, 1, 1, 12)).isoformat())
        self.assert_snapshot(data)
        self.assertTrue(data["transfer_time"].startswith("2020-01-01"))
