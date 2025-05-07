from django.apps import AppConfig


class QueryManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'query_management'

    def ready(self):
        import query_management.signals
