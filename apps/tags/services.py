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
    def get_tag_detail(user, tag_id: int):
        """查询当前用户的有效标签。"""
        tag = Tag.objects.filter(
            id=tag_id,
            user=user,
            is_deleted=False,
        ).first()

        if tag is None:
            raise BusinessException("标签不存在")

        return tag

    @staticmethod
    @transaction.atomic
    def update_tag(user, tag_id: int, validated_data: dict):
        """修改名称、颜色，并保留已有账单关联。"""
        tag = Tag.objects.select_for_update().filter(
            id=tag_id,
            user=user,
            is_deleted=False,
        ).first()

        if tag is None:
            raise BusinessException("标签不存在")

        if "name" in validated_data:
            name = validated_data["name"]
            exists = Tag.objects.filter(
                user=user,
                name=name,
                is_deleted=False,
            ).exclude(id=tag.id).exists()
            if exists:
                raise BusinessException("该标签已存在")

        update_fields = []
        for field in ("name", "color"):
            if field in validated_data:
                setattr(tag, field, validated_data[field])
                update_fields.append(field)

        if update_fields:
            tag.save(update_fields=[*update_fields, "updated_at"])

        return tag

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
