from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import Account


class AccountListFilterTests(APITestCase):
    """账户列表筛选：验证缺省条件、false值、组合条件及用户隔离。"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="filter-owner")
        self.other = get_user_model().objects.create_user(username="filter-other")
        self.bank = Account.objects.create(
            user=self.user, name="建设银行储蓄卡", account_type="bank",
            is_active=True, is_default=True, sort_order=20,
        )
        self.credit = Account.objects.create(
            user=self.user, name="建设银行信用卡", account_type="credit_card",
            is_active=False, sort_order=10,
        )
        self.cash = Account.objects.create(
            user=self.user, name="现金", account_type="cash", sort_order=20,
        )
        self.deleted = Account.objects.create(
            user=self.user, name="建设银行已删除", account_type="bank", is_deleted=True,
        )
        self.foreign = Account.objects.create(
            user=self.other, name="建设银行他人账户", account_type="bank", is_default=True,
        )
        self.client.force_authenticate(user=self.user)

    def query_ids(self, params=None):
        response = self.client.get("/api/v1/accounts/", params or {})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["message"], "获取账户列表成功")
        self.assertIsInstance(response.data["data"], list)
        return [item["id"] for item in response.data["data"]]

    def test_no_filters_returns_active_and_inactive_in_original_order(self):
        self.assertEqual(self.query_ids(), [self.credit.pk, self.bank.pk, self.cash.pk])

    def test_keyword_is_trimmed_and_matches_account_name(self):
        self.assertEqual(self.query_ids({"keyword": "  建设  "}), [self.credit.pk, self.bank.pk])

    def test_empty_keyword_does_not_filter(self):
        for value in ("", "   "):
            with self.subTest(value=value):
                self.assertEqual(self.query_ids({"keyword": value}), self.query_ids())

    def test_all_account_types_are_accepted_and_bank_does_not_include_credit(self):
        for kind, expected in (
            ("bank", [self.bank.pk]), ("credit_card", [self.credit.pk]),
            ("cash", [self.cash.pk]), ("wechat", []), ("alipay", []), ("other", []),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(self.query_ids({"account_type": kind}), expected)

    def test_active_true_and_false_filter_correctly(self):
        self.assertEqual(self.query_ids({"is_active": "true"}), [self.bank.pk, self.cash.pk])
        self.assertEqual(self.query_ids({"is_active": "false"}), [self.credit.pk])

    def test_default_true_and_false_filter_correctly(self):
        self.assertEqual(self.query_ids({"is_default": "true"}), [self.bank.pk])
        self.assertEqual(self.query_ids({"is_default": "false"}), [self.credit.pk, self.cash.pk])

    def test_multiple_filters_are_intersected(self):
        self.assertEqual(self.query_ids({
            "keyword": "建设", "account_type": "bank",
            "is_active": "true", "is_default": "true",
        }), [self.bank.pk])

    def test_conflicting_filters_return_empty_list(self):
        self.assertEqual(self.query_ids({"account_type": "bank", "is_active": "false"}), [])

    def test_user_id_cannot_override_authenticated_user(self):
        self.assertEqual(self.query_ids({"user_id": self.other.pk, "account_type": "bank"}), [self.bank.pk])

    def test_unknown_keyword_returns_empty_list(self):
        self.assertEqual(self.query_ids({"keyword": "不存在"}), [])

    def test_invalid_choices_and_booleans_are_rejected(self):
        cases = (
            {"account_type": "invalid"}, {"account_type": ""},
            {"is_active": "invalid"}, {"is_default": "invalid"},
            {"is_active": ""}, {"is_default": ""},
            {"keyword": "a" * 51},
        )
        for params in cases:
            with self.subTest(params=params):
                response = self.client.get("/api/v1/accounts/", params)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(response.data["code"], 400)
                self.assertIsNone(response.data["data"])

    def test_no_filter_changes_stored_account_data(self):
        before = list(Account.objects.order_by("pk").values())
        self.query_ids({"is_active": "false", "keyword": "建设"})
        self.assertEqual(list(Account.objects.order_by("pk").values()), before)

    def test_anonymous_user_is_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/accounts/")
        self.assertEqual(response.status_code, 401)
