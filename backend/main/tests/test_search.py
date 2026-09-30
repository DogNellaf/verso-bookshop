from unittest import skipUnless

from django.db import connection
from django.urls import reverse

from main.models import Book, BookTranslation
from main.tests.helpers import APITestCase, make_book

POSTGRES = connection.vendor == "postgresql"


class SearchTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.crime = make_book(
            title="Crime and Punishment",
            author="Fyodor Dostoevsky",
            description="A student murders a pawnbroker and is consumed by guilt.",
        )
        BookTranslation.objects.create(
            book=self.crime,
            language="ru",
            title="Преступление и наказание",
            author="Фёдор Достоевский",
            description="Студент убивает старуху-процентщицу и мучается чувством вины.",
        )
        self.hobbit = make_book(
            title="The Hobbit",
            author="J. R. R. Tolkien",
            description="Bilbo goes on a quest to win a treasure guarded by a dragon.",
        )
        self.dracula = make_book(
            title="Dracula",
            author="Bram Stoker",
            description="Letters and diaries about an ancient count and his dragon-like cruelty.",
        )

    def titles(self, term, language="en", **params):
        response = self.client.get(
            reverse("book-list"), {"search": term, **params}, HTTP_ACCEPT_LANGUAGE=language
        )
        return [b["title"] for b in response.data["results"]]


class SearchIndexTest(SearchTestCase):
    def test_search_text_holds_every_language(self):
        text = Book.objects.get(pk=self.crime.pk).search_text
        self.assertIn("Crime and Punishment", text)
        self.assertIn("Преступление и наказание", text)
        self.assertIn("Фёдор Достоевский", text)

    def test_index_follows_translation_changes(self):
        translation = self.crime.translations.get()
        translation.delete()
        self.assertNotIn("Преступление", Book.objects.get(pk=self.crime.pk).search_text)

    def test_title_and_author_in_any_language(self):
        self.assertEqual(self.titles("наказание"), ["Crime and Punishment"])
        self.assertEqual(self.titles("Tolkien"), ["The Hobbit"])


@skipUnless(POSTGRES, "full-text search needs PostgreSQL")
class FullTextSearchTest(SearchTestCase):
    def test_description_words_match_with_stemming(self):
        # "murdered" and "murders" share the stem "murder".
        self.assertEqual(self.titles("murdered"), ["Crime and Punishment"])

    def test_russian_morphology(self):
        # The description says "убивает", the query uses another form.
        self.assertEqual(self.titles("убийство студента", language="ru"), [])
        self.assertEqual(self.titles("студенты", language="ru"), ["Преступление и наказание"])

    def test_title_matches_rank_above_description_matches(self):
        make_book(title="The Count of Monte Cristo", description="A sailor is jailed.")
        self.assertEqual(self.titles("count"), ["The Count of Monte Cristo", "Dracula"])

    def test_websearch_syntax(self):
        self.assertEqual(self.titles("dragon -count"), ["The Hobbit"])
        self.assertEqual(self.titles('"ancient count"'), ["Dracula"])

    def test_typos_fall_back_to_trigram_similarity(self):
        self.assertEqual(self.titles("Dostoyevsky"), ["Crime and Punishment"])
        self.assertEqual(self.titles("Tolkein"), ["The Hobbit"])

    def test_explicit_ordering_wins_over_rank(self):
        self.assertEqual(self.titles("dragon", ordering="-title"), ["The Hobbit", "Dracula"])
