import requests
import json
from urllib.parse import urlparse, parse_qs

from .models import Author, Comment
from django.core.files.base import ContentFile
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('vk_parser.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def extract_group_and_post_ids(post_url):
    """Извлекает ID группы и поста из URL ВКонтакте."""
    try:
        parsed_url = urlparse(post_url)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        if "vk.com" in parsed_url.netloc:
            if "wall" in path:
                parts = path.split("wall")
                if len(parts) == 2:
                    ids_str = parts[1].strip("/")
                    if "_" in ids_str:
                        group_id, post_id = ids_str.split("_")
                        return "" + group_id, post_id
            elif "w" in query and "wall" in query["w"][0]:
                wall_part = query["w"][0]
                if "wall" in wall_part:
                    ids_str = wall_part.split("wall")[1]
                    if "_" in ids_str:
                        group_id, post_id = ids_str.split("_")
                        return "" + group_id, post_id
            elif path.startswith("/wall"):
                parts = path.split("wall")
                if len(parts) == 2:
                    ids_str = parts[1].strip("/")
                    if "_" in ids_str:
                        group_id, post_id = ids_str.split("_")
                        return "-" + group_id, post_id
        return None, None

    except (AttributeError, ValueError, IndexError):
        return None, None


def get_user_info(user_id, access_token, api_version="5.131"):
    """Получает информацию о пользователе VK с использованием API."""
    try:
        api_url = f"https://api.vk.com/method/users.get"
        params = {
            "user_ids": user_id,
            "fields": "photo_50,photo_100,photo_200",
            "access_token": access_token,
            "v": api_version,
        }
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        if "response" in data and len(data["response"]) > 0:
            return data["response"][0]
        else:
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при разборе JSON ответа: {e}")
        return None


def get_comments_vk(group_id, post_id, access_token, api_version="5.131", max_comments=1000):
    """Получает все комментарии из поста ВКонтакте с использованием API.
       Сохраняет авторов и комментарии в базе данных.
    """
    all_comments = []
    offset = 0
    count = 100
    import datetime  # Import the datetime module

    while len(all_comments) < max_comments:
        try:
            api_url = f"https://api.vk.com/method/wall.getComments"
            params = {
                "owner_id": group_id,
                "post_id": post_id,
                "need_likes": "0",
                "count": count,
                "extended": "1",
                "access_token": access_token,
                "v": api_version,
                "offset": offset,
            }
            logger.debug(f"URL запроса: {api_url}")  # Log the URL
            logger.debug(f"Параметры запроса: {params}")  # Log the parameters

            response = requests.get(api_url, params=params)
            logger.debug(f"Статус код ответа: {response.status_code}")  # Log the status code
            logger.debug(f"Текст ответа: {response.text}")  # Log the response text

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"Ошибка API VK: {data['error']['error_msg']}")  # Log the error message
                break

            if "response" in data and "items" in data["response"]:
                comments = data["response"]["items"]

                if not comments:
                    break

                profiles = data["response"].get("profiles", [])
                profiles_dict = {str(profile["id"]): profile for profile in profiles}
                groups = data["response"].get("groups", [])  # Get the groups

                for comment in comments:
                    comment_id = str(comment["id"])
                    author_id = str(comment["from_id"])

                    logger.debug(f"ID автора: {author_id}")

                    if author_id.startswith('-'):
                        # It's a group
                        logger.debug("Это группа")
                        try:
                            group_info = next(
                                group for group in groups if str(group["id"]) == author_id[1:])
                            author_name = group_info.get("name", "Unknown Group")
                            author_surname = ""  # Groups don't have surnames
                            author_photo_url = group_info.get("photo_100", "") or group_info.get("photo_50", "")  # Try photo_100 first
                        except StopIteration:
                            author_name = "Unknown Group"
                            author_surname = ""
                            author_photo_url = ""
                    else:
                        # It's a user
                        logger.debug("Это пользователь")
                        user_info = get_user_info(author_id, access_token)  # Get user info
                        if user_info:
                            author_name = user_info.get("first_name", "Unknown")
                            author_surname = user_info.get("last_name", "")
                            author_photo_url = user_info.get("photo_100", "") or user_info.get("photo_50", "")  # Get photo
                        else:
                            author_name = "Unknown"
                            author_surname = ""
                            author_photo_url = ""

                    logger.debug(f"URL фотографии автора: {author_photo_url}")

                    # Скачиваем и сохраняем фото
                    if author_photo_url:
                        try:
                            logger.debug(f"Скачиваем фото с URL: {author_photo_url}")
                            response = requests.get(author_photo_url, stream=True)
                            response.raise_for_status()  # Raise an exception for bad status codes
                            photo_content = ContentFile(response.content)
                            photo_file_name = f"{author_id}.jpg"  # Unique filename

                            # Сохраняем автора в базу данных (или обновляем, если он уже есть)
                            author, created = Author.objects.get_or_create(
                                author_id=author_id,
                                defaults={
                                    'first_name': author_name,
                                    'last_name': author_surname,
                                }
                            )
                            logger.debug(f"Сохраняем фото как: {photo_file_name}")
                            author.photo.save(photo_file_name, photo_content, save=True)  # Сохраняем изображение в поле photo
                            logger.debug("Фото успешно сохранено")
                        except requests.exceptions.RequestException as e:
                            logger.error(f"Ошибка при скачивании фото: {e}")
                        except Exception as e:
                            logger.error(f"Ошибка при сохранении фото: {e}")
                    else:
                        author, created = Author.objects.get_or_create(
                            author_id=author_id,
                            defaults={
                                'first_name': author_name,
                                'last_name': author_surname,
                            }
                        )

                    # Сохраняем комментарий в базу данных
                    comment_date = timezone.datetime.fromtimestamp(comment.get("date", 0), tz=datetime.timezone.utc)
                    comment, created = Comment.objects.get_or_create(
                        comment_id=comment_id,
                        defaults={
                            'author': author,
                            'text': comment.get("text", ""),
                            'date': comment_date,
                            'post_id': post_id,
                        }
                    )

                    comment_data = {
                        "author_name": author.first_name,
                        "author_surname": author.last_name,
                        "author_photo": author.photo.url if author.photo else '',  # Use the URL from ImageField
                        "text": comment.text,
                        "date": comment.date,
                        "comment_id": comment.comment_id,
                    }
                    all_comments.append(comment_data)

                offset += count
            else:
                break
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            break
        except json.JSONDecodeError:
            logger.error(f"Ошибка при разборе JSON ответа: {e}")
            break
        except Exception as e:
            logger.error(f"Произошла непредвиденная ошибка: {e}")
            break

    return all_comments