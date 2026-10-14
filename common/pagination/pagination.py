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

    def get_page_size(self, request):
        """
        分页优先级：请求参数 > 用户偏好 > 系统默认值。

        最大100条；用户显式请求非法分页数量时返回参数错误。
        """
        from apps.preferences.services import PreferenceService
        from rest_framework.exceptions import ValidationError

        value = request.query_params.get(self.page_size_query_param)
        if value is not None:
            try:
                page_size = int(value)
            except (TypeError, ValueError):
                raise ValidationError("page_size必须是1-100之间的整数")
            if page_size < 1 or page_size > self.max_page_size:
                raise ValidationError("page_size必须是1-100之间的整数")
            return page_size
        if request.user.is_authenticated:
            preference = PreferenceService.get_or_create_preference(request.user)
            return preference.page_size
        return self.page_size

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
