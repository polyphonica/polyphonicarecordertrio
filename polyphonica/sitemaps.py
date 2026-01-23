from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from concerts.models import Concert
from workshops.models import Workshop


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    changefreq = 'monthly'

    def items(self):
        return [
            'core:home',
            'core:contact',
            'core:privacy',
            'core:accessibility',
            'about:index',
            'concerts:index',
            'workshops:index',
            'media_content:index',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == 'core:home':
            return 1.0
        elif item in ['concerts:index', 'workshops:index']:
            return 0.8
        return 0.5


class ConcertSitemap(Sitemap):
    """Sitemap for concert pages."""
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Concert.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class WorkshopSitemap(Sitemap):
    """Sitemap for workshop pages."""
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Workshop.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


sitemaps = {
    'static': StaticViewSitemap,
    'concerts': ConcertSitemap,
    'workshops': WorkshopSitemap,
}
