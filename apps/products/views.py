from rest_framework.views import APIView

from common.response import ApiResponse

from .serializers import (
    ProductCreateSerializer,
    ProductPriceCreateSerializer,
    ProductPriceRecordSerializer,
    ProductQuerySerializer,
    ProductSerializer,
    ProductUpdateSerializer,
)
from .services import ProductService


class ProductListCreateView(APIView):
    """
    商品列表 / 创建接口。

    GET：
        查询商品列表。

    POST：
        新增商品。
    """

    def get(
        self,
        request,
    ):
        """
        获取商品列表。
        """

        # ======================================
        # 查询参数校验
        # ======================================
        #
        # 注意：
        # 这里转成普通 dict，
        # 避免 QueryDict 对 BooleanField
        # 产生 HTML checkbox 兼容行为。
        # ======================================

        query_serializer = ProductQuerySerializer(data=(request.query_params.dict()))

        query_serializer.is_valid(raise_exception=True)

        # ======================================
        # 查询商品
        # ======================================

        products = ProductService.get_product_list(
            user=request.user,
            query_params=(query_serializer.validated_data),
        )

        # ======================================
        # 序列化
        # ======================================

        serializer = ProductSerializer(
            products,
            many=True,
        )

        return ApiResponse.success(
            message="获取商品列表成功",
            data=serializer.data,
        )

    def post(
        self,
        request,
    ):
        """
        新增商品。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = ProductCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 创建商品
        # ======================================

        product = ProductService.create_product(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回创建结果
        # ======================================

        response_serializer = ProductSerializer(product)

        return ApiResponse.success(
            message="新增商品成功",
            data=response_serializer.data,
        )


class ProductDetailView(APIView):
    """
    商品详情接口。

    GET：
        查询商品详情。

    PUT：
        修改商品。

    DELETE：
        删除商品。
    """

    def get(
        self,
        request,
        product_id,
    ):
        """
        查询商品详情。
        """

        # ======================================
        # 查询商品
        # ======================================

        product = ProductService.get_product_detail(
            user=request.user,
            product_id=product_id,
        )

        # ======================================
        # 序列化
        # ======================================

        serializer = ProductSerializer(product)

        return ApiResponse.success(
            message="获取商品详情成功",
            data=serializer.data,
        )

    def put(
        self,
        request,
        product_id,
    ):
        """
        修改商品。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = ProductUpdateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 修改商品
        # ======================================

        product = ProductService.update_product(
            user=request.user,
            product_id=product_id,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回修改结果
        # ======================================

        response_serializer = ProductSerializer(product)

        return ApiResponse.success(
            message="修改商品成功",
            data=response_serializer.data,
        )

    def delete(
        self,
        request,
        product_id,
    ):
        """
        删除商品。
        """

        ProductService.delete_product(
            user=request.user,
            product_id=product_id,
        )

        return ApiResponse.success(
            message="删除商品成功",
            data=None,
        )


class ProductPriceRecordListCreateView(APIView):
    """
    商品价格记录接口。

    GET：
        查询商品价格历史。

    POST：
        新增商品价格记录。
    """

    def post(
        self,
        request,
        product_id,
    ):
        """
        新增商品价格记录。
        """

        # ======================================
        # 参数校验
        # ======================================

        serializer = ProductPriceCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ======================================
        # 创建价格记录
        # ======================================

        record = ProductService.create_price_record(
            user=request.user,
            product_id=product_id,
            validated_data=(serializer.validated_data),
        )

        # ======================================
        # 返回结果
        # ======================================

        response_serializer = ProductPriceRecordSerializer(record)

        return ApiResponse.success(
            message="新增商品价格记录成功",
            data=response_serializer.data,
        )

    def get(
        self,
        request,
        product_id,
    ):
        """
        查询商品历史价格。
        """

        # ======================================
        # 查询历史
        # ======================================

        result = ProductService.get_price_records(
            user=request.user,
            product_id=product_id,
        )

        # ======================================
        # 商品信息
        # ======================================

        product_serializer = ProductSerializer(result["product"])

        # ======================================
        # 价格记录
        # ======================================

        record_serializer = ProductPriceRecordSerializer(
            result["records"],
            many=True,
        )

        return ApiResponse.success(
            message="获取商品价格历史成功",
            data={
                "product": (product_serializer.data),
                "latest_price": (result["latest_price"]),
                "lowest_price": (result["lowest_price"]),
                "highest_price": (result["highest_price"]),
                "record_count": (result["record_count"]),
                "records": (record_serializer.data),
            },
        )
