from django.db.models import Q
from django.db import transaction

from common.exceptions.business import BusinessException

from .models import Category


class CategoryService:
    """
    分类业务服务。
    """

    @staticmethod
    def get_category_list(
        user,
        category_type=None,
    ):
        """
        获取当前用户可用分类。

        包含：
        1. 系统默认分类；
        2. 当前用户自定义分类。

        :param user:
            当前登录用户。

        :param category_type:
            expense / income，可选。

        :return:
            QuerySet
        """

        # 查询：
        #
        # 系统分类：
        # user IS NULL + is_system=True
        #
        # 或者：
        #
        # 当前用户自己的分类。
        system_category_filter = Q(
            user__isnull=True,
            is_system=True,
        )

        user_category_filter = Q(
            user=user,
            is_system=False,
        )

        queryset = Category.objects.filter(
            system_category_filter | user_category_filter,
            is_deleted=False,
            is_active=True,
        )

        # 如果传入分类类型，
        # 则进一步过滤。
        if category_type:
            queryset = queryset.filter(category_type=category_type)

        # 系统分类优先，
        # 然后根据排序值排序。
        queryset = queryset.order_by(
            "-is_system",
            "sort_order",
            "id",
        )

        return queryset

    @staticmethod
    @transaction.atomic
    def create_category(
        user,
        validated_data: dict,
    ) -> Category:
        """
        创建当前用户自定义分类。

        用户创建的分类：
        is_system 永远为 False。
        """

        category = Category.objects.create(
            user=user,
            name=validated_data["name"],
            category_type=(validated_data["category_type"]),
            icon=validated_data.get(
                "icon",
                "",
            ),
            color=validated_data.get(
                "color",
                "",
            ),
            sort_order=validated_data.get(
                "sort_order",
                0,
            ),
            is_system=False,
        )

        return category

    @staticmethod
    def get_category_detail(
        user,
        category_id: int,
    ) -> Category:
        """
        获取分类详情。

        可以查询：
        1. 系统默认分类；
        2. 当前用户自己的自定义分类。
        """

        try:
            # 允许访问：
            # 系统分类
            # 或当前用户自己的分类。
            category_filter = Q(
                id=category_id,
                user__isnull=True,
                is_system=True,
            ) | Q(
                id=category_id,
                user=user,
                is_system=False,
            )

            category = Category.objects.filter(
                category_filter,
                is_deleted=False,
            ).get()

        except Category.DoesNotExist:
            raise BusinessException("分类不存在")

        return category

    @staticmethod
    @transaction.atomic
    def update_category(
        user,
        category_id: int,
        validated_data: dict,
    ) -> Category:
        """
        修改用户自定义分类。

        系统分类禁止修改。
        """

        category = CategoryService.get_category_detail(
            user=user,
            category_id=category_id,
        )

        # 系统分类禁止修改。
        if category.is_system:
            raise BusinessException("系统分类不允许修改")

        # 再做一次用户归属校验。
        if category.user_id != user.id:
            raise BusinessException("无权修改该分类")

        # 修改名称。
        if "name" in validated_data:
            category.name = validated_data["name"]

        # 修改分类类型。
        if "category_type" in validated_data:
            category.category_type = validated_data["category_type"]

        # 修改图标。
        if "icon" in validated_data:
            category.icon = validated_data["icon"]

        # 修改颜色。
        if "color" in validated_data:
            category.color = validated_data["color"]

        # 修改排序。
        if "sort_order" in validated_data:
            category.sort_order = validated_data["sort_order"]

        # 修改启用状态。
        if "is_active" in validated_data:
            category.is_active = validated_data["is_active"]

        # 保存。
        category.save()

        return category

    @staticmethod
    @transaction.atomic
    def delete_category(
        user,
        category_id: int,
    ) -> None:
        """
        逻辑删除用户自定义分类。

        系统分类禁止删除。
        """

        category = CategoryService.get_category_detail(
            user=user,
            category_id=category_id,
        )

        # 系统分类不允许删除。
        if category.is_system:
            raise BusinessException("系统分类不允许删除")

        # 只能删除自己的分类。
        if category.user_id != user.id:
            raise BusinessException("无权删除该分类")

        # 逻辑删除。
        category.is_deleted = True

        # 删除后同时停用。
        category.is_active = False

        # 保存状态。
        category.save(
            update_fields=[
                "is_deleted",
                "is_active",
                "updated_at",
            ]
        )
