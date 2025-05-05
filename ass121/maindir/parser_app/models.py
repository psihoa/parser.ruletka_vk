from django.db import models

class Author(models.Model):
    author_id = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    photo = models.ImageField(upload_to='authors_photos', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.author_id})"

class Comment(models.Model):
    comment_id = models.CharField(max_length=255, unique=True)  # ID комментария из VK
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    text = models.TextField()
    date = models.DateTimeField()
    post_id = models.CharField(max_length=255, default='') # Add post_id

    def __str__(self):
        return f"Comment {self.comment_id} by {self.author}"

from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
import os

@receiver(pre_delete, sender=Author)
def delete_author_photo(sender, instance, **kwargs):
    """Удаляет фотографию автора перед удалением объекта Author."""
    if instance.photo:
        photo_path = instance.photo.path
        if os.path.exists(photo_path):
            os.remove(photo_path)

@receiver(post_save, sender=Author)
def delete_old_author_photo(sender, instance, **kwargs):
    """Удаляет старую фотографию автора после сохранения новой."""
    if kwargs.get('update_fields') and 'photo' in kwargs['update_fields']:
        try:
            old_instance = Author.objects.get(pk=instance.pk)
            if old_instance.photo and old_instance.photo != instance.photo:
                old_photo_path = old_instance.photo.path
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)
        except Author.DoesNotExist:
            pass