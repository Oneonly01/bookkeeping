from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.preferences.services import PreferenceService
from apps.tags.models import Tag
from common.exceptions import BusinessException

from .models import RecurringExecution, RecurringTransaction
from .services import TransactionService


class RecurringTransactionService:
    """
    周期账单业务服务。

    所有金额变更复用普通账单业务，模板和执行记录负责调度去重。
    使用系统时区的计划日期00:00记账，不提前执行未来周期。
    """

    @staticmethod
    def validate_references(user, data):
        """模板只允许使用当前用户有效账户、有效分类和有效标签。"""
        account_id = data.get("account_id")
        if account_id is None:
            account_id = PreferenceService.get_default_account(user).id
        account = Account.objects.filter(
            id=account_id, user=user, is_deleted=False, is_active=True,
        ).first()
        if account is None:
            raise BusinessException("账户不存在或已停用")
        category = Category.objects.filter(
            Q(user=user, is_system=False) | Q(user__isnull=True, is_system=True),
            id=data["category_id"], is_deleted=False, is_active=True,
        ).first()
        if category is None:
            raise BusinessException("分类不存在")
        if category.category_type != data["transaction_type"]:
            raise BusinessException("分类类型与账单类型不一致")
        tag_ids = list(dict.fromkeys(data.get("tag_ids", [])))
        tags = list(Tag.objects.filter(id__in=tag_ids, user=user, is_deleted=False))
        if len(tags) != len(tag_ids):
            raise BusinessException("存在无效标签")
        return account, category, tags

    @staticmethod
    def get_template(
        user,
        template_id,
        lock=False,
    ):
        queryset = RecurringTransaction.objects.filter(
            id=template_id, user=user, is_deleted=False,
        )
        if lock:
            queryset = queryset.select_for_update()
        template = queryset.first()
        if template is None:
            raise BusinessException("周期账单模板不存在")
        return template

    @staticmethod
    @transaction.atomic
    def create_template(user, validated_data):
        # ======================================
        # 关联校验 / 保存模板
        # ======================================
        data = validated_data.copy()
        account, category, tags = RecurringTransactionService.validate_references(user, data)
        data.pop("account_id", None)
        data.pop("category_id")
        data.pop("tag_ids", None)
        template = RecurringTransaction.objects.create(
            user=user,
            account=account,
            category=category,
            next_date=data["start_date"],
            **data,
        )
        template.tags.set(tags)
        return template

    @staticmethod
    @transaction.atomic
    def update_template(
        user,
        template_id,
        validated_data,
    ):
        """
        修改模板，仅影响之后生成的账单。

        已有执行记录时禁止改起始日、频率和间隔；
        需要新计划时创建新模板，避免重新解释历史周期。
        """
        template = RecurringTransactionService.get_template(user, template_id, lock=True)
        data = validated_data.copy()
        schedule_changed = any(
            field in data and data[field] != getattr(template, field)
            for field in ("start_date", "frequency", "interval")
        )
        if schedule_changed and template.executions.exists():
            raise BusinessException("模板已有执行记录，修改周期请创建新模板")
        merged = {
            "account_id": template.account_id,
            "category_id": template.category_id,
            "transaction_type": template.transaction_type,
            "tag_ids": list(template.tags.values_list("id", flat=True)),
            **data,
        }
        account, category, tags = RecurringTransactionService.validate_references(user, merged)
        for field in ("account_id", "category_id", "tag_ids"):
            data.pop(field, None)
        for field, value in data.items():
            setattr(template, field, value)
        template.account = account
        template.category = category
        if schedule_changed:
            template.next_date = template.start_date
        if template.end_date and template.end_date < template.next_date:
            template.is_active = False
        template.last_error = ""
        template.save()
        template.tags.set(tags)
        return template

    @staticmethod
    @transaction.atomic
    def delete_template(user, template_id):
        """逻辑删除模板，保留已生成账单和历史执行记录。"""
        template = RecurringTransactionService.get_template(user, template_id, lock=True)
        template.is_deleted = True
        template.is_active = False
        template.save(update_fields=["is_deleted", "is_active", "updated_at"])

    @staticmethod
    def get_next_date(template, current_date):
        """
        根据起始日期计算下一周期。

        每月31日：1月31日、2月最后一天、3月31日。
        每年2月29日：非闰年取2月28日，闰年恢复2月29日。
        """
        if template.frequency == RecurringTransaction.Frequency.DAILY:
            return current_date + timedelta(days=template.interval)
        if template.frequency == RecurringTransaction.Frequency.WEEKLY:
            return current_date + timedelta(weeks=template.interval)
        anchor = template.start_date
        if template.frequency == RecurringTransaction.Frequency.MONTHLY:
            total_months = current_date.year * 12 + current_date.month - 1 + template.interval
            year, month_zero = divmod(total_months, 12)
            month = month_zero + 1
        else:
            year, month = current_date.year + template.interval, anchor.month
        day = min(anchor.day, monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    @transaction.atomic
    def execute_due(
        user,
        template_id,
        as_of=None,
        limit=100,
    ):
        """
        执行一个模板截至今天的到期周期。

        1. 锁定模板，多个任务不会同时生成同一周期；
        2. 成功账单、执行记录和下次日期一起提交；
        3. 单个失败周期回滚，保留原计划日期供修复后重试；
        4. 单次最多100个周期，积压数据可以分批补记；
        5. 余额不足不会跳过该周期，也不会继续生成后续周期。
        """
        as_of = as_of or timezone.localdate()
        if as_of > timezone.localdate():
            raise BusinessException("不能提前执行未来周期")
        if limit < 1 or limit > 100:
            raise BusinessException("执行数量必须在1-100之间")
        template = RecurringTransactionService.get_template(user, template_id, lock=True)
        created_ids = []
        error = ""
        if not template.is_active:
            return {"created_ids": [], "error": "", "more_due": False}

        # ======================================
        # 按计划顺序补记，单周期使用事务保存点
        # ======================================
        for _ in range(limit):
            scheduled = template.next_date
            if scheduled > as_of:
                break
            if template.end_date and scheduled > template.end_date:
                template.is_active = False
                break
            try:
                with transaction.atomic():
                    # 提前计算下次日期，任何异常都发生在扣款之前。
                    next_date = RecurringTransactionService.get_next_date(template, scheduled)
                    if not template.executions.filter(scheduled_date=scheduled).exists():
                        record = TransactionService.create_transaction(
                            user=user,
                            validated_data={
                                "account_id": template.account_id,
                                "category_id": template.category_id,
                                "tag_ids": list(template.tags.values_list("id", flat=True)),
                                "transaction_type": template.transaction_type,
                                "amount": template.amount,
                                "merchant": template.merchant,
                                "note": template.note,
                                "transaction_time": timezone.make_aware(datetime.combine(scheduled, time.min)),
                            },
                        )
                        RecurringExecution.objects.create(
                            template=template,
                            scheduled_date=scheduled,
                            transaction=record,
                        )
                        created_ids.append(record.id)
            except BusinessException as exc:
                error = str(exc.detail)
                break
            template.next_date = next_date
            template.last_error = ""
            if template.end_date and next_date > template.end_date:
                template.is_active = False
                break

        # 保存可追踪错误；失败周期的next_date不推进。
        template.last_error = error
        template.save(update_fields=["next_date", "last_error", "is_active", "updated_at"])
        return {
            "created_ids": created_ids,
            "error": error,
            "more_due": template.is_active and template.next_date <= as_of,
        }
