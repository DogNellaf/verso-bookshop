"""Catalog search.

On PostgreSQL every book has a ``search_document`` (tsvector) built from the
English original and all translations, each stemmed with its own language
configuration, plus unstemmed titles and authors. Queries use
``websearch_to_tsquery`` in the visitor's language, results are ranked, and
when nothing matches a trigram search on ``search_text`` catches typos.

Other databases (SQLite in development) fall back to ``icontains`` on
``search_text``, which holds every title and author in every language.
"""

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramWordSimilarity,
)
from django.db import connection
from django.db.models import F, Value
from rest_framework.filters import BaseFilterBackend

TS_CONFIGS = {"en": "english", "ru": "russian", "fr": "french", "de": "german"}
TRIGRAM_THRESHOLD = 0.4


def is_postgres():
    return connection.vendor == "postgresql"


def document_parts(book, translations):
    """(language, title, author, description) for the original and translations."""
    parts = [("en", book.title, book.author, book.description)]
    parts += [(t.language, t.title, t.author, t.description) for t in translations]
    return parts


def search_text(parts):
    return " ".join(f"{title} {author}" for _, title, author, _ in parts)


def search_vector(parts):
    vector = None
    for language, title, author, description in parts:
        config = TS_CONFIGS.get(language, "simple")
        pieces = [
            SearchVector(Value(title), config=config, weight="A"),
            SearchVector(Value(title), config="simple", weight="A"),
            SearchVector(Value(author), config="simple", weight="B"),
            SearchVector(Value(description), config=config, weight="C"),
        ]
        for piece in pieces:
            vector = piece if vector is None else vector + piece
    return vector


def update_book_index(book_model, book_id):
    """Rebuild the search fields of one book."""
    book = book_model.objects.filter(pk=book_id).prefetch_related("translations").first()
    if book is None:
        return
    parts = document_parts(book, book.translations.all())
    fields = {"search_text": search_text(parts)}
    if is_postgres():
        fields["search_document"] = search_vector(parts)
    book_model.objects.filter(pk=book_id).update(**fields)


class BookSearchFilter(BaseFilterBackend):
    """``?search=`` for books. See the module docstring."""

    param = "search"

    def filter_queryset(self, request, queryset, view):
        term = request.query_params.get(self.param, "").strip()
        if not term:
            return queryset
        explicit_ordering = bool(request.query_params.get("ordering"))

        if not is_postgres():
            return queryset.filter(search_text__icontains=term)

        from main.serializers import current_language

        config = TS_CONFIGS.get(current_language(), "english")
        query = SearchQuery(term, config=config, search_type="websearch") | SearchQuery(
            term, config="simple", search_type="websearch"
        )
        matches = queryset.filter(search_document=query).annotate(
            rank=SearchRank(F("search_document"), query)
        )
        if matches.exists():
            return matches if explicit_ordering else matches.order_by("-rank", "title_i18n")

        # Nothing matched exactly: try a fuzzy match to forgive typos.
        fuzzy = queryset.annotate(similarity=TrigramWordSimilarity(term, "search_text")).filter(
            similarity__gte=TRIGRAM_THRESHOLD
        )
        return fuzzy if explicit_ordering else fuzzy.order_by("-similarity", "title_i18n")
