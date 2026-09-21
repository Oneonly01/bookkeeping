from typing import Any

from rest_framework import status
from rest_framework.response import Response


class ApiResponse:
    """
    API 统一响应工具类。

    所有接口统一返回：

    {
        "code": 0,
        "message": "操作成功",
        "data": {}
    }
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        code: int = 200,
        http_status: int = status.HTTP_200_OK,
    ) -> Response:
        """
        返回成功响应。
        """

        return Response(
            {
                "code": code,
                "message": message,
                "data": data,
            },
            status=http_status,
        )

    @staticmethod
    def error(
        message: str = "操作失败",
        code: int = 1,
        data: Any = None,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
        """
        返回失败响应。
        """

        return Response(
            {
                "code": code,
                "message": message,
                "data": data,
            },
            status=http_status,
        )
