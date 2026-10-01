from django.db import transaction

from common.exceptions import BusinessException

from .models import Tag


class TagService:
    """
    标签业务服务。
    """

    @staticmethod
    @transaction.atomic
    def create_tag(
        user,
        validated_data: dict,
    ):
        """
        创建账单标签。

        同一用户下，
        不允许存在同名且未删除标签。
        """

        name = validated_data["name"]

        # ======================================
        # 重复标签检查
        # ======================================

        exists = Tag.objects.filter(
            user=user,
            name=name,
            is_deleted=False,
        ).exists()

        if exists:
            raise BusinessException("该标签已存在")

        # ======================================
        # 创建标签
        # ======================================

        tag = Tag.objects.create(
            user=user,
            name=name,
            color=validated_data.get(
                "color",
                "",
            ),
            is_deleted=False,
        )

        return tag

    @staticmethod
    def get_tag_list(
        user,
    ):
        """
        查询当前用户标签列表。
        """

        return Tag.objects.filter(
            user=user,
            is_deleted=False,
        ).order_by(
            "name",
            "id",
        )

    @staticmethod
    @transaction.atomic
    def delete_tag(
        user,
        tag_id: int,
    ):
        """
        删除标签。

        使用逻辑删除。
        """

        tag = (
            Tag.objects.select_for_update()
            .filter(
                id=tag_id,
                user=user,
                is_deleted=False,
            )
            .first()
        )

        if tag is None:
            raise BusinessException("标签不存在")

        tag.is_deleted = True

        tag.save(
            update_fields=[
                "is_deleted",
                "updated_at",
            ]
        )

        return tag
