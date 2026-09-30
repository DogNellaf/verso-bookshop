"""Machine translation of the catalog through the DeepL API.

New books are written in English. With DEEPL_API_KEY set, the missing
Russian, French and German versions are filled in automatically when a book
is created, from the admin ("Translate missing languages") or with
``python manage.py translate_books``. Staff can edit the result afterwards.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from main.models import Book, BookTranslation

logger = logging.getLogger(__name__)

TRANSLATED_LANGUAGES = [code for code, _ in settings.LANGUAGES if code != "en"]
FIELDS = ("title", "author", "description")


class TranslationError(Exception):
    pass


def is_configured():
    return bool(settings.DEEPL_API_KEY)


def _endpoint():
    # Keys of the free plan end with ":fx" and use a separate host.
    host = "api-free.deepl.com" if settings.DEEPL_API_KEY.endswith(":fx") else "api.deepl.com"
    return f"https://{host}/v2/translate"


def translate(texts, target_language):
    """Translate English texts into one of the UI languages."""
    if not is_configured():
        raise TranslationError("DEEPL_API_KEY is not set.")
    body = json.dumps(
        {"text": list(texts), "source_lang": "EN", "target_lang": target_language.upper()}
    ).encode()
    request = urllib.request.Request(
        _endpoint(),
        data=body,
        method="POST",
        headers={
            "Authorization": f"DeepL-Auth-Key {settings.DEEPL_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise TranslationError(f"DeepL request failed: {exc}") from exc
    try:
        return [item["text"] for item in payload["translations"]]
    except (KeyError, TypeError) as exc:
        raise TranslationError("Unexpected response from DeepL.") from exc


def missing_languages(book):
    present = {t.language for t in book.translations.all()}
    return [code for code in TRANSLATED_LANGUAGES if code not in present]


def translate_book(book, languages=None, overwrite=False):
    """Create translations for the book. Returns the languages that were filled."""
    targets = languages or (TRANSLATED_LANGUAGES if overwrite else missing_languages(book))
    source = [getattr(book, field) for field in FIELDS]
    done = []
    for language in targets:
        title, author, description = translate(source, language)
        BookTranslation.objects.update_or_create(
            book=book,
            language=language,
            defaults={"title": title, "author": author, "description": description},
        )
        done.append(language)
    return done


def translate_new_book(book_id):
    """Called after a book is created. Failures are logged, never raised."""
    if not (is_configured() and settings.AUTO_TRANSLATE_BOOKS):
        return
    try:
        translate_book(Book.objects.get(pk=book_id))
    except (TranslationError, Book.DoesNotExist):
        logger.exception("Automatic translation of book %s failed", book_id)
