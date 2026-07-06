import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_order"),
    ]

    operations = [
        migrations.RenameField(
            model_name="order",
            old_name="count",
            new_name="quantity",
        ),
        migrations.AddField(
            model_name="order",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="Created at",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="book",
            options={"ordering": ["title"], "verbose_name": "Book", "verbose_name_plural": "Books"},
        ),
        migrations.AlterModelOptions(
            name="order",
            options={"ordering": ["-created_at"], "verbose_name": "Order", "verbose_name_plural": "Orders"},
        ),
        migrations.AlterField(
            model_name="order",
            name="quantity",
            field=models.PositiveIntegerField(default=1, verbose_name="Quantity"),
        ),
    ]
