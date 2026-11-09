"""使用独立测试数据库验证逾期边界、状态转换及接口权限。"""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.savings.models import SavingsGoal


class SavingsOverdueTests(APITestCase):
    def setUp(self):
        self.today = date(2026, 11, 8)
        self.clock = patch("django.utils.timezone.localdate", return_value=self.today)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.user = get_user_model().objects.create_user(username="overdue-owner")
        self.other = get_user_model().objects.create_user(username="overdue-other")
        self.client.force_authenticate(user=self.user)
        self.base = "/api/v1/savings/goals/"
        self.past = self.goal("昨天到期", date(2026, 11, 7))
        self.due_today = self.goal("今天到期", self.today)
        self.future = self.goal("明天到期", date(2026, 11, 9))
        self.no_deadline = self.goal("长期储蓄", None)
        self.paused = self.goal("已暂停", date(2026, 11, 1), status="paused")
        self.completed = self.goal("已完成", date(2026, 11, 1), status="completed", current_amount="100.00")
        self.deleted = self.goal("已删除", date(2026, 11, 1), is_deleted=True)
        self.foreign = self.goal("其他用户", date(2026, 11, 1), user=self.other)

    def goal(self, name, deadline, **extra):
        return SavingsGoal.objects.create(
            name=name, deadline=deadline, target_amount="100.00",
            user=extra.pop("user", self.user), **extra,
        )

    def detail(self, goal):
        response = self.client.get(f"{self.base}{goal.pk}/")
        self.assertEqual(response.status_code, 200)
        return response.data["data"]

    def list_ids(self, **params):
        response = self.client.get(self.base, params)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data["data"], list)
        return [item["id"] for item in response.data["data"]]

    def test_overdue_metadata_preserves_business_status(self):
        data = self.detail(self.past)
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["status_display"], "进行中")
        self.assertTrue(data["is_overdue"])
        self.assertEqual(data["overdue_days"], 1)
        self.assertEqual(data["display_status"], "overdue")
        self.assertEqual(data["display_status_text"], "已逾期")
        self.past.refresh_from_db()
        self.assertEqual(self.past.status, "active")

    def test_today_future_no_deadline_paused_completed_are_not_overdue(self):
        for goal in (self.due_today, self.future, self.no_deadline, self.paused, self.completed):
            with self.subTest(goal=goal.name):
                data = self.detail(goal)
                self.assertFalse(data["is_overdue"])
                self.assertEqual(data["overdue_days"], 0)
                self.assertEqual(data["display_status"], goal.status)
                self.assertEqual(data["display_status_text"], goal.get_status_display())

    def test_list_defaults_to_all_non_deleted_owned_goals_in_original_order(self):
        self.assertEqual(self.list_ids(), [self.completed.pk, self.paused.pk,
                         self.no_deadline.pk, self.future.pk, self.due_today.pk, self.past.pk])

    def test_overdue_filter_does_not_include_deleted_or_other_users(self):
        self.assertEqual(self.list_ids(status="overdue", user_id=self.other.pk), [self.past.pk])

    def test_active_filter_excludes_overdue_and_preserves_no_deadline(self):
        self.assertEqual(self.list_ids(status="active"),
                         [self.no_deadline.pk, self.future.pk, self.due_today.pk])

    def test_paused_and_completed_filters(self):
        self.assertEqual(self.list_ids(status="paused"), [self.paused.pk])
        self.assertEqual(self.list_ids(status="completed"), [self.completed.pk])

    def test_invalid_filter_returns_400(self):
        response = self.client.get(self.base, {"status": "unknown"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.base, {"status": "overdue"}).status_code, 401)

    def test_foreign_detail_and_deleted_detail_remain_inaccessible(self):
        for goal in (self.foreign, self.deleted):
            response = self.client.get(f"{self.base}{goal.pk}/")
            self.assertNotEqual(response.status_code, 200)

    def test_day_rollover_changes_display_without_database_updates(self):
        before = self.due_today.updated_at
        with patch("django.utils.timezone.localdate", return_value=date(2026, 11, 9)):
            data = self.detail(self.due_today)
            self.assertTrue(data["is_overdue"])
            self.assertEqual(data["overdue_days"], 1)
            self.assertEqual(set(self.list_ids(status="overdue")), {self.past.pk, self.due_today.pk})
        self.due_today.refresh_from_db()
        self.assertEqual(self.due_today.updated_at, before)

    def test_extending_or_clearing_deadline_removes_overdue(self):
        for deadline in ("2026-11-09", None):
            with self.subTest(deadline=deadline):
                response = self.client.put(f"{self.base}{self.past.pk}/", {"deadline": deadline}, format="json")
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.data["data"]["is_overdue"])
                self.assertEqual(response.data["data"]["display_status"], "active")

    def test_pausing_clears_marker_resuming_expired_goal_restores_it(self):
        response = self.client.post(f"{self.base}{self.past.pk}/pause/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["display_status"], "paused")
        self.assertFalse(response.data["data"]["is_overdue"])
        response = self.client.post(f"{self.base}{self.past.pk}/resume/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["display_status"], "overdue")

    def test_overdue_goal_can_keep_saving_and_completion_clears_marker(self):
        for amount, expected in (("10.00", "overdue"), ("90.00", "completed")):
            response = self.client.post(f"{self.base}{self.past.pk}/deposit/", {"amount": amount}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["data"]["goal"]["display_status"], expected)
        self.assertEqual(self.list_ids(status="overdue"), [])

    def test_summary_and_dashboard_share_counts_without_changing_active_count(self):
        summary = self.client.get("/api/v1/savings/summary/")
        dashboard = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(dashboard.status_code, 200)
        for data in (summary.data["data"], dashboard.data["data"]["savings"]):
            self.assertEqual(data["total_count"], 6)
            self.assertEqual(data["active_count"], 4)
            self.assertEqual(data["overdue_count"], 1)
            self.assertEqual(data["paused_count"], 1)
            self.assertEqual(data["completed_count"], 1)
            self.assertEqual(data["total_count"], data["active_count"] + data["paused_count"] + data["completed_count"])
