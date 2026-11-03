from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.dashboard.asset_services import AssetSnapshotService


class Command(BaseCommand):
    """
    初始化资产跟踪并结转已结束月份。

    可由每日计划任务调用；重复执行不覆盖历史快照。
    不接受历史日期参数，防止把当前余额错误标记为历史月末余额。
    """

    help = "初始化用户当月资产跟踪，并结转已跟踪的历史月份"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, default=None, help="只处理指定用户")

    def handle(self, *args, **options):
        users = get_user_model().objects.order_by("pk")
        if options["user_id"] is not None:
            users = users.filter(pk=options["user_id"])
            if not users.exists():
                raise CommandError("指定用户不存在")

        processed = 0
        closed_count = 0
        for user in users.iterator(chunk_size=200):
            closed_count += AssetSnapshotService.prepare_user(user)
            processed += 1

        self.stdout.write(
            self.style.SUCCESS(f"处理用户{processed}个，新结转月末快照{closed_count}条")
        )
