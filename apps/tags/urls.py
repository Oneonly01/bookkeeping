from django.urls import path

from .views import (
    TagDetailView,
    TagListCreateView,
)

urlpatterns = [
    # ==========================================
    # 标签列表 / 新增标签
    # ==========================================
    # GET：
    # 获取当前用户的全部可用标签。
    #
    # POST：
    # 新增一个标签。
    #
    # 说明：
    # 1. 标签仅属于当前用户；
    # 2. 标签名称不能重复；
    # 3. 已逻辑删除的标签不会出现在列表中。
    path(
        "",
        TagListCreateView.as_view(),
        name="tag-list-create",
    ),
    # ==========================================
    # 删除标签
    # ==========================================
    # DELETE：
    # 逻辑删除指定标签。
    #
    # 说明：
    # 1. 标签必须属于当前用户；
    # 2. 删除后不能再用于新增或修改账单；
    # 3. 历史账单中的标签关联仍然保留；
    # 4. 已删除标签不会继续返回给前端。
    path(
        "<int:tag_id>/",
        TagDetailView.as_view(),
        name="tag-detail",
    ),
]
