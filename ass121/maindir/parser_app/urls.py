from django.urls import path
from . import views

app_name = 'parser_app'

urlpatterns = [
    path('get_comments/', views.get_comments, name='get_comments'),
]