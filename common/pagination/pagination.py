from rest_framework.pagination import PageNumberPagination

from common.response import ApiResponse


class StandardPagination(PageNumberPagination):
    """
    系统统一分页规则。
    """

    # 默认每页20条
    page_size = 20

    # 前端可以传：
    # ?page_size=50
    page_size_query_param = "page_size"

    # 单次最多100条
    max_page_size = 100

    def get_paginated_response(self, data):
        return ApiResponse.success(
            data={
                "list": data,
                "pagination": {
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total": self.page.paginator.count,
                    "pages": (self.page.paginator.num_pages),
                },
            }
        )
