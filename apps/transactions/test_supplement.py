import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account, Transfer
from apps.budgets.models import Budget
from apps.preferences.models import UserPreference
from apps.savings.models import SavingsGoal, SavingsRecord
from apps.tags.models import Tag
from apps.categories.models import Category
from apps.users.models import UserProfile
from .models import ApiIdempotencyRecord, RecurringExecution, RecurringTransaction, Transaction
from .recurring_services import RecurringTransactionService


class SupplementApiTests(APITestCase): 
    """六项补充功能的正常、异常和跨用户回归测试。"""

    @classmethod
    def setUpTestData(cls): 
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="supplement-user", password="Test@123456")
        cls.other = user_model.objects.create_user(username="supplement-other", password="Test@123456")
        cls.account = Account.objects.create(
            user=cls.user, 
            name="现金", 
            account_type="cash", 
            balance="1000.00", 
            initial_balance="1000.00", 
            is_default=True, 
        )
        cls.target = Account.objects.create(user=cls.user, name="转入", account_type="cash")
        cls.foreign_account = Account.objects.create(
            user=cls.other, 
            name="他人账户", 
            account_type="cash", 
            balance="1000.00", 
        )
        cls.expense = Category.objects.create(user=cls.user, name="餐饮", category_type="expense")
        cls.income = Category.objects.create(user=cls.user, name="工资", category_type="income")
        cls.tag = Tag.objects.create(user=cls.user, name="报销")
        cls.foreign_tag = Tag.objects.create(user=cls.other, name="他人标签")

    def setUp(self): 
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}")

    def ok(self, response): 
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.assertEqual(response.data["code"], 200)
        return response.data["data"]

    def bad(
        self, 
        response, 
        code=400, 
    ): 
        self.assertEqual(response.status_code, code, response.data)
        self.assertEqual(response.data["code"], code)

    def bill_data(self, **changes): 
        return {
            "account_id": self.account.id, "category_id": self.expense.id, 
            "transaction_type": "expense", "amount": "10.00", 
            "transaction_time": timezone.now().isoformat(), **changes, 
        }

    def create_bill(self, **changes): 
        return self.ok(self.client.post("/api/v1/transactions/", self.bill_data(**changes), format="json"))

    def get_balance(self): 
        self.account.refresh_from_db()
        return self.account.balance

    def template_data(self, **changes): 
        return {
            "name": "每日餐饮", "account_id": self.account.id, 
            "category_id": self.expense.id, "transaction_type": "expense", 
            "amount": "10.00", "frequency": "daily", 
            "start_date": timezone.localdate().isoformat(), **changes, 
        }

    def create_template(self, **changes): 
        return self.ok(
            self.client.post("/api/v1/transactions/recurring/", self.template_data(**changes), format="json"), 
        )

    def test_bill_retries_execute_once_and_replay_response(self): 
        body = self.bill_data()
        first = self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="bill-1")
        second = self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="bill-1")
        self.assertEqual(self.ok(first), self.ok(second))
        self.assertEqual(second["Idempotency-Replayed"], "true")
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.get_balance(), Decimal("990.00"))

    def test_reusing_key_for_different_content_is_conflict(self): 
        body = self.bill_data()
        self.ok(self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="conflict"))
        body["amount"] = "20.00"
        self.bad(self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="conflict"), 409)
        self.assertEqual(self.get_balance(), Decimal("990.00"))

    def test_failed_request_does_not_reserve_key(self): 
        body = self.bill_data(amount="2000.00")
        self.bad(self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="retry-failure"))
        self.assertFalse(ApiIdempotencyRecord.objects.filter(request_key="retry-failure").exists())
        body["amount"] = "10.00"
        self.ok(self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="retry-failure"))

    def test_invalid_idempotency_key_rejected(self): 
        self.bad(
            self.client.post("/api/v1/transactions/", self.bill_data(), format="json", HTTP_IDEMPOTENCY_KEY="bad key"), 
        )
        self.assertEqual(self.get_balance(), Decimal("1000.00"))

    def test_transfer_retry_changes_both_accounts_once(self): 
        body = {"source_account_id": self.account.id, "target_account_id": self.target.id, "amount": "20.00", "fee": "1.00", "transfer_time": timezone.now().isoformat()}
        for _ in range(2): 
            self.ok(
                self.client.post("/api/v1/accounts/transfers/", body, format="json", HTTP_IDEMPOTENCY_KEY="transfer-1"), 
            )
        self.assertEqual(Transfer.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.get_balance(), Decimal("979.00"))
        self.target.refresh_from_db()
        self.assertEqual(self.target.balance, Decimal("20.00"))

    def test_savings_deposit_and_withdraw_retry_once(self): 
        goal = SavingsGoal.objects.create(user=self.user, name="旅行", target_amount="100.00")
        for action, amount in (("deposit", "20.00"), ("withdraw", "5.00")): 
            for _ in range(2): 
                self.ok(
                    self.client.post(
                        f"/api/v1/savings/goals/{goal.id}/{action}/", 
                        {"amount": amount}, 
                        format="json", 
                        HTTP_IDEMPOTENCY_KEY=action, 
                    ), 
                )
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal("15.00"))
        self.assertEqual(SavingsRecord.objects.filter(goal=goal).count(), 2)

    def test_same_key_is_isolated_per_user(self): 
        body = self.bill_data()
        self.ok(self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="shared"))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.other).access_token}")
        category = Category.objects.create(user=self.other, name="他人餐饮", category_type="expense")
        body.update(account_id=self.foreign_account.id, category_id=category.id)
        self.ok(self.client.post("/api/v1/transactions/", body, format="json", HTTP_IDEMPOTENCY_KEY="shared"))
        self.assertEqual(ApiIdempotencyRecord.objects.filter(request_key="shared").count(), 2)

    def test_pagination_preference_and_explicit_override(self): 
        UserPreference.objects.create(user=self.user, page_size=5)
        for _ in range(6): 
            self.create_bill()
        data = self.ok(self.client.get("/api/v1/transactions/"))
        self.assertEqual(data["page_size"], 5)
        self.assertEqual(len(data["results"]), 5)
        data = self.ok(self.client.get("/api/v1/transactions/?page_size=6"))
        self.assertEqual(len(data["results"]), 6)
        self.bad(self.client.get("/api/v1/transactions/?page_size=0"))

    def test_default_account_applies_and_cannot_reference_other_user(self): 
        self.ok(self.client.put("/api/v1/preferences/", {"default_account": self.target.id}, format="json"))
        self.account.refresh_from_db()
        self.target.refresh_from_db()
        self.assertFalse(self.account.is_default)
        self.assertTrue(self.target.is_default)
        body = self.bill_data(category_id=self.income.id, transaction_type="income")
        body.pop("account_id")
        data = self.ok(self.client.post("/api/v1/transactions/", body, format="json"))
        self.assertEqual(data["account"], self.target.id)
        self.bad(self.client.put("/api/v1/preferences/", {"default_account": self.foreign_account.id}, format="json"))

    def test_account_default_changes_and_delete_sync_preferences(self): 
        self.ok(self.client.put(f"/api/v1/accounts/{self.target.id}/", {"is_default": True}, format="json"))
        self.assertEqual(self.ok(self.client.get("/api/v1/preferences/"))["default_account"], self.target.id)
        self.ok(self.client.delete(f"/api/v1/accounts/{self.target.id}/"))
        self.assertEqual(self.ok(self.client.get("/api/v1/preferences/"))["default_account"], self.account.id)

    def test_clearing_default_account_requires_explicit_account(self): 
        self.ok(self.client.put("/api/v1/preferences/", {"default_account": None}, format="json"))
        body = self.bill_data()
        body.pop("account_id")
        self.bad(self.client.post("/api/v1/transactions/", body, format="json"))

    def test_currency_stays_consistent_between_both_apis(self): 
        self.ok(self.client.put("/api/v1/preferences/", {"currency": "usd"}, format="json"))
        self.assertEqual(self.ok(self.client.get("/api/v1/users/me/"))["currency"], "USD")
        self.ok(self.client.put("/api/v1/users/me/", {"currency": "CNY"}, format="json"))
        self.assertEqual(self.ok(self.client.get("/api/v1/preferences/"))["currency"], "CNY")

    def test_budget_inherits_threshold_and_reminder_switch(self): 
        today = timezone.localdate()
        self.ok(self.client.put("/api/v1/preferences/", {"budget_reminder_threshold": 50}, format="json"))
        budget = self.ok(
            self.client.post(
                "/api/v1/budgets/", 
                {"budget_type": "overall", "year": today.year, "month": today.month, "amount": "100.00"}, 
                format="json", 
            ), 
        )
        self.assertIsNone(budget["alert_threshold"])
        self.create_bill(amount="60.00")
        progress = self.ok(self.client.get("/api/v1/budgets/progress/"))["budgets"][0]
        self.assertEqual(progress["alert_threshold"], "50.00")
        self.assertTrue(progress["is_alert"])
        self.ok(self.client.put(f"/api/v1/budgets/{budget['id']}/", {"alert_threshold": "80.00"}, format="json"))
        self.assertFalse(self.ok(self.client.get("/api/v1/budgets/progress/"))["budgets"][0]["is_alert"])
        self.ok(self.client.put(f"/api/v1/budgets/{budget['id']}/", {"alert_threshold": None}, format="json"))
        self.ok(self.client.put("/api/v1/preferences/", {"budget_reminder_enabled": False}, format="json"))
        self.assertFalse(self.ok(self.client.get("/api/v1/budgets/progress/"))["budgets"][0]["is_alert"])

    def test_tag_filter_and_cross_user_rejection(self): 
        tagged = self.create_bill(tag_ids=[self.tag.id])
        self.create_bill()
        results = self.ok(self.client.get(f"/api/v1/transactions/?tag_id={self.tag.id}"))["results"]
        self.assertEqual([item["id"] for item in results], [tagged["id"]])
        self.bad(self.client.get(f"/api/v1/transactions/?tag_id={self.foreign_tag.id}"))
        self.bad(self.client.get("/api/v1/transactions/?tag_id=0"))

    def test_export_filters_and_escapes_formulas(self): 
        bill = self.create_bill(tag_ids=[self.tag.id], note="=1+1", merchant='商户,带逗号')
        self.create_bill()
        response = self.client.get(f"/api/v1/transactions/export/?tag_id={self.tag.id}")
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(content)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(bill["id"]))
        self.assertEqual(rows[1][7], '商户,带逗号')
        self.assertEqual(rows[1][8], "'=1+1")

    def test_recycle_bin_restore_and_retry_balance_once(self): 
        bill = self.create_bill(tag_ids=[self.tag.id])
        bill_id = bill["id"]
        self.ok(self.client.delete(f"/api/v1/transactions/{bill_id}/"))
        self.assertEqual(self.get_balance(), Decimal("1000.00"))
        self.assertEqual(self.ok(self.client.get("/api/v1/transactions/"))["count"], 0)
        self.assertEqual(self.ok(self.client.get("/api/v1/transactions/recycle-bin/"))["count"], 1)
        for _ in range(2): 
            self.ok(
                self.client.post(
                    f"/api/v1/transactions/{bill_id}/restore/", 
                    {}, 
                    format="json", 
                    HTTP_IDEMPOTENCY_KEY="restore", 
                ), 
            )
        self.assertEqual(self.get_balance(), Decimal("990.00"))
        self.assertEqual(list(Transaction.objects.get(pk=bill_id).tags.values_list("id", flat=True)), [self.tag.id])
        self.assertEqual(self.ok(self.client.get("/api/v1/transactions/recycle-bin/"))["count"], 0)
        self.bad(self.client.post(f"/api/v1/transactions/{bill_id}/restore/", {}, format="json"))

    def test_restore_insufficient_balance_rolls_back(self): 
        bill = self.create_bill()
        self.ok(self.client.delete(f"/api/v1/transactions/{bill['id']}/"))
        Account.objects.filter(pk=self.account.id).update(balance=0)
        self.bad(self.client.post(f"/api/v1/transactions/{bill['id']}/restore/", {}, format="json"))
        self.assertEqual(Transaction.objects.get(pk=bill["id"]).status, "deleted")
        self.assertEqual(self.get_balance(), Decimal("0.00"))

    def test_restore_can_replace_unavailable_category(self): 
        bill = self.create_bill()
        self.ok(self.client.delete(f"/api/v1/transactions/{bill['id']}/"))
        Category.objects.filter(pk=self.expense.id).update(is_deleted=True)
        self.bad(self.client.post(f"/api/v1/transactions/{bill['id']}/restore/", {}, format="json"))
        replacement = Category.objects.create(user=self.user, name="替代分类", category_type="expense")
        data = self.ok(
            self.client.post(
                f"/api/v1/transactions/{bill['id']}/restore/", 
                {"category_id": replacement.id}, 
                format="json", 
            ), 
        )
        self.assertEqual(data["category"], replacement.id)

    def test_restore_other_users_bill_rejected(self): 
        bill = self.create_bill()
        self.ok(self.client.delete(f"/api/v1/transactions/{bill['id']}/"))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.other).access_token}")
        self.bad(self.client.post(f"/api/v1/transactions/{bill['id']}/restore/", {}, format="json"))
        self.assertEqual(self.ok(self.client.get("/api/v1/transactions/recycle-bin/"))["count"], 0)

    def test_recurring_template_creates_no_bill_until_run_and_runs_once(self): 
        template = self.create_template(tag_ids=[self.tag.id])
        self.assertEqual(Transaction.objects.count(), 0)
        for _ in range(2): 
            self.ok(self.client.post(f"/api/v1/transactions/recurring/{template['id']}/run/", {}, format="json"))
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(RecurringExecution.objects.count(), 1)
        self.assertEqual(self.get_balance(), Decimal("990.00"))
        self.assertEqual(
            self.ok(
                self.client.get(f"/api/v1/transactions/recurring/{template['id']}/executions/"), 
            )["pagination"]["total"], 
            1, 
        )

    def test_recurring_catches_up_and_stops_at_end_date(self): 
        today = timezone.localdate()
        template = self.create_template(
            start_date=(today-timedelta(days=2)).isoformat(), 
            end_date=(today-timedelta(days=1)).isoformat(), 
        )
        result = self.ok(self.client.post(f"/api/v1/transactions/recurring/{template['id']}/run/", {}, format="json"))
        self.assertEqual(len(result["created_ids"]), 2)
        self.assertFalse(RecurringTransaction.objects.get(pk=template["id"]).is_active)
        self.assertEqual(self.get_balance(), Decimal("980.00"))

    def test_recurring_failure_keeps_due_date_and_can_retry(self): 
        template = self.create_template(amount="2000.00")
        url = f"/api/v1/transactions/recurring/{template['id']}/run/"
        result = self.ok(self.client.post(url, {}, format="json"))
        self.assertTrue(result["error"])
        self.assertEqual(RecurringExecution.objects.count(), 0)
        record = RecurringTransaction.objects.get(pk=template["id"])
        self.assertEqual(record.next_date, record.start_date)
        self.ok(self.client.put(f"/api/v1/transactions/recurring/{template['id']}/", {"amount": "10.00"}, format="json"))
        result = self.ok(self.client.post(url, {}, format="json"))
        self.assertFalse(result["error"])
        self.assertEqual(len(result["created_ids"]), 1)

    def test_recurring_deleted_generated_bill_is_not_regenerated(self): 
        template = self.create_template()
        url = f"/api/v1/transactions/recurring/{template['id']}/run/"
        result = self.ok(self.client.post(url, {}, format="json"))
        self.ok(self.client.delete(f"/api/v1/transactions/{result['created_ids'][0]}/"))
        # Simulate a stale scheduler cursor to exercise the database execution guard.
        RecurringTransaction.objects.filter(pk=template["id"]).update(next_date=timezone.localdate())
        self.ok(self.client.post(url, {}, format="json"))
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.get_balance(), Decimal("1000.00"))

    def test_recurring_schedule_boundaries_keep_anchor(self): 
        template = SimpleNamespace(frequency="monthly", interval=1, start_date=date(2024, 1, 31))
        feb = RecurringTransactionService.get_next_date(template, date(2024, 1, 31))
        self.assertEqual(feb, date(2024, 2, 29))
        self.assertEqual(RecurringTransactionService.get_next_date(template, feb), date(2024, 3, 31))
        template = SimpleNamespace(frequency="yearly", interval=1, start_date=date(2024, 2, 29))
        self.assertEqual(RecurringTransactionService.get_next_date(template, date(2027, 2, 28)), date(2028, 2, 29))

    def test_recurring_permissions_invalid_dates_and_paused_template(self): 
        self.bad(
            self.client.post(
                "/api/v1/transactions/recurring/", 
                self.template_data(account_id=self.foreign_account.id), 
                format="json", 
            ), 
        )
        self.bad(self.client.post("/api/v1/transactions/recurring/", self.template_data(interval=0), format="json"))
        self.bad(
            self.client.post("/api/v1/transactions/recurring/", self.template_data(end_date="1900-01-01"), format="json"), 
        )
        template = self.create_template(is_active=False)
        self.assertEqual(
            self.ok(
                self.client.post(f"/api/v1/transactions/recurring/{template['id']}/run/", {}, format="json"), 
            )["created_ids"], 
            [], 
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.other).access_token}")
        for url in (f"/api/v1/transactions/recurring/{template['id']}/", f"/api/v1/transactions/recurring/{template['id']}/executions/"): 
            self.bad(self.client.get(url))

    def test_recurring_existing_schedule_cannot_be_reinterpreted(self): 
        template = self.create_template()
        self.ok(self.client.post(f"/api/v1/transactions/recurring/{template['id']}/run/", {}, format="json"))
        self.bad(
            self.client.put(f"/api/v1/transactions/recurring/{template['id']}/", {"frequency": "monthly"}, format="json"), 
        )
        self.ok(self.client.delete(f"/api/v1/transactions/recurring/{template['id']}/"))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_scheduler_command_and_future_date_rejection(self): 
        self.create_template()
        output = io.StringIO()
        call_command("process_recurring_transactions", stdout=output)
        call_command("process_recurring_transactions", stdout=output)
        self.assertEqual(Transaction.objects.count(), 1)
        with self.assertRaises(CommandError): 
            call_command("process_recurring_transactions", date=timezone.localdate()+timedelta(days=1), stdout=output)

    def test_recovery_of_income_and_credit_card_expense(self): 
        bill = self.create_bill(category_id=self.income.id, transaction_type="income")
        self.ok(self.client.delete(f"/api/v1/transactions/{bill['id']}/"))
        self.ok(self.client.post(f"/api/v1/transactions/{bill['id']}/restore/", {}, format="json"))
        self.assertEqual(self.get_balance(), Decimal("1010.00"))
        expense = self.create_bill()
        self.ok(self.client.delete(f"/api/v1/transactions/{expense['id']}/"))
        Account.objects.filter(pk=self.account.id).update(account_type="credit_card", balance=0)
        self.ok(self.client.post(f"/api/v1/transactions/{expense['id']}/restore/", {}, format="json"))
        self.assertEqual(self.get_balance(), Decimal("-10.00"))

    def test_restore_rejects_inactive_or_foreign_replacement_account(self): 
        bill = self.create_bill()
        self.ok(self.client.delete(f"/api/v1/transactions/{bill['id']}/"))
        Account.objects.filter(pk=self.account.id).update(is_active=False)
        url = f"/api/v1/transactions/{bill['id']}/restore/"
        self.bad(self.client.post(url, {}, format="json"))
        self.bad(self.client.post(url, {"account_id": self.foreign_account.id}, format="json"))
        self.assertEqual(Transaction.objects.get(pk=bill["id"]).status, "deleted")

    def test_downstream_failure_rolls_back_money_and_idempotency_record(self): 
        # 账单保存之后序列化失败，也必须回滚本次扣款和请求凭证。
        with patch("apps.transactions.views.TransactionSerializer", side_effect=RuntimeError("render failed")): 
            with self.assertRaises(RuntimeError): 
                self.client.post(
                    "/api/v1/transactions/", 
                    self.bill_data(), 
                    format="json", 
                    HTTP_IDEMPOTENCY_KEY="rollback", 
                )
        self.assertEqual(self.get_balance(), Decimal("1000.00"))
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertFalse(ApiIdempotencyRecord.objects.filter(request_key="rollback").exists())

    def test_csv_export_isolated_and_excludes_deleted_bills(self): 
        own = self.create_bill()
        deleted = self.create_bill()
        self.ok(self.client.delete(f"/api/v1/transactions/{deleted['id']}/"))
        foreign = Transaction.objects.create(
            user=self.other, 
            account=self.foreign_account, 
            category=self.expense, 
            transaction_type="expense", 
            amount="1.00", 
            transaction_time=timezone.now(), 
        )
        response = self.client.get("/api/v1/transactions/export/")
        rows = list(csv.reader(io.StringIO(b"".join(response.streaming_content).decode("utf-8-sig"))))
        self.assertEqual([row[0] for row in rows[1: ]], [str(own["id"])])
        self.assertNotIn(str(foreign.id), [row[0] for row in rows[1: ]])

    def test_recurring_weekly_and_batch_limit(self): 
        today = timezone.localdate()
        template = self.create_template(start_date=(today-timedelta(days=3)).isoformat())
        result = RecurringTransactionService.execute_due(self.user, template["id"], limit=2)
        self.assertEqual(len(result["created_ids"]), 2)
        self.assertTrue(result["more_due"])
        result = RecurringTransactionService.execute_due(self.user, template["id"], limit=2)
        self.assertEqual(len(result["created_ids"]), 2)
        self.assertFalse(result["more_due"])
        fake = SimpleNamespace(frequency="weekly", interval=2)
        self.assertEqual(RecurringTransactionService.get_next_date(fake, today), today+timedelta(days=14))

    def test_scheduler_failure_reported_and_due_date_preserved(self): 
        template = self.create_template(amount="2000.00")
        with self.assertRaises(CommandError): 
            call_command("process_recurring_transactions", stdout=io.StringIO())
        record = RecurringTransaction.objects.get(pk=template["id"])
        self.assertTrue(record.last_error)
        self.assertEqual(record.next_date, record.start_date)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_new_feature_endpoints_require_authentication(self): 
        self.client.credentials()
        for path in ("/api/v1/transactions/export/", "/api/v1/transactions/recycle-bin/", "/api/v1/transactions/recurring/"): 
            with self.subTest(path=path): 
                self.bad(self.client.get(path), 401)
