from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.transactions.models import RecurringTransaction
from apps.transactions.recurring_services import RecurringTransactionService


class Command(BaseCommand):
    """
    执行到期周期账单。

    由系统计划任务定时调用，重复启动不会重复生成同一周期。
    业务失败记录在模板last_error中，并返回非零退出码供监控识别。
    """

    help = "执行到期周期账单；余额不足时保留周期待重试"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=date.fromisoformat, default=None)
        parser.add_argument("--limit", type=int, default=1000)

    def handle(self, *args, **options):
        as_of = options["date"] or timezone.localdate()
        if as_of > timezone.localdate():
            raise CommandError("不能提前执行未来周期")
        limit = options["limit"]
        if not 1 <= limit <= 10000:
            raise CommandError("limit必须在1-10000之间")
        # ======================================
        # 只处理启用、未删除、已经到期的模板
        # ======================================
        templates = list(RecurringTransaction.objects.filter(
            is_active=True, is_deleted=False, next_date__lte=as_of,
        ).select_related("user").order_by("next_date", "id")[:limit])
        created_count = 0
        errors = []
        for template in templates:
            result = RecurringTransactionService.execute_due(
                template.user, template.id, as_of=as_of,
            )
            created_count += len(result["created_ids"])
            if result["error"]:
                errors.append(f"模板{template.id}: {result['error']}")
            elif result["more_due"]:
                self.stdout.write(f"模板{template.id}仍有到期周期，请再次执行")
        self.stdout.write(f"处理模板{len(templates)}个，生成账单{created_count}条")
        if errors:
            raise CommandError("；".join(errors))
