from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve
from django.templatetags.static import static as static_file
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=static_file('img/logo-sidebar.png'), permanent=True)),
    path('admin/', admin.site.urls),

    # Auth JWT
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API
    path('api/v1/', include([
        path('auth/', include('apps.accounts.urls')),
        path('projects/', include('apps.projects.urls')),
        path('projects/<int:project_id>/tasks/', include('apps.tasks.urls')),
        path('projects/<int:project_id>/resources/', include('apps.resources.urls')),
        path('projects/<int:project_id>/assignments/', include('apps.assignments.urls')),
        path('projects/<int:project_id>/baselines/', include('apps.baselines.urls')),
        path('projects/<int:project_id>/kpis/', include('apps.kpis.urls')),
        path('projects/<int:project_id>/reports/', include('apps.reports.urls')),
        path('projects/<int:project_id>/objectives/', include('apps.objectives.urls')),
        path('projects/<int:project_id>/meetings/', include('apps.meetings.urls')),
        path('notifications/', include('apps.notifications.urls')),
    ])),

    # Frontend views
    path('accounts/', include('apps.accounts.frontend_urls')),
    path('discussions/', include('apps.discussions.urls')),
    path('', include('apps.projects.frontend_urls')),
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
