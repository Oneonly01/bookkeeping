from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.transactions.models import Transaction, TransactionImage


class TransactionImageLimitTests(APITestCase):
    """验证凭证累计数量、边界、补传及用户隔离，不写入真实上传目录。"""

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(MEDIA_ROOT=self.directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = get_user_model().objects.create_user(username="image-limit-owner")
        self.other = get_user_model().objects.create_user(username="image-limit-other")
        self.account = Account.objects.create(user=self.user, name="现金", account_type="cash")
        self.bill = Transaction.objects.create(
            user=self.user, account=self.account, transaction_type="expense",
            amount="1", transaction_time=timezone.now(),
        )
        self.client.force_authenticate(user=self.user)
        output = BytesIO()
        Image.new("RGB", (2, 2), "white").save(output, format="PNG")
        self.image_bytes = output.getvalue()

    def upload(self, bill=None, name="voucher.png", content=None):
        return self.client.post(
            f"/api/v1/transactions/{(bill or self.bill).pk}/images/",
            {"image": SimpleUploadedFile(name, content if content is not None else self.image_bytes, content_type="image/png")},
            format="multipart",
        )

    def fill(self, count):
        for _ in range(count):
            response = self.upload()
            self.assertEqual(response.status_code, 200, response.data)

    def test_ninth_image_is_allowed(self):
        self.fill(8)
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(TransactionImage.objects.filter(transaction=self.bill).count(), 9)

    def test_tenth_image_is_rejected_without_saving_file(self):
        self.fill(9)
        files_before = sorted(str(path) for path in Path(self.directory.name).rglob('*') if path.is_file())
        response = self.upload()
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("9", response.data["message"])
        self.assertEqual(TransactionImage.objects.count(), 9)
        self.assertEqual(files_before, sorted(str(path) for path in Path(self.directory.name).rglob('*') if path.is_file()))

    def test_deletion_releases_slot_for_replacement(self):
        self.fill(9)
        image = TransactionImage.objects.filter(transaction=self.bill).first()
        response = self.client.delete(f"/api/v1/transactions/{self.bill.pk}/images/{image.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.upload().status_code, 200)
        self.assertEqual(TransactionImage.objects.count(), 9)
        self.assertEqual(self.upload().status_code, 400)

    def test_limit_is_per_bill_not_per_user(self):
        self.fill(9)
        other_bill = Transaction.objects.create(
            user=self.user, account=self.account, transaction_type="income",
            amount="1", transaction_time=timezone.now(),
        )
        self.assertEqual(self.upload(other_bill).status_code, 200)

    def test_old_over_limit_records_are_preserved_but_cannot_add_more(self):
        # 模拟升级前已有10张记录，不执行清理或删除历史文件。
        TransactionImage.objects.bulk_create([
            TransactionImage(user=self.user, transaction=self.bill, image=f"legacy/{index}.png")
            for index in range(10)
        ])
        self.assertEqual(self.upload().status_code, 400)
        self.assertEqual(TransactionImage.objects.count(), 10)

    def test_five_megabyte_limit_still_applies(self):
        content = self.image_bytes + b"0" * (5 * 1024 * 1024)
        response = self.upload(content=content)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("5MB", response.data["message"])
        self.assertFalse(TransactionImage.objects.exists())

    def test_foreign_bill_cannot_be_uploaded_to(self):
        self.client.force_authenticate(user=self.other)
        response = self.upload()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TransactionImage.objects.exists())

    def test_deleted_bill_cannot_be_uploaded_to(self):
        self.bill.status = "deleted"
        self.bill.save(update_fields=["status"])
        self.assertEqual(self.upload().status_code, 400)

    def test_anonymous_upload_is_rejected(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.upload().status_code, 401)

    def test_deleted_bill_images_remain_readable_and_files_are_preserved(self):
        self.fill(2)
        url = f"/api/v1/transactions/{self.bill.pk}/images/"
        before = self.client.get(url).data["data"]
        image_paths = [Path(self.directory.name) / image.image.name for image in TransactionImage.objects.all()]
        self.assertEqual(self.client.delete(f"/api/v1/transactions/{self.bill.pk}/").status_code, 200)
        self.account.refresh_from_db()
        balance = self.account.balance
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"], before)
        self.assertTrue(all(path.is_file() for path in image_paths))
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, balance)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, "deleted")

    def test_deleted_bill_images_are_not_visible_to_other_users_or_anonymous(self):
        self.fill(1)
        self.bill.status = "deleted"
        self.bill.save(update_fields=["status"])
        url = f"/api/v1/transactions/{self.bill.pk}/images/"
        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.client.get(url).status_code, 400)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(url).status_code, 401)

    def test_deleted_bill_images_cannot_be_modified(self):
        self.fill(1)
        image = TransactionImage.objects.get(transaction=self.bill)
        self.bill.status = "deleted"
        self.bill.save(update_fields=["status"])
        self.assertEqual(self.upload().status_code, 400)
        self.assertEqual(self.client.delete(f"/api/v1/transactions/{self.bill.pk}/images/{image.pk}/").status_code, 400)
        self.assertTrue(TransactionImage.objects.filter(pk=image.pk).exists())
        self.assertTrue(Path(image.image.path).is_file())

    def test_deleted_bill_without_images_returns_empty_list(self):
        self.bill.status = "deleted"
        self.bill.save(update_fields=["status"])
        response = self.client.get(f"/api/v1/transactions/{self.bill.pk}/images/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"], [])

    def test_images_remain_readable_after_restore(self):
        from apps.categories.models import Category
        self.bill.category = Category.objects.create(user=self.user, name="餐饮", category_type="expense")
        self.bill.save(update_fields=["category"])
        self.fill(1)
        url = f"/api/v1/transactions/{self.bill.pk}/images/"
        before = self.client.get(url).data["data"]
        self.assertEqual(self.client.delete(f"/api/v1/transactions/{self.bill.pk}/").status_code, 200)
        response = self.client.post(f"/api/v1/transactions/{self.bill.pk}/restore/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get(url).data["data"], before)
