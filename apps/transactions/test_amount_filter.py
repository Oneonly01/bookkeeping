import csv
import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.tags.models import Tag

from .models import Transaction


class TransactionAmountFilterTests(APITestCase):
    """金额边界、组合条件，以及列表、回收站、导出的筛选一致性。"""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="amount-owner")
        cls.other = get_user_model().objects.create_user(username="amount-other")
        cls.account = Account.objects.create(user=cls.user, name="测试现金", account_type="cash")
        cls.category = Category.objects.create(user=cls.user, name="餐饮", category_type="expense")
        cls.tag = Tag.objects.create(user=cls.user, name="筛选测试")
        cls.now = timezone.now()
        cls.bills = []
        for index, amount in enumerate(("0.01", "10.00", "20.00", "100.00")):
            cls.bills.append(
                Transaction.objects.create(
                    user=cls.user,
                    account=cls.account,
                    category=cls.category,
                    transaction_type="expense",
                    amount=amount,
                    transaction_time=cls.now - timedelta(minutes=index),
                    merchant="金额测试",
                ),
            )
        cls.bills[2].tags.add(cls.tag)
        cls.deleted = Transaction.objects.create(
            user=cls.user,
            account=cls.account,
            category=cls.category,
            transaction_type="expense",
            amount="15.00",
            transaction_time=cls.now,
            status="deleted",
            deleted_at=cls.now,
        )
        other_account = Account.objects.create(user=cls.other, name="其他现金", account_type="cash")
        cls.foreign = Transaction.objects.create(
            user=cls.other,
            account=other_account,
            category=cls.category,
            transaction_type="expense",
            amount="15.00",
            transaction_time=cls.now,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def query(self, params=None, path="/api/v1/transactions/"):
        response = self.client.get(path, params or {})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["data"]

    def ids(self, params=None):
        return [row["id"] for row in self.query(params)["results"]]

    def test_no_amount_parameters_preserves_existing_list(self):
        self.assertEqual(self.ids(), [bill.id for bill in self.bills])

    def test_empty_optional_query_values_are_treated_as_omitted(self):
        # 查询参数中的空字符串沿用DRF对可选参数的处理，方便Apifox留空。
        self.assertEqual(self.ids({"min_amount": "", "max_amount": ""}), self.ids())

    def test_range_includes_both_boundaries(self):
        self.assertEqual(
            self.ids({"min_amount": "10.00", "max_amount": "20.00"}),
            [self.bills[1].id, self.bills[2].id],
        )

    def test_single_bound_and_exact_amount(self):
        cases = (
            ({"min_amount": "20.00"}, [self.bills[2].id, self.bills[3].id]),
            ({"max_amount": "10.00"}, [self.bills[0].id, self.bills[1].id]),
            ({"min_amount": "20.00", "max_amount": "20.00"}, [self.bills[2].id]),
            ({"max_amount": "0.00"}, []),
            ({"min_amount": "0.00"}, [bill.id for bill in self.bills]),
            ({"min_amount": "999999999999.99"}, []),
        )
        for params, expected in cases:
            with self.subTest(params=params):
                self.assertEqual(self.ids(params), expected)

    def test_amount_range_combines_with_existing_filters_and_pagination(self):
        params = {
            "min_amount": "10.00",
            "max_amount": "20.00",
            "tag_id": self.tag.id,
            "account_id": self.account.id,
            "category_id": self.category.id,
            "transaction_type": "expense",
            "keyword": "金额测试",
            "start_date": (timezone.localdate() - timedelta(days=1)).isoformat(),
            "end_date": timezone.localdate().isoformat(),
            "page_size": 1,
        }
        data = self.query(params)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.bills[2].id)
        self.assertEqual(data["page_size"], 1)

    def test_recycle_bin_filters_amount_without_showing_normal_bills(self):
        data = self.query(
            {"min_amount": "10.00", "max_amount": "20.00"},
            "/api/v1/transactions/recycle-bin/",
        )
        self.assertEqual([row["id"] for row in data["results"]], [self.deleted.id])
        self.assertEqual(
            self.query({"max_amount": "10.00"}, "/api/v1/transactions/recycle-bin/")["count"],
            0,
        )

    def test_csv_export_uses_same_range_and_excludes_deleted_or_foreign_bills(self):
        response = self.client.get(
            "/api/v1/transactions/export/",
            {"min_amount": "10.00", "max_amount": "20.00", "page_size": 1},
        )
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(content)))
        self.assertEqual([int(row[0]) for row in rows[1:]], [self.bills[1].id, self.bills[2].id])

    def test_invalid_ranges_and_amounts_are_rejected_on_all_three_endpoints(self):
        cases = (
            {"min_amount": "20.00", "max_amount": "10.00"},
            {"min_amount": "-0.01"},
            {"max_amount": "-1"},
            {"min_amount": "abc"},
            {"max_amount": "10.001"},
            {"max_amount": "1000000000000.00"},
            {"min_amount": " "},
        )
        paths = (
            "/api/v1/transactions/",
            "/api/v1/transactions/recycle-bin/",
            "/api/v1/transactions/export/",
        )
        for path in paths:
            for params in cases:
                with self.subTest(path=path, params=params):
                    response = self.client.get(path, params)
                    self.assertEqual(response.status_code, 400, getattr(response, "data", None))
                    self.assertEqual(response.data["code"], 400)
