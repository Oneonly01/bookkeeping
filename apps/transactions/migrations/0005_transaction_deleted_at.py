from django.db import migrations, models
from django.db.models import F


def fill_deleted_at(apps, schema_editor):
    """
    为历史已删除账单补齐删除时间。

    旧版本没有单独保存删除时间，只能使用最后更新时间作为历史近似值；
    不将迁移执行时间写入旧账单，避免丢失原有先后顺序。
    """
    transaction_model = apps.get_model("transactions", "Transaction")
    transaction_model.objects.using(schema_editor.connection.alias).filter(
        status="deleted",
        deleted_at__isnull=True,
    ).update(
        deleted_at=F("updated_at"),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0004_recurringtransaction_recurringexecution_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="deleted_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name="删除时间",
                db_comment="最近一次逻辑删除账单的时间，恢复后清空",
            ),
        ),
        # 回退时AddField负责移除字段，不反向修改账单状态或余额。
        migrations.RunPython(
            fill_deleted_at,
            migrations.RunPython.noop,
        ),
    ]
