from rest_framework.views import APIView

from common.response import ApiResponse

from .services import DashboardService


class DashboardSummaryView(APIView):
    """
    首页 Dashboard 汇总接口。
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户首页汇总数据。
        """

        # ======================================
        # 调用 Dashboard Service
        # ======================================

        summary = DashboardService.get_summary(
            user=request.user,
        )

        # ======================================
        # 返回统一响应
        # ======================================

        return ApiResponse.success(
            message="获取首页数据成功",
            data=summary,
        )
