from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import UserProfile


User = get_user_model()


class UsernameEmailLoginTests(APITestCase):
    """用户名和邮箱登录，以及账号冲突、禁用账号等异常情况。"""

    @classmethod
    def setUpTestData(cls):
        cls.password = "R7!xQ2@pL9#v"
        cls.user = User.objects.create_user(
            username="login-owner",
            email="owner@example.com",
            password=cls.password,
        )

    def login(self, account, password=None):
        return self.client.post(
            "/api/v1/auth/login/",
            {
                "username": account,
                "password": password if password is not None else self.password,
            },
            format="json",
        )

    def assert_login_user(self, response, user):
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["user"]["id"], user.id)
        self.assertTrue(response.data["data"]["access_token"])
        self.assertTrue(response.data["data"]["refresh_token"])

    def test_username_login_remains_available(self):
        self.assert_login_user(self.login(self.user.username), self.user)

    def test_email_login_ignores_case_and_trims_outer_spaces(self):
        self.assert_login_user(self.login("  OWNER@EXAMPLE.COM  "), self.user)

    def test_unknown_account_and_wrong_password_return_same_error(self):
        for account, password in (
            ("unknown@example.com", self.password),
            (self.user.email, "incorrect-password"),
            (self.user.username, "incorrect-password"),
        ):
            with self.subTest(account=account):
                response = self.login(account, password)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["message"], "用户名或密码错误")

    def test_disabled_user_cannot_login_with_username_or_email(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        for account in (self.user.username, self.user.email):
            with self.subTest(account=account):
                self.assertEqual(self.login(account).status_code, 400)

    def test_duplicate_historical_emails_are_not_arbitrarily_selected(self):
        User.objects.create_user(
            username="legacy-owner",
            email="OWNER@example.com",
            password=self.password,
        )
        self.assertEqual(self.login(self.user.email).status_code, 400)
        self.assert_login_user(self.login(self.user.username), self.user)

    def test_exact_username_takes_precedence_over_another_users_email(self):
        account = User.objects.create_user(
            username=self.user.email,
            email="different@example.com",
            password="Different@321!",
        )
        # 同一输入先作为用户名处理，错误密码不回退到邮箱对应的其他账号。
        self.assertEqual(self.login(self.user.email).status_code, 400)
        self.assert_login_user(self.login(self.user.email, "Different@321!"), account)

    def test_email_longer_than_username_limit_can_login(self):
        email = "owner@" + ".".join(["a" * 50, "b" * 50, "c" * 50, "com"])
        self.user.email = email
        self.user.save(update_fields=["email"])
        self.assertGreater(len(email), 150)
        self.assert_login_user(self.login(email), self.user)

    def test_missing_blank_or_overlong_login_account_is_rejected(self):
        bodies = (
            {"password": self.password},
            {"username": " ", "password": self.password},
            {"username": "a" * 255, "password": self.password},
            {"username": self.user.email},
        )
        for body in bodies:
            with self.subTest(body=body):
                response = self.client.post("/api/v1/auth/login/", body, format="json")
                self.assertEqual(response.status_code, 400)


class RegisterPasswordPolicyTests(APITestCase):
    """注册密码与项目密码规则保持一致，失败时不创建用户或资料。"""

    def payload(self, **changes):
        return {
            "username": "register-owner",
            "email": "register@example.com",
            "phone": "13800000009",
            "password": "R7!xQ2@pL9#v",
            "confirm_password": "R7!xQ2@pL9#v",
            **changes,
        }

    def test_strong_password_is_hashed_and_blank_nickname_is_generated(self):
        body = self.payload(nickname=" ")
        response = self.client.post("/api/v1/auth/register/", body, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        user = User.objects.get(username=body["username"])
        self.assertNotEqual(user.password, body["password"])
        self.assertTrue(user.check_password(body["password"]))
        self.assertTrue(user.profile.nickname.startswith("用户"))
        self.assertEqual(user.profile.phone, body["phone"])

    def test_missing_nickname_is_generated(self):
        response = self.client.post("/api/v1/auth/register/", self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(UserProfile.objects.get().nickname.startswith("用户"))

    def test_custom_nickname_is_preserved(self):
        body = self.payload(nickname="记账小伙伴")
        response = self.client.post("/api/v1/auth/register/", body, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(UserProfile.objects.get().nickname, body["nickname"])

    def test_short_common_numeric_and_similar_passwords_are_rejected(self):
        for password in ("aB@123", "password", "8736491052", "register-owner"):
            with self.subTest(password=password):
                response = self.client.post(
                    "/api/v1/auth/register/",
                    self.payload(password=password, confirm_password=password),
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertFalse(User.objects.exists())
                self.assertFalse(UserProfile.objects.exists())

    def test_password_mismatch_is_rejected_before_creation(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            self.payload(confirm_password="Different@321!"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())
        self.assertFalse(UserProfile.objects.exists())

    def test_email_and_phone_remain_required(self):
        for field in ("email", "phone"):
            with self.subTest(field=field):
                body = self.payload()
                body.pop(field)
                response = self.client.post("/api/v1/auth/register/", body, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(User.objects.exists())
