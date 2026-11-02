from django.urls import path

from .views import (
        HomePubblicaView,
        RegistrazioneView,
        CreazioneProfiloView,
        AccediView,
        EsciView,
        HomeView,
        PersoneView,
        CommunityView,
        ProfiloView,
        NotificheView,
        AnteprimaProfiloView,
        ModificaProfiloView,
        CambiaPasswordView,
        EliminaAccountView,
        DettaglioPersonaView,
        ValutaPersonaView,
        ChatPrivataView,
        MatchChatView,
        AnnullaMatchView,
        LikeRicevutiView,
        RispondiLikeRicevutoView,
        SelezioneInteressiView,
        ModificaInteressiView,
        DettaglioCommunityView,
        CreazioneCommunityView,
        SelezioneInteressiCommunityView,
        CommunityGestiteView,
        ModificaCommunityView,
        ModificaInteressiCommunityView,
        EliminaCommunityView,
        InviaRichiestaCommunityView,
        AnnullaRichiestaCommunityView,
        GestioneRichiesteCommunityView,
        GestisciRichiestaCommunityView,
        EsciCommunityView,
        ChatGruppoView,
        ValutaCommunityView,
        EventiCommunityView,
        GestioneEventiCommunityView,
        CreazioneEventoCommunityView,
        ModificaEventoCommunityView,
        EliminaEventoCommunityView,
        ApriNotificaView,
    )

urlpatterns = [

    # HOME PUBBLICA + AUTENTICAZIONE E CREAZIONE PROFILO
    path("", HomePubblicaView.as_view(), name="home_pubblica"),
    path('registrazione/', RegistrazioneView.as_view(), name='registrazione'),
    path('creazione-profilo/', CreazioneProfiloView.as_view(), name='creazione_profilo'), 
    path('login/', AccediView.as_view(), name='login'),
    path('logout/', EsciView.as_view(), name='logout'),
    path('profilo/selezione-interessi/', SelezioneInteressiView.as_view(), name='selezione_interessi'),

    # HOME PRIVATA
    path('home/', HomeView.as_view(), name='home'),
    path('persone/', PersoneView.as_view(), name='persone'),
    path('community/', CommunityView.as_view(), name='community'),
    path('profilo/', ProfiloView.as_view(), name='profilo'),
    path('notifiche/', NotificheView.as_view(), name='notifiche'),

    # PROFILO
    path('profilo/anteprima/', AnteprimaProfiloView.as_view(), name='anteprima_profilo'),
    path('profilo/modifica/', ModificaProfiloView.as_view(), name='modifica_profilo'),
    path('profilo/modifica/modifica-interessi/', ModificaInteressiView.as_view(), name='modifica_interessi'),
    path('profilo/cambia-password/', CambiaPasswordView.as_view(), name='cambia_password'),
    path('profilo/elimina-account/', EliminaAccountView.as_view(), name='elimina_account'),
    path('profilo/match-chat/', MatchChatView.as_view(), name="match_chat"),
    path('profilo/annulla-match/<int:pk>', AnnullaMatchView.as_view(), name='annulla_match'),
    path('profilo/like-ricevuti/', LikeRicevutiView.as_view(), name='like_ricevuti'),
    path('profilo/like-ricevuti/<int:pk>/rispondi/', RispondiLikeRicevutoView.as_view(), name='rispondi_like_ricevuto'),
    path('profilo/community-gestite/', CommunityGestiteView.as_view(), name='community_gestite'),
    path('profilo/community-gestite/<int:pk>/modifica/', ModificaCommunityView.as_view(), name='modifica_community'),
    path('profilo/community-gestite/<int:pk>/modifica-interessi/', ModificaInteressiCommunityView.as_view(), name='modifica_interessi_community'),
    path('profilo/community-gestite/<int:pk>/elimina/', EliminaCommunityView.as_view(), name='elimina_community'),

    # PERSONE
    path('persone/<int:pk>/', DettaglioPersonaView.as_view(), name='dettaglio_persona'),
    path('persone/<int:pk>/valuta/', ValutaPersonaView.as_view(), name='valuta_persona'),
    path('chat/<int:pk>/', ChatPrivataView.as_view(), name='chat_privata'),

    # COMMUNITY
    path('community/<int:pk>/', DettaglioCommunityView.as_view(), name='dettaglio_community'),
    path('community/crea/', CreazioneCommunityView.as_view(), name='creazione_community'),
    path('community/<int:pk>/selezione-interessi', SelezioneInteressiCommunityView.as_view(), name='selezione_interessi_community'),
    path('community/<int:pk>/richiedi/', InviaRichiestaCommunityView.as_view(), name='invia_richiesta_community'),
    path('community/<int:pk>/annulla-richiesta/', AnnullaRichiestaCommunityView.as_view(), name='annulla_richiesta_community'),
    path('profilo/community-gestite/<int:pk>/richieste/', GestioneRichiesteCommunityView.as_view(), name='gestione_richieste_community'),
    path('profilo/community-gestite/<int:pk>/richieste/<int:richiesta_pk>/gestisci/', GestisciRichiestaCommunityView.as_view(), name='gestisci_richiesta_community'),
    path('community/<int:pk>/esci/', EsciCommunityView.as_view(), name='esci_community'),
    path('community/<int:pk>/chat/', ChatGruppoView.as_view(), name='chat_gruppo'),
    path('community/<int:pk>/valuta/', ValutaCommunityView.as_view(), name='valuta_community'),

    # EVENTI
    path('community/<int:pk>/eventi/', EventiCommunityView.as_view(), name='eventi_community'),
    path('profilo/community-gestite/<int:pk>/eventi/', GestioneEventiCommunityView.as_view(), name='gestione_eventi_community'),
    path('profilo/community-gestite/<int:pk>/eventi/crea/', CreazioneEventoCommunityView.as_view(), name='creazione_evento_community'),
    path('profilo/community-gestite/<int:pk>/eventi/<int:evento_pk>/modifica/', ModificaEventoCommunityView.as_view(), name='modifica_evento_community'),
    path('profilo/community-gestite/<int:pk>/eventi/<int:evento_pk>/elimina/', EliminaEventoCommunityView.as_view(), name='elimina_evento_community'),

    # NOTIFICHE
    path('notifiche/<int:pk>/apri/', ApriNotificaView.as_view(), name='apri_notifica'),
]