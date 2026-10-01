from django.utils import timezone
from django.db import transaction
from django.db.models import Max, Min, Q

from common.exceptions.business import BusinessException

from .models import Product, ProductPriceRecord


class ProductService:
    """
    商品业务服务类。
    """

    @staticmethod
    @transaction.atomic
    def create_product(
        user,
        validated_data: dict,
    ):
        """
        创建商品。

        业务规则：

        1. 自动绑定当前登录用户；
        2. 创建后默认启用；
        3. 默认未删除；
        4. 同一用户下，
        相同名称 + 品牌 + 型号的未删除商品
        不允许重复创建；
        5. is_active 不参与重复判断，
        因为停用不等于删除。
        """

        # ======================================
        # 获取商品关键字段
        # ======================================

        name = validated_data["name"]

        brand = validated_data.get(
            "brand",
            "",
        )

        model_name = validated_data.get(
            "model_name",
            "",
        )

        # ======================================
        # 重复商品检查
        # ======================================
        #
        # 注意：
        # 这里只判断 is_deleted=False，
        # 不判断 is_active。
        #
        # 原因：
        # is_active=False 只表示商品被停用，
        # 商品数据仍然存在，
        # 不应该因此允许再次新增一模一样的商品。
        # ======================================

        exists = Product.objects.filter(
            user=user,
            name=name,
            brand=brand,
            model_name=model_name,
            is_deleted=False,
        ).exists()

        if exists:
            raise BusinessException("该商品已存在")

        # ======================================
        # 创建商品
        # ======================================

        product = Product.objects.create(
            # 当前登录用户。
            user=user,
            # 商品名称。
            name=name,
            # 品牌。
            brand=brand,
            # 型号。
            model_name=model_name,
            # 商品分类。
            category=validated_data.get(
                "category",
                "",
            ),
            # 商品链接。
            product_url=validated_data.get(
                "product_url",
                "",
            ),
            # 商品图片。
            image_url=validated_data.get(
                "image_url",
                "",
            ),
            # 备注。
            note=validated_data.get(
                "note",
                "",
            ),
            # 新增商品默认启用。
            is_active=True,
            # 新增商品默认未删除。
            is_deleted=False,
        )

        return product

    @staticmethod
    def get_product_list(
        user,
        query_params: dict,
    ):
        """
        获取当前用户商品列表。

        支持：

        keyword
        category
        brand
        is_active
        """

        products = Product.objects.filter(
            user=user,
            is_deleted=False,
        )

        # ======================================
        # 关键字搜索
        # ======================================

        keyword = query_params.get("keyword")

        if keyword:
            products = products.filter(
                Q(name__icontains=keyword)
                | Q(brand__icontains=keyword)
                | Q(model_name__icontains=keyword)
                | Q(note__icontains=keyword)
            )

        # ======================================
        # 分类筛选
        # ======================================

        category = query_params.get("category")

        if category:
            products = products.filter(category=category)

        # ======================================
        # 品牌筛选
        # ======================================

        brand = query_params.get("brand")

        if brand:
            products = products.filter(brand=brand)

        # ======================================
        # 启用状态筛选
        # ======================================

        is_active = query_params.get("is_active")

        if is_active is not None:
            products = products.filter(is_active=is_active)

        return products.order_by(
            "-created_at",
            "-id",
        )

    @staticmethod
    def get_product_detail(
        user,
        product_id: int,
    ):
        """
        获取商品详情。

        业务规则：

        1. 只能查询当前登录用户自己的商品；
        2. 已逻辑删除商品不可查询。
        """

        product = Product.objects.filter(
            id=product_id,
            user=user,
            is_deleted=False,
        ).first()

        if product is None:
            raise BusinessException("商品不存在")

        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        user,
        product_id: int,
        validated_data: dict,
    ):
        """
        修改商品。

        使用 select_for_update 锁定当前商品，
        避免多个请求同时修改同一条数据。
        """

        # ======================================
        # 查询并锁定商品
        # ======================================

        product = (
            Product.objects.select_for_update()
            .filter(
                id=product_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if product is None:
            raise BusinessException("商品不存在")

        # ======================================
        # 商品名称
        # ======================================

        if "name" in validated_data:
            product.name = validated_data["name"]

        # ======================================
        # 品牌
        # ======================================

        if "brand" in validated_data:
            product.brand = validated_data["brand"]

        # ======================================
        # 型号
        # ======================================

        if "model_name" in validated_data:
            product.model_name = validated_data["model_name"]

        # ======================================
        # 分类
        # ======================================

        if "category" in validated_data:
            product.category = validated_data["category"]

        # ======================================
        # 商品链接
        # ======================================

        if "product_url" in validated_data:
            product.product_url = validated_data["product_url"]

        # ======================================
        # 商品图片
        # ======================================

        if "image_url" in validated_data:
            product.image_url = validated_data["image_url"]

        # ======================================
        # 备注
        # ======================================

        if "note" in validated_data:
            product.note = validated_data["note"]

        # ======================================
        # 启用状态
        # ======================================

        if "is_active" in validated_data:
            product.is_active = validated_data["is_active"]

        # ======================================
        # 保存
        # ======================================

        product.save(
            update_fields=[
                "name",
                "brand",
                "model_name",
                "category",
                "product_url",
                "image_url",
                "note",
                "is_active",
                "updated_at",
            ]
        )

        return product

    @staticmethod
    @transaction.atomic
    def delete_product(
        user,
        product_id: int,
    ):
        """
        删除商品。

        使用逻辑删除：

        is_deleted = True
        is_active = False

        不直接物理删除，
        后续价格历史仍然可以保留。
        """

        # ======================================
        # 查询并锁定商品
        # ======================================

        product = (
            Product.objects.select_for_update()
            .filter(
                id=product_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if product is None:
            raise BusinessException("商品不存在")

        # ======================================
        # 逻辑删除
        # ======================================

        product.is_deleted = True
        product.is_active = False

        product.save(
            update_fields=[
                "is_deleted",
                "is_active",
                "updated_at",
            ]
        )

        return product

    @staticmethod
    @transaction.atomic
    def create_price_record(
        user,
        product_id: int,
        validated_data: dict,
    ):
        """
        新增商品价格记录。

        业务规则：

        1. 只能给当前用户自己的商品添加价格；
        2. 已逻辑删除商品不能添加价格；
        3. 停用商品仍允许补录历史价格；
        4. 价格必须大于 0；
        5. 未传 recorded_date 时默认今天。
        """

        # ======================================
        # 查询并锁定商品
        # ======================================

        product = (
            Product.objects.select_for_update()
            .filter(
                id=product_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if product is None:
            raise BusinessException("商品不存在")

        # ======================================
        # 创建价格记录
        # ======================================

        record = ProductPriceRecord.objects.create(
            user=user,
            product=product,
            price=validated_data["price"],
            platform=validated_data.get(
                "platform",
                "",
            ),
            recorded_date=(validated_data.get("recorded_date") or timezone.localdate()),
            note=validated_data.get(
                "note",
                "",
            ),
        )

        return record

    @staticmethod
    def get_price_records(
        user,
        product_id: int,
    ):
        """
        查询商品价格历史。

        返回：

        1. 商品信息；
        2. 最新价格；
        3. 历史最低价；
        4. 历史最高价；
        5. 价格记录数量；
        6. 全部价格记录。
        """

        # ======================================
        # 验证商品是否存在以及归属
        # ======================================

        product = Product.objects.filter(
            id=product_id,
            user=user,
            is_deleted=False,
        ).first()

        if product is None:
            raise BusinessException("商品不存在")

        # ======================================
        # 查询历史价格
        # ======================================

        records = ProductPriceRecord.objects.filter(
            user=user,
            product=product,
        ).order_by(
            "-recorded_date",
            "-id",
        )

        # ======================================
        # 最高价 / 最低价
        # ======================================

        summary = records.aggregate(
            lowest_price=Min("price"),
            highest_price=Max("price"),
        )

        lowest_price = summary["lowest_price"]

        highest_price = summary["highest_price"]

        # ======================================
        # 最新价格
        # ======================================

        latest_record = records.first()

        latest_price = latest_record.price if latest_record else None

        # ======================================
        # 返回结果
        # ======================================

        return {
            "product": product,
            "latest_price": (
                f"{latest_price:.2f}" if latest_price is not None else None
            ),
            "lowest_price": (
                f"{lowest_price:.2f}" if lowest_price is not None else None
            ),
            "highest_price": (
                f"{highest_price:.2f}" if highest_price is not None else None
            ),
            "record_count": (records.count()),
            "records": records,
        }
