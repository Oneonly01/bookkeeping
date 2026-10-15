from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.categories.models import Category

from .models import Transaction


class RecycleBinOrderingTests(APITestCase):
    """验证删除时间排序、恢复后再次删除，以及历史数据回填。"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="recycle-user")
        self.account = Account.objects.create(
            user=self.user,
            name="测试现金",
            account_type="cash",
            balance="1000.00",
        )
        self.category = Category.objects.create(
            user=self.user,
            name="测试餐饮",
            category_type="expense",
        )
        self.client.force_authenticate(self.user)
        self.now = timezone.now()

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["data"]

    def create_bill(self, days_ago=0):
        return self.ok(
            self.client.post(
                "/api/v1/transactions/",
                {
                    "account_id": self.account.id,
                    "category_id": self.category.id,
                    "transaction_type": "expense",
                    "amount": "10.00",
                    "transaction_time": (self.now - timedelta(days=days_ago)).isoformat(),
                },
                format="json",
            ),
        )["id"]

    def delete_bill(self, bill_id, deleted_at):
        with patch("apps.transactions.services.timezone.now", return_value=deleted_at):
            self.ok(self.client.delete(f"/api/v1/transactions/{bill_id}/"))
        self.assertEqual(Transaction.objects.get(pk=bill_id).deleted_at, deleted_at)

    def test_recent_deletion_precedes_recent_transaction(self):
        # 旧交易最后删除，应排在新交易前面；不能再按交易时间排序。
        older = self.create_bill(days_ago=30)
        newer = self.create_bill()
        self.delete_bill(newer, self.now - timedelta(minutes=2))
        self.delete_bill(older, self.now - timedelta(minutes=1))
        rows = self.ok(self.client.get("/api/v1/transactions/recycle-bin/"))["results"]
        self.assertEqual([row["id"] for row in rows], [older, newer])
        self.assertTrue(all(row["deleted_at"] for row in rows))

        # 恢复后正常列表继续按交易时间倒序，删除时间为空。
        for bill_id in (older, newer):
            data = self.ok(
                self.client.post(f"/api/v1/transactions/{bill_id}/restore/", {}, format="json"),
            )
            self.assertIsNone(data["deleted_at"])
        rows = self.ok(self.client.get("/api/v1/transactions/"))["results"]
        self.assertEqual([row["id"] for row in rows], [newer, older])

    def test_same_deletion_time_has_stable_pagination_and_user_isolation(self):
        first = self.create_bill()
        second = self.create_bill(days_ago=1)
        self.delete_bill(first, self.now)
        self.delete_bill(second, self.now)
        other = get_user_model().objects.create_user(username="other-recycle-user")
        Transaction.objects.create(
            user=other,
            account=self.account,
            category=self.category,
            transaction_type="expense",
            amount="1.00",
            transaction_time=self.now,
            status="deleted",
            deleted_at=self.now + timedelta(minutes=1),
        )
        ids = []
        for page in (1, 2):
            data = self.ok(
                self.client.get(f"/api/v1/transactions/recycle-bin/?page_size=1&page={page}"),
            )
            self.assertEqual(data["count"], 2)
            ids.extend(row["id"] for row in data["results"])
        self.assertEqual(ids, [second, first])

    def test_restore_clears_time_and_next_delete_records_new_time(self):
        bill_id = self.create_bill()
        self.delete_bill(bill_id, self.now - timedelta(hours=1))
        Account.objects.filter(pk=self.account.id).update(balance=0)
        response = self.client.post(f"/api/v1/transactions/{bill_id}/restore/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        record = Transaction.objects.get(pk=bill_id)
        self.assertEqual(record.status, "deleted")
        self.assertEqual(record.deleted_at, self.now - timedelta(hours=1))

        Account.objects.filter(pk=self.account.id).update(balance=1000)
        data = self.ok(
            self.client.post(f"/api/v1/transactions/{bill_id}/restore/", {}, format="json"),
        )
        self.assertIsNone(data["deleted_at"])
        self.assertIsNone(Transaction.objects.get(pk=bill_id).deleted_at)
        self.delete_bill(bill_id, self.now)

    def test_historical_backfill_uses_updated_at_for_deleted_rows_only(self):
        old_id = self.create_bill()
        normal_id = self.create_bill()
        populated_id = self.create_bill()
        old_time = self.now - timedelta(days=2)
        Transaction.objects.filter(pk=old_id).update(status="deleted", updated_at=old_time)
        Transaction.objects.filter(pk=populated_id).update(status="deleted", deleted_at=self.now)
        migration = import_module("apps.transactions.migrations.0005_transaction_deleted_at")
        migration.fill_deleted_at(apps, SimpleNamespace(connection=connection))
        self.assertEqual(Transaction.objects.get(pk=old_id).deleted_at, old_time)
        self.assertIsNone(Transaction.objects.get(pk=normal_id).deleted_at)
        self.assertEqual(Transaction.objects.get(pk=populated_id).deleted_at, self.now)
