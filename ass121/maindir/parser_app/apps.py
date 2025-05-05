from django.apps import AppConfig


class ParserAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parser_app'


    def ready(self):
        import parser_app.signals  # noqa