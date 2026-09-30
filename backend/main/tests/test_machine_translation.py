import json
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from main import machine_translation
from main.models import Book, BookTranslation
from main.tests.helpers import make_book

FAKE = {"ru": "RU", "fr": "FR", "de": "DE"}


def fake_deepl():
    """Answer DeepL requests with '<LANG> <text>' for each text."""

    def urlopen(request, timeout=None):
        body = json.loads(request.data)
        prefix = body["target_lang"]
        response = mock.MagicMock()
        response.__enter__.return_value = StringIO(
            json.dumps({"translations": [{"text": f"{prefix} {t}"} for t in body["text"]]})
        )
        return response

    return mock.patch("urllib.request.urlopen", side_effect=urlopen)


@override_settings(DEEPL_API_KEY="key:fx", AUTO_TRANSLATE_BOOKS=False)
class MachineTranslationTest(TestCase):
    def test_translate_book_fills_missing_languages(self):
        book = make_book(title="Dune", author="Frank Herbert", description="Desert planet.")
        BookTranslation.objects.create(
            book=book, language="ru", title="Дюна", author="Фрэнк Герберт", description="…"
        )
        with fake_deepl() as urlopen:
            done = machine_translation.translate_book(book)
        self.assertEqual(done, ["fr", "de"])
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(
            urlopen.call_args.args[0].full_url, "https://api-free.deepl.com/v2/translate"
        )
        fr = book.translations.get(language="fr")
        self.assertEqual((fr.title, fr.author), ("FR Dune", "FR Frank Herbert"))
        # The hand-made Russian translation stays.
        self.assertEqual(book.translations.get(language="ru").title, "Дюна")

    def test_command(self):
        make_book(title="Dune")
        out = StringIO()
        with fake_deepl():
            call_command("translate_books", stdout=out)
        self.assertEqual(BookTranslation.objects.count(), 3)
        self.assertIn("Translated 1 book(s).", out.getvalue())

    @override_settings(DEEPL_API_KEY="")
    def test_command_without_key(self):
        with self.assertRaises(CommandError):
            call_command("translate_books", stdout=StringIO())

    def test_network_error(self):
        book = make_book()
        with (
            mock.patch("urllib.request.urlopen", side_effect=OSError("down")),
            self.assertRaises(machine_translation.TranslationError),
        ):
            machine_translation.translate_book(book)


@override_settings(DEEPL_API_KEY="key", AUTO_TRANSLATE_BOOKS=True)
class AutoTranslationTest(TransactionTestCase):
    def test_new_book_is_translated_after_commit(self):
        with fake_deepl() as urlopen:
            book = make_book(title="Dune")
        self.assertEqual(urlopen.call_args.args[0].full_url, "https://api.deepl.com/v2/translate")
        self.assertEqual(
            sorted(book.translations.values_list("language", flat=True)), ["de", "fr", "ru"]
        )

    def test_failures_do_not_break_saving(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
            make_book(title="Dune")
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(BookTranslation.objects.count(), 0)


@override_settings(DEEPL_API_KEY="key:fx", AUTO_TRANSLATE_BOOKS=False)
class AdminTranslationTest(TestCase):
    def setUp(self):
        User.objects.create_superuser("admin", "a@example.com", "adminpass123")
        self.client.login(username="admin", password="adminpass123")
        self.book = make_book(title="Dune")

    def test_missing_translations_filter_and_action(self):
        url = reverse("admin:main_book_changelist")
        response = self.client.get(url, {"translations": "missing"})
        self.assertContains(response, "missing ru, fr, de")

        with fake_deepl():
            self.client.post(
                url, {"action": "translate_missing", "_selected_action": [self.book.pk]}
            )
        self.assertEqual(self.book.translations.count(), 3)
        response = self.client.get(url, {"translations": "missing"})
        self.assertNotContains(response, "Dune")
