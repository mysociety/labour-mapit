from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin

handler500 = 'mapit.shortcuts.json_500'

urlpatterns = [
    re_path(r'^', include('mapit.urls')),
    re_path(r'^', include('mapit_labour.urls')),
    re_path(r'^admin/', admin.site.urls),
]

if settings.DEBUG: # pragma: no cover
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
