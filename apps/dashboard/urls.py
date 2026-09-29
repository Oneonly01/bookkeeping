from django.urls import path

from .views import DashboardSummaryView

urlpatterns = [
    # ==========================================
    # 首页数据汇总
    # ==========================================
    path(
        "summary/",
        DashboardSummaryView.as_view(),
        name="dashboard-summary",
    ),
]
