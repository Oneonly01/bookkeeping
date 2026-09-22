from rest_framework import serializers

from .models import Category


class CategoryCreateSerializer(serializers.Serializer):
    """
    新增自定义分类参数序列化器。
    """

    # 分类名称。
    name = serializers.CharField(
        max_length=50,
        required=True,
        trim_whitespace=True,
        error_messages={
            "required": "请输入分类名称",
            "blank": "分类名称不能为空",
            "max_length": ("分类名称长度不能超过50个字符"),
        },
    )

    # 分类类型。
    category_type = serializers.ChoiceField(
        choices=Category.CategoryType.choices,
        required=True,
        error_messages={
            "required": "请选择分类类型",
            "invalid_choice": "分类类型不正确",
        },
    )

    # 图标。
    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    # 颜色。
    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
    )

    # 排序值。
    sort_order = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    def validate(self, attrs):
        """
        校验当前用户是否存在同名同类型分类。
        """

        # 获取 request。
        request = self.context.get("request")

        # 获取当前登录用户。
        user = request.user

        # 获取分类名称。
        name = attrs["name"]

        # 获取分类类型。
        category_type = attrs["category_type"]

        # 当前用户不能创建同名同类型分类。
        exists = Category.objects.filter(
            user=user,
            name=name,
            category_type=category_type,
            is_deleted=False,
        ).exists()

        if exists:
            raise serializers.ValidationError("已存在同名分类")

        return attrs


class CategorySerializer(serializers.ModelSerializer):
    """
    分类返回序列化器。
    """

    # 分类类型中文名称。
    category_type_display = serializers.CharField(
        source="get_category_type_display",
        read_only=True,
    )

    class Meta:
        # 对应模型。
        model = Category

        # 返回字段。
        fields = [
            "id",
            "name",
            "category_type",
            "category_type_display",
            "icon",
            "color",
            "sort_order",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
        ]

        # 所有字段只用于返回。
        read_only_fields = fields


class CategoryUpdateSerializer(serializers.Serializer):
    """
    修改用户自定义分类参数序列化器。
    """

    # 分类名称。
    name = serializers.CharField(
        max_length=50,
        required=False,
        trim_whitespace=True,
        error_messages={
            "blank": "分类名称不能为空",
            "max_length": "分类名称长度不能超过50个字符",
        },
    )

    # 分类类型。
    category_type = serializers.ChoiceField(
        choices=Category.CategoryType.choices,
        required=False,
        error_messages={
            "invalid_choice": "分类类型不正确",
        },
    )

    # 图标。
    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    # 颜色。
    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    # 排序值。
    sort_order = serializers.IntegerField(
        min_value=0,
        required=False,
    )

    # 是否启用。
    is_active = serializers.BooleanField(
        required=False,
    )

    def __init__(self, *args, **kwargs):
        """
        获取当前用户和当前分类。
        """

        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        self.user = request.user if request else None

        self.category = self.context.get("category")

    def validate(self, attrs):
        """
        校验修改后的分类名称和类型是否重复。
        """

        # 至少需要传一个字段。
        if not attrs:
            raise serializers.ValidationError("请至少提供一个需要修改的字段")

        # 修改后的名称。
        name = attrs.get(
            "name",
            self.category.name,
        )

        # 修改后的分类类型。
        category_type = attrs.get(
            "category_type",
            self.category.category_type,
        )

        # 查询当前用户其他未删除分类。
        exists = (
            Category.objects.filter(
                user=self.user,
                name=name,
                category_type=category_type,
                is_deleted=False,
            )
            .exclude(id=self.category.id)
            .exists()
        )

        if exists:
            raise serializers.ValidationError("已存在同名分类")

        return attrs
