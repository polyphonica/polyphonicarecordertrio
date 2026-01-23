"""
URL configuration for polyphonica project.
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.decorators.cache import cache_page

from .sitemaps import sitemaps


def robots_txt(request):
    """Serve robots.txt file."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /manage/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', cache_page(86400)(sitemap), {'sitemaps': sitemaps}, name='sitemap'),
    path('', include('core.urls')),
    path('about/', include('about.urls')),
    path('concerts/', include('concerts.urls')),
    path('workshops/', include('workshops.urls')),
    path('media/', include('media_content.urls')),
    path('accounts/', include('accounts.urls')),
    path('manage/repertoire/', include('repertoire.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
