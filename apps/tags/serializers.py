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
