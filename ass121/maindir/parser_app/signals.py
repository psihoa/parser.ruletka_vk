# parser_app/signals.py
import shutil
import os
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def clear_authors_photos(sender, **kwargs):
    """Очищает папку authors_photos при каждой миграции."""
    folder = os.path.join(settings.MEDIA_ROOT, 'authors_photos')
    try:
        shutil.rmtree(folder)
    except FileNotFoundError:
        pass  # Папка не существует, ничего не делаем
    os.makedirs(folder, exist_ok=True)  # Создаем папку снова
    print(f"Очищена папка {folder}") # Optional message for visibility