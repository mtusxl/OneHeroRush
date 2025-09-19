from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view  # Импорт для Swagger schema
from drf_yasg import openapi  # Для info/description в доках


schema_view = get_schema_view(
    openapi.Info(
        title="OneHeroRush Dota 2 Idle Server API",
        default_version='v1',
        description="API для waves (625x5 acts x4 diff=2500 battles с creeps Small Satyr/Hellbear + bosses Oracle), clans (rank=sum MMR, max_members=30+ passive stats), souls (summon 15 coupons=15 souls, lvl up chance legendary + hidden stats), pets (Small Kobold +10% gold), chests (randomized Phase Boots x rarity 0.5-3.1 vamp/crit, auto-mode 1-20 opens), offline farm (+gold/keys AFK via Celery), quests (daily 'победить врагов 150 раз' за 150 diamonds +5 souls). Scale to 10k+ with Redis/Throttling/Prometheus/Grafana.",
        terms_of_service="https://github.com/mtusxl/OneHeroRush",
        contact=openapi.Contact(email="mtusxl@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[path('api/', include('Users.urls'))],  # Scan для /api/auth/login/ etc. (auto-fields от serializers)
)
urlpatterns = [
    path('admin/', admin.site.urls),  
    path('api/', include('Users.urls')), 
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'), 
]