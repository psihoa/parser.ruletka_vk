from django.urls import path
from . import views  # Импорт из текущего приложения
from django.urls import path, include
from django.contrib import admin
urlpatterns = [
    path('', views.home, name='home'),  # Главная страница
    # Другие URL вашего приложения


    path('admin/', admin.site.urls),
    path('parser/', include(('parser_app.urls', 'parser_app'))),  # Пространство имен здесь
]