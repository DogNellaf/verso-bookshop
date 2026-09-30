from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from main.models import Book, BookTranslation
from main.search import update_book_index


@receiver(post_save, sender=Book, dispatch_uid="verso_translate_new_book")
def translate_new_book(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        from main.machine_translation import translate_new_book as translate

        transaction.on_commit(lambda: translate(instance.pk))


@receiver(post_save, sender=Book, dispatch_uid="verso_index_book")
def index_book(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw:
        return
    # Saving only stock or price doesn't change what search looks at.
    if update_fields and not {"title", "author", "description"} & set(update_fields):
        return
    update_book_index(Book, instance.pk)


@receiver(post_save, sender=BookTranslation, dispatch_uid="verso_index_translation")
@receiver(post_delete, sender=BookTranslation, dispatch_uid="verso_index_translation_delete")
def index_translation(sender, instance, raw=False, **kwargs):
    if not raw:
        update_book_index(Book, instance.book_id)
