import hashlib
import json
import re
from functools import wraps

from django.db import transaction
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from common.exceptions import BusinessException


class IdempotencyConflict(BusinessException):
    """同一个请求键不能用于不同操作或不同参数。"""

    status_code = 409


def idempotent_request(view_method):
    """
    金额操作重复提交保护。

    规则：
    1. 前端为一次操作生成 Idempotency-Key，重试沿用原键；
    2. 用户、请求键、请求内容共同确定首次成功结果；
    3. 相同键和内容返回原响应，不重复执行余额变更；
    4. 相同键用于不同接口或参数时返回409；
    5. 失败请求不占用键，可以修正条件后重试；
    6. 旧客户端未传请求键时沿用原行为。

    数据库唯一约束处理同时插入，行锁处理同时重试。
    凭证不自动过期，避免旧请求重试后再次扣款。
    """

    @wraps(view_method)
    def wrapped(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if key is None:
            return view_method(self, request, *args, **kwargs)

        # ======================================
        # 请求键 / 请求摘要
        # ======================================
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", key):
            raise BusinessException("Idempotency-Key格式不正确")

        content = {
            "method": request.method,
            "path": request.path,
            "data": request.data,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                content,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        # 延迟导入，避免模型加载阶段产生循环依赖。
        from apps.transactions.models import ApiIdempotencyRecord

        # ======================================
        # 凭证和业务变更使用同一个事务
        # ======================================
        with transaction.atomic():
            record, created = ApiIdempotencyRecord.objects.get_or_create(
                user=request.user,
                request_key=key,
                defaults={"fingerprint": fingerprint},
            )
            record = ApiIdempotencyRecord.objects.select_for_update().get(
                pk=record.pk,
            )
            if record.fingerprint != fingerprint:
                raise IdempotencyConflict("请求键已用于其他操作，请使用新的Idempotency-Key")

            if not created and record.response_data is not None:
                response = Response(
                    record.response_data,
                    status=record.status_code,
                )
                response["Idempotency-Replayed"] = "true"
                return response

            response = view_method(self, request, *args, **kwargs)
            if response.status_code >= 400:
                transaction.set_rollback(True)
                return response

            # 使用实际JSON渲染结果保存响应，兼容Decimal和日期字段。
            record.response_data = json.loads(
                JSONRenderer().render(response.data),
            )
            record.status_code = response.status_code
            record.save(update_fields=["response_data", "status_code"])
            response["Idempotency-Replayed"] = "false"
            return response

    return wrapped
