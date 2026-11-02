from django.contrib import admin

from .models import (
    Profilo,
    Interesse,
    Like,
    Dislike,
    MessaggioPrivato,
    Community,
    RichiestaCommunity,
    Evento,
    MessaggioCommunity,
    ValutazioneCommunity,
    Notifica,
)

admin.site.register(Profilo)
admin.site.register(Interesse)
admin.site.register(Like)
admin.site.register(Dislike)
admin.site.register(MessaggioPrivato)
admin.site.register(Community)
admin.site.register(RichiestaCommunity)
admin.site.register(Evento)
admin.site.register(MessaggioCommunity)
admin.site.register(ValutazioneCommunity)
admin.site.register(Notifica)