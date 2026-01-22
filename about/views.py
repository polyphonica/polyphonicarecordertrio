from django.shortcuts import render
from .models import PlayerBio, TrioInfo


def index(request):
    """About page with trio info and player biographies."""
    trio_info = TrioInfo.objects.first()
    players = PlayerBio.objects.filter(is_active=True).order_by('display_order')

    context = {
        'trio_info': trio_info,
        'players': players,
    }
    return render(request, 'about/index.html', context)
