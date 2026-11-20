# Definisce gli indirizzi WebSocket, stabilendo quale Consumer deve gestire una determinata connessioni
# Associa gli URL delle connessioni WebSocket ai ConsumerDjanoChannels

from django.urls import path

from .consumers import (
    ChatPrivataConsumer,
    ChatGruppoConsumer,
)


websocket_urlpatterns = [

    # Chat privata tra due utenti con Match.
    path(
        'ws/chat/<int:pk>/',
        ChatPrivataConsumer.as_asgi(),
        name='ws_chat_privata'
    ),

    # Chat di gruppo di una community.
    path(
        'ws/community/<int:pk>/chat/',
        ChatGruppoConsumer.as_asgi(),
        name='ws_chat_gruppo'
    ),

]
