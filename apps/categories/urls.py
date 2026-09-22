from django.urls import path

from .views import CategoryDetailView, CategoryListCreateView

app_name = "categories"


urlpatterns = [
    # 分类列表 / 新增。
    path(
        "",
        CategoryListCreateView.as_view(),
        name="category-list-create",
    ),
    # 分类详情 / 修改 / 删除。
    path(
        "<int:category_id>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
]
