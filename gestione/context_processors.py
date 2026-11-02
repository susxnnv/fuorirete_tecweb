
from .models import Notifica


def notifiche_non_lette(request):

    # Utente anonimo
    if not request.user.is_authenticated:
        return {
            'navbar_notifiche_non_lette': 0
        }

    # Utente senza profilo
    if not hasattr(request.user, 'profilo'):
        return {
            'navbar_notifiche_non_lette': 0
        }

    # Contiamo le notifiche non lette
    # dell'utente autenticato.
    numero = Notifica.objects.filter(
        destinatario=request.user.profilo,
        letta=False
    ).count()

    return {
        'navbar_notifiche_non_lette': numero
    }
