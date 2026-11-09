from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


User = get_user_model()


@override_settings(SIMPLE_JWT={
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_REVOKE_TOKEN": True,
})
class TokenRefreshTests(APITestCase):
    """使用独立测试数据库验证真实刷新接口，不访问开发账号。"""

    def setUp(self):
        # SimpleJWT 的模块会缓存导入时的设置对象；隔离测试显式使用本用例的设置。
        from rest_framework_simplejwt.settings import api_settings
        for token_class, lifetime in (
            (RefreshToken, api_settings.REFRESH_TOKEN_LIFETIME),
            (AccessToken, api_settings.ACCESS_TOKEN_LIFETIME),
        ):
            lifetime_patch = patch.object(token_class, "lifetime", lifetime)
            lifetime_patch.start()
            self.addCleanup(lifetime_patch.stop)
        for target in (
            "rest_framework_simplejwt.tokens.api_settings",
            "rest_framework_simplejwt.serializers.api_settings",
            "rest_framework_simplejwt.authentication.api_settings",
            "apps.users.serializers.jwt_settings",
        ):
            setting_patch = patch(target, api_settings)
            setting_patch.start()
            self.addCleanup(setting_patch.stop)
        self.user = User.objects.create_user(username="refresh-test", password="Test@7654321")
        self.token = RefreshToken.for_user(self.user)

    def refresh(self, token=None, **headers):
        return self.client.post("/api/v1/auth/refresh/", {
            "refresh_token": str(token if token is not None else self.token)
        }, format="json", **headers)

    def test_rotation_renews_claims_and_blacklists_old_token(self):
        self.token.set_iat(at_time=timezone.now() - timedelta(hours=1))
        self.token.set_exp(from_time=timezone.now() - timedelta(hours=1))
        response = self.refresh()
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["token_type"], "Bearer")
        fresh = RefreshToken(data["refresh_token"])
        access = AccessToken(data["access_token"])
        self.assertNotEqual(fresh["jti"], self.token["jti"])
        self.assertGreater(fresh["iat"], self.token["iat"])
        self.assertGreater(fresh["exp"], self.token["exp"])
        self.assertEqual(fresh["exp"] - fresh["iat"], 7 * 86400)
        self.assertEqual(access["exp"] - access["iat"], 3600)
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=self.token["jti"]).exists())
        self.assertTrue(OutstandingToken.objects.filter(jti=fresh["jti"]).exists())
        self.assertEqual(self.refresh().status_code, 400)
        self.assertEqual(self.refresh(fresh).status_code, 200)

    def test_new_access_can_authenticate_protected_endpoint(self):
        response = self.refresh()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["data"]["access_token"])
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)

    def test_refresh_ignores_expired_access_header(self):
        access = self.token.access_token
        access.set_exp(from_time=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.refresh(HTTP_AUTHORIZATION="Bearer " + str(access)).status_code, 200)

    def test_disabled_user_is_rejected_without_minting_or_blacklisting(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.refresh().status_code, 400)
        self.assertFalse(BlacklistedToken.objects.filter(token__jti=self.token["jti"]).exists())

    def test_password_change_revokes_existing_refresh(self):
        self.user.set_password("New@7654321")
        self.user.save(update_fields=["password"])
        self.assertEqual(self.refresh().status_code, 400)
        self.assertEqual(self.refresh(RefreshToken.for_user(self.user)).status_code, 200)

    def test_deleted_user_is_rejected(self):
        self.user.delete()
        self.assertEqual(self.refresh().status_code, 400)

    def test_missing_or_invalid_user_claim_is_rejected(self):
        for claim in (None, "not-an-id", 99999999):
            token = RefreshToken.for_user(self.user)
            if claim is None:
                del token["user_id"]
            else:
                token["user_id"] = claim
            with self.subTest(claim=claim):
                self.assertEqual(self.refresh(token).status_code, 400)

    def test_expired_blacklisted_access_and_malformed_tokens_are_rejected(self):
        expired = RefreshToken.for_user(self.user)
        expired.set_exp(from_time=timezone.now() - timedelta(days=8))
        blacklisted = RefreshToken.for_user(self.user)
        blacklisted.blacklist()
        for token in (expired, blacklisted, self.token.access_token, "bad-token"):
            with self.subTest(kind=type(token).__name__):
                self.assertEqual(self.refresh(token).status_code, 400)
        with self.assertRaises(TokenError):
            RefreshToken(str(blacklisted))

    def test_missing_refresh_field_is_rejected(self):
        for body in ({}, {"refreshToken": str(self.token)}, {"refresh_token": ""}):
            self.assertEqual(self.client.post("/api/v1/auth/refresh/", body, format="json").status_code, 400)
