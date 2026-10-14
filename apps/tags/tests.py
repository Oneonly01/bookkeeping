from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.models import Transaction

from .models import Tag


class TagDetailApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="tag-owner", password="Test@123456")
        cls.other_user = user_model.objects.create_user(username="tag-other", password="Test@123456")
        cls.tag = Tag.objects.create(user=cls.user, name="工作", color="#123456")
        cls.duplicate = Tag.objects.create(user=cls.user, name="报销")
        cls.foreign_tag = Tag.objects.create(user=cls.other_user, name="旅行")
        cls.deleted_tag = Tag.objects.create(user=cls.user, name="旧标签", is_deleted=True)
        account = Account.objects.create(user=cls.user, name="测试账户", account_type="cash")
        category = Category.objects.create(user=cls.user, name="测试分类", category_type="expense")
        cls.record = Transaction.objects.create(
            user=cls.user, account=account, category=category,
            transaction_type="expense", amount="1.00", transaction_time=timezone.now(),
        )
        cls.record.tags.add(cls.tag)

    def setUp(self):
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = f"/api/v1/tags/{self.tag.id}/"

    def assert_success(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["code"], 200)
        return response.data["data"]

    def assert_error(self, response, code=400):
        self.assertEqual(response.status_code, code, response.data)
        self.assertEqual(response.data["code"], code)
        self.assertIsNone(response.data["data"])

    def test_get_detail(self):
        data = self.assert_success(self.client.get(self.url))
        self.assertEqual(data["id"], self.tag.id)
        self.assertEqual(data["name"], "工作")
        self.assertEqual(data["color"], "#123456")

    def test_update_preserves_transaction_association(self):
        data = self.assert_success(self.client.put(self.url, {"name": "  新名称  ", "color": "#abcdef"}, format="json"))
        self.assertEqual(data["id"], self.tag.id)
        self.assertEqual(data["name"], "新名称")
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.color, "#abcdef")
        related = self.record.tags.get(id=self.tag.id)
        self.assertEqual(related.name, "新名称")

    def test_color_only_can_clear_color_and_preserves_name(self):
        data = self.assert_success(self.client.put(self.url, {"color": ""}, format="json"))
        self.assertEqual(data["name"], "工作")
        self.assertEqual(data["color"], "")
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.color, "")

    def test_name_only_preserves_color(self):
        data = self.assert_success(self.client.put(self.url, {"name": "新名称"}, format="json"))
        self.assertEqual(data["name"], "新名称")
        self.assertEqual(data["color"], "#123456")

    def test_unchanged_name_is_allowed(self):
        self.assert_success(self.client.put(self.url, {"name": "工作"}, format="json"))

    def test_other_users_name_and_deleted_name_can_be_reused(self):
        for name in ("旅行", "旧标签"):
            with self.subTest(name=name):
                data = self.assert_success(self.client.put(self.url, {"name": name}, format="json"))
                self.assertEqual(data["name"], name)

    def test_duplicate_name_rejected_without_modification(self):
        response = self.client.put(self.url, {"name": "报销", "color": "red"}, format="json")
        self.assert_error(response)
        self.assertEqual(response.data["message"], "该标签已存在")
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, "工作")
        self.assertEqual(self.tag.color, "#123456")

    def test_invalid_fields_rejected_without_modification(self):
        for body in ({"name": ""}, {"name": "   "}, {"name": "x" * 51}, {"color": "x" * 21}, {"name": None}):
            with self.subTest(body=body):
                self.assert_error(self.client.put(self.url, body, format="json"))
                self.tag.refresh_from_db()
                self.assertEqual(self.tag.name, "工作")
                self.assertEqual(self.tag.color, "#123456")

    def test_field_length_boundaries(self):
        data = self.assert_success(self.client.put(self.url, {"name": "x" * 50, "color": "c" * 20}, format="json"))
        self.assertEqual(len(data["name"]), 50)
        self.assertEqual(len(data["color"]), 20)

    def test_missing_deleted_and_foreign_tags_cannot_be_read_or_updated(self):
        for tag_id in (self.tag.id + 10000, self.deleted_tag.id, self.foreign_tag.id):
            url = f"/api/v1/tags/{tag_id}/"
            for method in ("get", "put"):
                with self.subTest(tag_id=tag_id, method=method):
                    response = self.client.get(url) if method == "get" else self.client.put(url, {"name": "无权修改"}, format="json")
                    self.assert_error(response)
                    self.assertEqual(response.data["message"], "标签不存在")
        self.foreign_tag.refresh_from_db()
        self.assertEqual(self.foreign_tag.name, "旅行")
        self.deleted_tag.refresh_from_db()
        self.assertEqual(self.deleted_tag.name, "旧标签")

    def test_authentication_required(self):
        self.client.credentials()
        self.assert_error(self.client.get(self.url), 401)
        self.assert_error(self.client.put(self.url, {"name": "无权修改"}, format="json"), 401)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, "工作")

    def test_delete_still_soft_deletes_and_preserves_association(self):
        self.assert_success(self.client.delete(self.url))
        self.tag.refresh_from_db()
        self.assertTrue(self.tag.is_deleted)
        self.assertTrue(self.record.tags.filter(id=self.tag.id).exists())
        self.assert_error(self.client.get(self.url))
