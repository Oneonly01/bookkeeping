# from rest_framework import status
from rest_framework_simplejwt.exceptions import (
    AuthenticationFailed,
    InvalidToken,
    TokenError,
)
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    DRF 全局异常处理器。

    将 DRF 默认错误响应统一转换为：

    {
        "code": xxx,
        "message": "错误信息",
        "data": null
    }
    """

    response = exception_handler(
        exc,
        context,
    )

    # DRF 无法处理的异常交给 Django，
    # 不在这里强行吞掉。
    if response is None:
        return None

    message = "请求失败"

    # JWT Token 无效、过期、已撤销等认证异常。

    if isinstance(
        exc,
        (
            InvalidToken,  # type: ignore
            AuthenticationFailed,
            TokenError,
        ),
    ):
        message = "登录状态已失效，请重新登录"
    # 参数校验异常
    if isinstance(exc, ValidationError):
        message = _extract_validation_message(response.data)

    elif isinstance(response.data, dict):
        detail = response.data.get("detail")

        if detail:
            message = str(detail)

    return response.__class__(
        {
            "code": response.status_code,
            "message": message,
            "data": None,
        },
        status=response.status_code,
    )


def _extract_validation_message(data) -> str:
    """
    从 Serializer ValidationError 中提取
    第一条可读错误信息。
    """

    if isinstance(data, dict):
        for field, messages in data.items():

            if isinstance(messages, list) and messages:
                return f"{field}: {messages[0]}"

            return f"{field}: {messages}"

    if isinstance(data, list) and data:
        return str(data[0])

    return str(data)
