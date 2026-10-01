from django.urls import path

from .views import (
    ProductDetailView,
    ProductListCreateView,
    ProductPriceRecordListCreateView,
)

urlpatterns = [
    # ==========================================
    # 商品列表 / 新增
    # ==========================================
    path(
        "",
        ProductListCreateView.as_view(),
        name="product-list-create",
    ),
    # ==========================================
    # 商品详情 / 修改 / 删除
    # ==========================================
    path(
        "<int:product_id>/",
        ProductDetailView.as_view(),
        name="product-detail",
    ),
    # ==========================================
    # 商品价格历史 / 新增价格记录
    # ==========================================
    path(
        "<int:product_id>/prices/",
        ProductPriceRecordListCreateView.as_view(),
        name="product-price-list-create",
    ),
]
