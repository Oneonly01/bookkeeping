from rest_framework.exceptions import APIException
from rest_framework import status


class BusinessException(APIException):
    """
    通用业务异常。

    例如：
    - 账户余额不足
    - 账户不存在
    - 分类不可用
    - 存钱目标已完成
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "业务处理失败"
    default_code = "business_error"

    def __init__(
        self,
        detail=None,
        code=None,
    ):
        super().__init__(
            detail=detail or self.default_detail,
            code=code or self.default_code,
        )
