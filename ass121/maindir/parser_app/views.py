from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .parser import extract_group_and_post_ids, get_comments_vk
from .models import Author, Comment
from django.core.exceptions import ObjectDoesNotExist
from django.templatetags.static import static
from django.conf import settings  #  Импортируйте settings
import os

# Токен указывается прямо в коде (НЕ РЕКОМЕНДУЕТСЯ для production!)
ACCESS_TOKEN = "06deaa9a06deaa9a06deaa9ab005ee1851006de06deaa9a6ecb9689a1983f76c13a089e"  # Замените на ваш токен!


@csrf_exempt
def get_comments(request):
    """
    Получает ссылку на пост VK из POST-запроса, извлекает имена авторов, фамилии и фото и передает их в шаблон.
    Сохраняет авторов и комментарии в базе данных.
    """
    author_data = []  # Теперь храним данные об авторах
    error_message = None

    if request.method == 'POST':
        post_url = request.POST.get('post_url', '')
        if not post_url:
            error_message = 'Не указана ссылка на пост ВКонтакте'
        else:
            group_id, post_id = extract_group_and_post_ids(post_url)

            if group_id and post_id:
                # Сначала пытаемся загрузить авторов из базы данных (вместо комментариев)
                try:
                    authors = Author.objects.filter(comment__post_id=post_id).distinct()  # Получаем уникальных авторов, которые оставляли комментарии к этому посту
                    if authors.exists():
                        for author in authors:
                            photo_url = author.photo.url if author.photo else static('main_app/img/default_avatar.png')  # Изменяем путь к статике
                            author_data.append({
                                'first_name': author.first_name,
                                'last_name': author.last_name,
                                'photo_url': photo_url
                            })
                except ObjectDoesNotExist:
                    pass  # Если нет авторов в базе, получаем из API

                # Если в базе данных нет авторов или произошла ошибка, получаем из API
                if not author_data:
                    comments = get_comments_vk(group_id, post_id, ACCESS_TOKEN)

                    if comments:
                        # После получения комментариев из API авторы уже сохранены в базе
                        # (внутри функции get_comments_vk), поэтому теперь просто загружаем их из базы
                        try:
                            authors = Author.objects.filter(comment__post_id=post_id).distinct()  # Получаем уникальных авторов, которые оставляли комментарии к этому посту
                            if authors.exists():
                                for author in authors:
                                    photo_url = author.photo.url if author.photo else static('main_app/img/default_avatar.png')  # Изменяем путь к статике

                                    author_data.append({
                                        'first_name': author.first_name,
                                        'last_name': author.last_name,
                                        'photo_url': photo_url
                                    })
                        except ObjectDoesNotExist:
                            error_message = "Не удалось загрузить авторов из базы данных после парсинга."
                    else:
                        error_message = 'Не удалось получить комментарии из API'
            else:
                error_message = 'Не удалось извлечь ID группы и поста из ссылки. Проверьте ссылку.'

    return render(request, 'main_app/home.html', {'author_data': author_data, 'error': error_message})  # Передаем author_data вместо comments_data