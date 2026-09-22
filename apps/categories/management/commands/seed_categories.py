from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.models import Category


class Command(BaseCommand):
    """
    初始化系统默认收入 / 支出分类。

    使用方式：

    python manage.py seed_categories
    """

    # 命令帮助说明。
    help = "初始化系统默认收入和支出分类"

    # 系统默认支出分类。
    EXPENSE_CATEGORIES = [
        {
            "name": "餐饮",
            "icon": "food",
            "color": "#FF9800",
            "sort_order": 1,
        },
        {
            "name": "交通",
            "icon": "transport",
            "color": "#2196F3",
            "sort_order": 2,
        },
        {
            "name": "购物",
            "icon": "shopping",
            "color": "#E91E63",
            "sort_order": 3,
        },
        {
            "name": "住房",
            "icon": "home",
            "color": "#795548",
            "sort_order": 4,
        },
        {
            "name": "娱乐",
            "icon": "entertainment",
            "color": "#9C27B0",
            "sort_order": 5,
        },
        {
            "name": "医疗",
            "icon": "medical",
            "color": "#F44336",
            "sort_order": 6,
        },
        {
            "name": "教育",
            "icon": "education",
            "color": "#3F51B5",
            "sort_order": 7,
        },
        {
            "name": "通讯",
            "icon": "communication",
            "color": "#00BCD4",
            "sort_order": 8,
        },
        {
            "name": "旅行",
            "icon": "travel",
            "color": "#4CAF50",
            "sort_order": 9,
        },
        {
            "name": "生活缴费",
            "icon": "utilities",
            "color": "#607D8B",
            "sort_order": 10,
        },
        {
            "name": "其他",
            "icon": "other",
            "color": "#9E9E9E",
            "sort_order": 99,
        },
    ]

    # 系统默认收入分类。
    INCOME_CATEGORIES = [
        {
            "name": "工资",
            "icon": "salary",
            "color": "#4CAF50",
            "sort_order": 1,
        },
        {
            "name": "奖金",
            "icon": "bonus",
            "color": "#8BC34A",
            "sort_order": 2,
        },
        {
            "name": "兼职",
            "icon": "parttime",
            "color": "#009688",
            "sort_order": 3,
        },
        {
            "name": "投资",
            "icon": "investment",
            "color": "#3F51B5",
            "sort_order": 4,
        },
        {
            "name": "红包",
            "icon": "redpacket",
            "color": "#F44336",
            "sort_order": 5,
        },
        {
            "name": "退款",
            "icon": "refund",
            "color": "#FF9800",
            "sort_order": 6,
        },
        {
            "name": "其他",
            "icon": "other",
            "color": "#9E9E9E",
            "sort_order": 99,
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        """
        执行初始化。

        特点：
        1. 可重复执行；
        2. 不会重复创建相同系统分类；
        3. 已存在分类会更新图标、颜色、排序等配置。
        """

        # 已创建数量。
        created_count = 0

        # 已更新数量。
        updated_count = 0

        # ==============================
        # 初始化支出分类
        # ==============================

        for item in self.EXPENSE_CATEGORIES:
            # 根据：
            #
            # 系统分类
            # + 分类名称
            # + 分类类型
            #
            # 判断记录是否已经存在。
            category, created = Category.objects.update_or_create(
                user=None,
                name=item["name"],
                category_type=(Category.CategoryType.EXPENSE),
                is_system=True,
                defaults={
                    "icon": item["icon"],
                    "color": item["color"],
                    "sort_order": (item["sort_order"]),
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            # 统计创建 / 更新数量。
            if created:
                created_count += 1
            else:
                updated_count += 1

        # ==============================
        # 初始化收入分类
        # ==============================

        for item in self.INCOME_CATEGORIES:
            category, created = Category.objects.update_or_create(
                user=None,
                name=item["name"],
                category_type=(Category.CategoryType.INCOME),
                is_system=True,
                defaults={
                    "icon": item["icon"],
                    "color": item["color"],
                    "sort_order": (item["sort_order"]),
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        # 输出执行结果。
        self.stdout.write(
            self.style.SUCCESS(
                (
                    "系统默认分类初始化完成："
                    f"新增 {created_count} 条，"
                    f"更新 {updated_count} 条"
                )
            )
        )
