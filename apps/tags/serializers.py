from rest_framework import serializers

from .models import Tag


class TagCreateSerializer(serializers.Serializer):
    """
    创建标签请求序列化器。
    """

    # ==========================================
    # 标签名称
    # ==========================================

    name = serializers.CharField(
        max_length=50,
    )

    # ==========================================
    # 标签颜色
    # ==========================================

    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_name(
        self,
        value,
    ):
        """
        标签名称不能为空字符串。
        """

        value = value.strip()

        if not value:
            raise serializers.ValidationError("标签名称不能为空")

        return value


class TagUpdateSerializer(serializers.Serializer):
    """修改标签；未传字段保持原值。"""

    name = serializers.CharField(
        max_length=50,
        required=False,
        trim_whitespace=True,
        error_messages={
            "blank": "标签名称不能为空",
            "max_length": "标签名称不能超过50个字符",
        },
    )

    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "max_length": "标签颜色不能超过20个字符",
        },
    )


class TagSerializer(serializers.ModelSerializer):
    """
    标签响应序列化器。
    """

    class Meta:
        model = Tag

        fields = [
            "id",
            "name",
            "color",
            "created_at",
            "updated_at",
        ]
