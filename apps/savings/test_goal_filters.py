"""独立验证存钱罐组合查询、金额边界、参数错误与用户隔离。"""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.savings.models import SavingsGoal


class SavingsGoalFilterTests(APITestCase):
    def setUp(self):
        clock = patch("django.utils.timezone.localdate", return_value=date(2026, 11, 8))
        clock.start()
        self.addCleanup(clock.stop)
        self.user = get_user_model().objects.create_user(username="savings-filter-owner")
        self.other = get_user_model().objects.create_user(username="savings-filter-other")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/savings/goals/"
        self.trip = self.goal("旅行基金", "5000.00", "1000.00", date(2026, 11, 30), note="年度假期")
        self.laptop = self.goal("电脑", "9000.00", "0.00", None, note="旅行办公设备")
        self.expired = self.goal("旅行旧计划", "2000.00", "100.00", date(2026, 11, 7))
        self.paused = self.goal("旅行暂停计划", "3000.00", "500.00", date(2026, 12, 1), status="paused")
        self.deleted = self.goal("旅行删除计划", "5000.00", "1000.00", date(2026, 11, 30), is_deleted=True)
        self.foreign = self.goal("旅行其他用户", "5000.00", "1000.00", date(2026, 11, 30), user=self.other)

    def goal(self, name, target, current, deadline, **extra):
        return SavingsGoal.objects.create(
            user=extra.pop("user", self.user), name=name, target_amount=target,
            current_amount=current, deadline=deadline, **extra,
        )

    def ids(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsInstance(response.data["data"], list)
        return [goal["id"] for goal in response.data["data"]]

    def test_default_order_and_empty_keyword_preserve_original_list(self):
        expected = [self.paused.pk, self.expired.pk, self.laptop.pk, self.trip.pk]
        for keyword in (None, "", "  "):
            params = {} if keyword is None else {"keyword": keyword}
            self.assertEqual(self.ids(**params), expected)

    def test_keyword_matches_name_or_note_and_trims_spaces(self):
        self.assertEqual(self.ids(keyword="  旅行  "), [self.paused.pk, self.expired.pk, self.laptop.pk, self.trip.pk])
        self.assertEqual(self.ids(keyword="假期"), [self.trip.pk])
        self.assertEqual(self.ids(keyword="不存在"), [])

    def test_target_amount_range_includes_equal_boundaries(self):
        self.assertEqual(self.ids(min_target_amount="3000", max_target_amount="5000.00"), [self.paused.pk, self.trip.pk])
        self.assertEqual(self.ids(min_target_amount="5000", max_target_amount="5000"), [self.trip.pk])

    def test_current_amount_range_includes_equal_boundaries(self):
        self.assertEqual(self.ids(min_current_amount="100", max_current_amount="500"), [self.paused.pk, self.expired.pk])
        self.assertEqual(self.ids(min_current_amount="0", max_current_amount="0"), [self.laptop.pk])

    def test_single_amount_bounds_and_zero_are_not_ignored(self):
        cases = (
            ({"max_current_amount": "0"}, [self.laptop.pk]),
            ({"min_current_amount": "1000"}, [self.trip.pk]),
            ({"min_target_amount": "9000"}, [self.laptop.pk]),
            ({"max_target_amount": "0"}, []),
        )
        for params, expected in cases:
            with self.subTest(params=params):
                self.assertEqual(self.ids(**params), expected)

    def test_deadline_range_includes_bounds_and_excludes_no_deadline(self):
        self.assertEqual(self.ids(deadline_start="2026-11-07", deadline_end="2026-11-30"), [self.expired.pk, self.trip.pk])
        self.assertEqual(self.ids(deadline_start="2026-11-30", deadline_end="2026-11-30"), [self.trip.pk])
        self.assertEqual(self.ids(deadline_end="2026-11-07"), [self.expired.pk])
        self.assertEqual(self.ids(deadline_start="2026-12-01"), [self.paused.pk])

    def test_all_conditions_are_intersected(self):
        self.assertEqual(self.ids(keyword="旅行", status="active", min_target_amount="5000", max_target_amount="5000",
                                  min_current_amount="1000", max_current_amount="1000",
                                  deadline_start="2026-11-30", deadline_end="2026-11-30"), [self.trip.pk])
        self.assertEqual(self.ids(keyword="电脑", status="overdue"), [])
        self.assertEqual(self.ids(keyword="旅行", status="overdue", max_current_amount="100"), [self.expired.pk])

    def test_foreign_and_deleted_goals_cannot_be_returned_by_parameters(self):
        self.assertEqual(self.ids(keyword="旅行", min_current_amount="1000", user_id=self.other.pk, is_deleted="true"), [self.trip.pk])

    def test_invalid_range_order_is_rejected(self):
        for params in (
            {"min_target_amount": "5000", "max_target_amount": "4999.99"},
            {"min_current_amount": "1", "max_current_amount": "0"},
            {"deadline_start": "2026-12-01", "deadline_end": "2026-11-30"},
        ):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["code"], 400)

    def test_invalid_amounts_are_rejected_for_every_bound(self):
        for key in ("min_target_amount", "max_target_amount", "min_current_amount", "max_current_amount"):
            for value in ("-1", "abc", "NaN", "Infinity", "1.001", "1000000000000", ""):
                with self.subTest(key=key, value=value):
                    self.assertEqual(self.client.get(self.url, {key: value}).status_code, 400)

    def test_invalid_dates_and_excessive_keyword_are_rejected(self):
        for params in ({"deadline_start": "2026-02-30"}, {"deadline_end": "not-date"},
                       {"deadline_start": ""}, {"keyword": "字" * 101}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, 400)

    def test_authentication_is_still_required(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url, {"keyword": "旅行"}).status_code, 401)
