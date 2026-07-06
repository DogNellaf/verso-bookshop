"""Populate the database with demo content for screenshots / portfolio.

Usage:
    python manage.py seed          # add demo data (idempotent)
    python manage.py seed --flush  # wipe books & orders first, then reseed

Book covers are downloaded from the Open Library covers API into MEDIA_ROOT.
If a download fails (e.g. no internet), the book is still created without a
cover and the frontend falls back to a generated placeholder.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import Book, Order

BOOKS = [
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "isbn": "9780743273565",
        "price": "12.99",
        "stock": 8,
        "description": (
            "Set in the summer of 1922, Fitzgerald's masterpiece follows the "
            "mysterious millionaire Jay Gatsby and his obsession with Daisy "
            "Buchanan — a shimmering, tragic portrait of the American Dream."
        ),
    },
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "isbn": "9780061120084",
        "price": "14.99",
        "stock": 5,
        "description": (
            "A Pulitzer Prize-winning story of racial injustice in the Deep "
            "South, seen through the eyes of young Scout Finch as her father "
            "defends a black man wrongly accused."
        ),
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "9780451524935",
        "price": "11.49",
        "stock": 12,
        "description": (
            "A chilling dystopia where surveillance, propaganda and "
            "totalitarian control define every waking moment. Big Brother is "
            "watching — and freedom is the most dangerous idea of all."
        ),
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "isbn": "9780060850524",
        "price": "13.99",
        "stock": 0,
        "description": (
            "A future engineered for happiness, stability and pleasure — but "
            "at the cost of freedom, art and truth. Huxley's prophetic vision "
            "of a society that trades soul for comfort."
        ),
    },
    {
        "title": "The Catcher in the Rye",
        "author": "J. D. Salinger",
        "isbn": "9780316769488",
        "price": "10.99",
        "stock": 3,
        "description": (
            "Holden Caulfield's restless, funny and heartbreaking journey "
            "through New York City after being expelled from prep school — the "
            "definitive novel of teenage alienation."
        ),
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "isbn": "9780141439518",
        "price": "9.49",
        "stock": 7,
        "description": (
            "Elizabeth Bennet navigates love, class and the sting of first "
            "impressions in Regency England. Austen's sparkling wit at its "
            "very finest."
        ),
    },
    {
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "isbn": "9780143058144",
        "price": "15.99",
        "stock": 0,
        "description": (
            "A destitute student murders a pawnbroker and is consumed by guilt "
            "and paranoia. A towering psychological drama of conscience, "
            "suffering and redemption."
        ),
    },
    {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "9780547928227",
        "price": "16.99",
        "stock": 10,
        "description": (
            "Bilbo Baggins is swept from his comfortable hobbit-hole into an "
            "epic quest to reclaim a treasure guarded by the dragon Smaug. The "
            "beloved prelude to The Lord of the Rings."
        ),
    },
    {
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "isbn": "9781451673319",
        "price": "12.49",
        "stock": 6,
        "description": (
            "In a world where books are outlawed and 'firemen' burn any that "
            "are found, one fireman begins to question everything. Bradbury's "
            "blazing warning about censorship and conformity."
        ),
    },
    {
        "title": "Animal Farm",
        "author": "George Orwell",
        "isbn": "9780451526342",
        "price": "8.99",
        "stock": 15,
        "description": (
            "The farm animals revolt against their human master, only to find "
            "that power corrupts absolutely. A razor-sharp fable of revolution "
            "betrayed."
        ),
    },
    {
        "title": "Jane Eyre",
        "author": "Charlotte Brontë",
        "isbn": "9780141441146",
        "price": "10.49",
        "stock": 4,
        "description": (
            "An orphaned governess falls for her brooding employer, Mr "
            "Rochester — but Thornfield Hall hides a terrible secret. A fierce, "
            "romantic and unforgettable heroine."
        ),
    },
    {
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "isbn": "9780141439471",
        "price": "11.99",
        "stock": 9,
        "description": (
            "Victor Frankenstein creates life — and unleashes a tragedy of "
            "ambition, abandonment and revenge. The novel that gave birth to "
            "science fiction."
        ),
    },
]

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demopass123"

# (book title, quantity) — orders placed by the demo user.
DEMO_ORDERS = [
    ("The Great Gatsby", 1),
    ("1984", 2),
    ("The Hobbit", 1),
]

COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"


class Command(BaseCommand):
    help = "Populate the database with demo books, a demo user and orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing books and orders before seeding.",
        )
        parser.add_argument(
            "--no-covers",
            action="store_true",
            help="Skip downloading cover images.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            deleted_orders = Order.objects.all().delete()[0]
            deleted_books = Book.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(
                    f"Flushed {deleted_books} book(s) and {deleted_orders} order(s)."
                )
            )

        created, updated, covers = 0, 0, 0
        books_by_title: dict[str, Book] = {}

        for data in BOOKS:
            book, was_created = Book.objects.get_or_create(
                title=data["title"],
                defaults={
                    "author": data["author"],
                    "description": data["description"],
                    "price": Decimal(data["price"]),
                    "stock": data["stock"],
                },
            )
            if not was_created:
                book.author = data["author"]
                book.description = data["description"]
                book.price = Decimal(data["price"])
                book.stock = data["stock"]
                book.save()
                updated += 1
            else:
                created += 1

            books_by_title[book.title] = book

            if not options["no_covers"] and not book.cover:
                if self._download_cover(book, data["isbn"]):
                    covers += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Books: {created} created, {updated} updated, {covers} cover(s) downloaded."
            )
        )

        self._seed_demo_user_and_orders(books_by_title)

    def _download_cover(self, book: Book, isbn: str) -> bool:
        url = COVER_URL.format(isbn=isbn)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "bookshop-seed/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                content = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.stdout.write(
                self.style.WARNING(f"  ! cover for '{book.title}' failed: {exc}")
            )
            return False

        # Open Library returns a tiny blank image when a cover is missing;
        # skip anything suspiciously small.
        if len(content) < 1000:
            self.stdout.write(
                self.style.WARNING(f"  ! no cover available for '{book.title}'")
            )
            return False

        book.cover.save(f"{isbn}.jpg", ContentFile(content), save=True)
        return True

    def _seed_demo_user_and_orders(self, books_by_title: dict[str, Book]) -> None:
        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"email": "demo@example.com"},
        )
        user.set_password(DEMO_PASSWORD)
        user.save()

        # Reset this demo user's orders so re-running stays clean.
        Order.objects.filter(buyer=user).delete()
        order_count = 0
        for title, quantity in DEMO_ORDERS:
            book = books_by_title.get(title)
            if book is None:
                continue
            Order.objects.create(buyer=user, book=book, quantity=quantity)
            order_count += 1

        state = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo user '{DEMO_USERNAME}' {state} (password: {DEMO_PASSWORD}), "
                f"{order_count} order(s) placed."
            )
        )
