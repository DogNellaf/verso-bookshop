import django.contrib.postgres.search
from django.db import migrations, models


def create_postgres_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS main_book_search_document_gin "
        "ON main_book USING gin (search_document)"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS main_book_search_text_trgm "
        "ON main_book USING gin (search_text gin_trgm_ops)"
    )


def drop_postgres_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS main_book_search_document_gin")
    schema_editor.execute("DROP INDEX IF EXISTS main_book_search_text_trgm")


def build_index(apps, schema_editor):
    from main.search import update_book_index

    Book = apps.get_model("main", "Book")
    for book_id in Book.objects.values_list("pk", flat=True):
        update_book_index(Book, book_id)


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0008_payments"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="search_document",
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="search_text",
            field=models.TextField(blank=True, default="", editable=False),
        ),
        migrations.RunPython(create_postgres_indexes, drop_postgres_indexes),
        migrations.RunPython(build_index, migrations.RunPython.noop),
    ]
