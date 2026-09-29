"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    # 用户与认证模块。
    path(
        "api/v1/",
        include("apps.users.urls"),
    ),
    # 账户模块接口。
    path(
        "api/v1/accounts/",
        include("apps.accounts.urls"),
    ),
    # 分类模块接口
    path(
        "api/v1/categories/",
        include("apps.categories.urls"),
    ),
    # 账单模块接口
    path(
        "api/v1/transactions/",
        include("apps.transactions.urls"),
    ),
    # 预算模块。
    path(
        "api/v1/budgets/",
        include("apps.budgets.urls"),
    ),
    # 存钱罐模块
    path(
        "api/v1/savings/",
        include("apps.savings.urls"),
    ),
    # 首页模块
    path(
        "api/v1/dashboard/",
        include("apps.dashboard.urls"),
    ),
]
# 开发环境下由 Django 提供媒体文件访问。
#
# 生产环境不能使用这种方式，
# 后续部署时交给 Nginx。
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
