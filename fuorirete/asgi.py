
import os

from django.core.asgi import get_asgi_application

from channels.routing import (
    ProtocolTypeRouter,
    URLRouter,
)

from channels.auth import AuthMiddlewareStack

from channels.security.websocket import (
    AllowedHostsOriginValidator,
)


os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'fuorirete.settings'
)

# Inizializziamo Django prima di importare il
# routing che utilizza i Consumer e i modelli.
django_asgi_app = get_asgi_application()

from gestione.routing import websocket_urlpatterns


application = ProtocolTypeRouter({

    # Le normali richieste HTTP continuano
    # a essere gestite da Django.
    'http': django_asgi_app,

    # Le connessioni WebSocket vengono
    # instradate ai Consumer.
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),

})
