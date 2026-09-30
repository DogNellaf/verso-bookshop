"""Fill in missing book translations with DeepL.

python manage.py translate_books               # only missing languages
python manage.py translate_books --overwrite   # redo every language
"""

from django.core.management.base import BaseCommand, CommandError

from main.machine_translation import (
    TranslationError,
    is_configured,
    missing_languages,
    translate_book,
)
from main.models import Book


class Command(BaseCommand):
    help = "Translate books into Russian, French and German with DeepL."

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, overwrite=False, **options):
        if not is_configured():
            raise CommandError("Set DEEPL_API_KEY to use machine translation.")
        books = Book.objects.prefetch_related("translations")
        count = 0
        for book in books:
            if not overwrite and not missing_languages(book):
                continue
            try:
                done = translate_book(book, overwrite=overwrite)
            except TranslationError as exc:
                raise CommandError(f"{book.title}: {exc}") from exc
            count += 1
            self.stdout.write(f"  {book.title}: {', '.join(done)}")
        self.stdout.write(self.style.SUCCESS(f"Translated {count} book(s)."))
