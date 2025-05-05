from django.shortcuts import render
def home(request):
    return render(request, 'main_app/home.html')  # Обратите внимание на имя папки шаблонов
