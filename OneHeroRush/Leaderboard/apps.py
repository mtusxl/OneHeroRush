from django.apps import AppConfig


class LeaderboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Leaderboard'

    def ready(self):
        import Leaderboard.signals
