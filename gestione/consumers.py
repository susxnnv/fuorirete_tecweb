
import json

from channels.auth import get_user
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Profilo,
    Like,
    MessaggioPrivato,
    Notifica,
)

from django.utils.formats import date_format
from .models import Community, MessaggioCommunity


class ChatPrivataConsumer(AsyncWebsocketConsumer):

    # ==========================================
    # CONNESSIONE
    # ==========================================

    async def connect(self):

        utente = self.scope['user']

        # La connessione è consentita soltanto
        # agli utenti autenticati.
        if not utente.is_authenticated:
            await self.close(code=4401)
            return

        # Recuperiamo l'ID dell'altra persona
        # direttamente dall'URL WebSocket.
        self.altra_persona_id = (
            self.scope['url_route']['kwargs']['pk']
        )

        # Verifichiamo profilo completo e Match.
        mio_profilo_id = await self.verifica_accesso(
            utente.pk,
            self.altra_persona_id
        )

        if mio_profilo_id is None:
            await self.close(code=4403)
            return

        self.mio_profilo_id = mio_profilo_id

        # Nome univoco della stanza privata.
        # I due utenti ottengono lo stesso nome
        # indipendentemente da chi si collega.
        primo, secondo = sorted([
            self.mio_profilo_id,
            self.altra_persona_id
        ])

        self.nome_gruppo = (
            f'chat_privata_{primo}_{secondo}'
        )

        # Aggiungiamo la connessione al gruppo.
        await self.channel_layer.group_add(
            self.nome_gruppo,
            self.channel_name
        )

        # Accettiamo il WebSocket.
        await self.accept()

        await self.send(text_data=json.dumps({
            'tipo': 'connessione',
            'stato': 'connesso'
        }))


    # ==========================================
    # DISCONNESSIONE
    # ==========================================

    async def disconnect(self, close_code):

        # Rimuoviamo questa connessione dal gruppo.
        if hasattr(self, 'nome_gruppo'):
            await self.channel_layer.group_discard(
                self.nome_gruppo,
                self.channel_name
            )


    # ==========================================
    # RICEZIONE MESSAGGI
    # ==========================================

    async def receive(
        self,
        text_data=None,
        bytes_data=None
    ):

        if text_data is None:
            return

        # Il browser deve inviare un JSON valido.
        try:
            dati = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            await self.invia_errore(
                'Formato del messaggio non valido.'
            )
            return

        if not isinstance(dati, dict):
            await self.invia_errore(
                'Formato del messaggio non valido.'
            )
            return

        if dati.get('tipo') != 'messaggio':
            return

        testo = dati.get('testo')

        if not isinstance(testo, str):
            await self.invia_errore(
                'Il testo del messaggio non è valido.'
            )
            return

        testo = testo.strip()

        if not testo:
            await self.invia_errore(
                'Scrivi un messaggio prima di inviarlo.'
            )
            return

        if len(testo) > 2000:
            await self.invia_errore(
                'Il messaggio non può superare 2000 caratteri.'
            )
            return

        # Controlliamo nuovamente la sessione:
        # potrebbe essere stata chiusa dopo
        # l'apertura del WebSocket.
        utente = await get_user(self.scope)

        if (
            not utente.is_authenticated
            or utente.pk != self.scope['user'].pk
        ):
            await self.close(code=4401)
            return

        # Salviamo il messaggio e la notifica.
        # La funzione ricontrolla anche il Match.
        messaggio = await self.salva_messaggio(
            utente.pk,
            self.altra_persona_id,
            testo
        )

        if messaggio is None:
            await self.invia_errore(
                'Non è possibile inviare il messaggio. '
                'Verifica che il Match sia ancora valido.'
            )
            await self.close(code=4403)
            return

        # Inviamo il messaggio a tutti i Consumer
        # collegati alla stessa stanza.
        await self.channel_layer.group_send(
            self.nome_gruppo,
            {
                'type': 'chat_messaggio',
                'messaggio': messaggio,
            }
        )


    # ==========================================
    # DISTRIBUZIONE AL CLIENT
    # ==========================================

    async def chat_messaggio(self, evento):

        # Prima di consegnare il messaggio,
        # verifichiamo che il Match esista ancora
        # e che il profilo sia ancora completo.
        utente = await get_user(self.scope)

        if (
            not utente.is_authenticated
            or utente.pk != self.scope['user'].pk
        ):
            await self.close(code=4401)
            return

        profilo_id = await self.verifica_accesso(
            utente.pk,
            self.altra_persona_id
        )

        if profilo_id != self.mio_profilo_id:
            await self.close(code=4403)
            return

        await self.send(text_data=json.dumps({
            'tipo': 'messaggio',
            **evento['messaggio']
        }))


    # ==========================================
    # INVIO ERRORE
    # ==========================================

    async def invia_errore(self, testo):

        await self.send(text_data=json.dumps({
            'tipo': 'errore',
            'testo': testo
        }))


    # ==========================================
    # CONTROLLO PERMESSI
    # ==========================================

    @database_sync_to_async
    def verifica_accesso(
        self,
        utente_id,
        altra_persona_id
    ):

        mio_profilo = Profilo.objects.filter(
            user_id=utente_id
        ).first()

        if mio_profilo is None:
            return None

        # Il profilo deve avere completato
        # la selezione iniziale degli interessi.
        if not mio_profilo.interessi.exists():
            return None

        if mio_profilo.pk == altra_persona_id:
            return None

        # L'altra persona deve esistere.
        if not Profilo.objects.filter(
            pk=altra_persona_id
        ).exists():
            return None

        # Il Match deriva da due Like reciproci.
        mio_like = Like.objects.filter(
            mittente_id=mio_profilo.pk,
            destinatario_id=altra_persona_id
        ).exists()

        suo_like = Like.objects.filter(
            mittente_id=altra_persona_id,
            destinatario_id=mio_profilo.pk
        ).exists()

        if not (mio_like and suo_like):
            return None

        return mio_profilo.pk


    # ==========================================
    # SALVATAGGIO NEL DATABASE
    # ==========================================

    @database_sync_to_async
    def salva_messaggio(
        self,
        utente_id,
        altra_persona_id,
        testo
    ):

        try:
            mio_profilo = Profilo.objects.get(
                user_id=utente_id
            )

            altra_persona = Profilo.objects.get(
                pk=altra_persona_id
            )

            with transaction.atomic():

                # Il modello MessaggioPrivato
                # verifica già i Like reciproci.
                messaggio = MessaggioPrivato(
                    mittente=mio_profilo,
                    destinatario=altra_persona,
                    testo=testo
                )

                messaggio.full_clean()
                messaggio.save()

                # Manteniamo la notifica prevista
                # dalla precedente view HTTP.
                Notifica.objects.create(
                    destinatario=altra_persona,
                    tipo='MESSAGGIO_PRIVATO',
                    testo=(
                        f'{mio_profilo.nome} ti ha inviato '
                        f'un nuovo messaggio.'
                    ),
                    profilo_collegato=mio_profilo
                )

            # Convertiamo la data nel fuso italiano
            # per mostrarla coerentemente nella chat.
            data_locale = timezone.localtime(
                messaggio.data_ora
            )

            return {
                'id': messaggio.pk,
                'mittente_id': mio_profilo.pk,
                'testo': messaggio.testo,
                'data_ora': data_locale.isoformat(),
                'giorno': data_locale.strftime('%Y-%m-%d'),
                'orario': data_locale.strftime('%H:%M'),
                'data_etichetta': (
                    f'{data_locale.day} '
                    f'{data_locale.strftime("%B")} '
                    f'{data_locale.year}'
                ),
            }

        except (
            Profilo.DoesNotExist,
            ValidationError,
        ):
            return None


# ==========================================
# CHAT DI GRUPPO - COMMUNITY
# ==========================================

class ChatGruppoConsumer(AsyncWebsocketConsumer):

    # ======================================
    # CONNESSIONE
    # ======================================

    async def connect(self):

        utente = await get_user(self.scope)

        if not utente.is_authenticated:
            await self.close(code=4401)
            return

        self.utente_id = utente.pk

        self.community_id = (
            self.scope['url_route']['kwargs']['pk']
        )

        # Verifichiamo che l'utente sia
        # organizzatore o membro e che
        # la community sia completa.
        self.profilo_id = await self.verifica_accesso(
            self.utente_id,
            self.community_id
        )

        if self.profilo_id is None:
            await self.close(code=4403)
            return

        # Identifica univocamente la stanza.
        self.nome_gruppo = (
            f'community_chat_{self.community_id}'
        )

        await self.channel_layer.group_add(
            self.nome_gruppo,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'tipo': 'connessione',
            'stato': 'connesso'
        }))


    # ======================================
    # DISCONNESSIONE
    # ======================================

    async def disconnect(self, close_code):

        if hasattr(self, 'nome_gruppo'):
            await self.channel_layer.group_discard(
                self.nome_gruppo,
                self.channel_name
            )


    # ======================================
    # RICEZIONE DEI MESSAGGI
    # ======================================

    async def receive(
        self,
        text_data=None,
        bytes_data=None
    ):

        if text_data is None:
            return

        try:
            dati = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            await self.invia_errore(
                'Formato del messaggio non valido.'
            )
            return

        if not isinstance(dati, dict):
            await self.invia_errore(
                'Formato del messaggio non valido.'
            )
            return

        if dati.get('tipo') != 'messaggio':
            return

        testo = dati.get('testo')

        if not isinstance(testo, str):
            await self.invia_errore(
                'Il testo non è valido.'
            )
            return

        testo = testo.strip()

        if not testo:
            await self.invia_errore(
                'Scrivi un messaggio prima di inviarlo.'
            )
            return

        if len(testo) > 2000:
            await self.invia_errore(
                'Il messaggio non può superare 2000 caratteri.'
            )
            return

        utente = await get_user(self.scope)

        if (
            not utente.is_authenticated
            or utente.pk != self.utente_id
        ):
            await self.close(code=4401)
            return

        # La modalità anteprima è di sola lettura,
        # come nella ChatGruppoView esistente.
        query_string = self.scope.get(
            'query_string', b''
        ).decode('utf-8', errors='replace')

        from urllib.parse import parse_qs

        parametri = parse_qs(query_string)

        if (
            parametri.get('anteprima') == ['1']
            and await self.sono_organizzatore(
                self.profilo_id,
                self.community_id
            )
        ):
            await self.invia_errore(
                'Non puoi scrivere in modalità anteprima.'
            )
            return

        # Verifica permessi e salvataggio
        # sono effettuati lato server.
        messaggio = await self.salva_messaggio(
            self.profilo_id,
            self.community_id,
            testo
        )

        if messaggio is None:
            await self.invia_errore(
                'Non è possibile inviare il messaggio. '
                'Verifica di essere ancora membro.'
            )
            await self.close(code=4403)
            return

        # Broadcast a tutti i partecipanti
        # collegati alla stessa community.
        await self.channel_layer.group_send(
            self.nome_gruppo,
            {
                'type': 'chat_messaggio',
                'messaggio': messaggio
            }
        )


    # ======================================
    # CONSEGNA DEL MESSAGGIO
    # ======================================

    async def chat_messaggio(self, evento):

        utente = await get_user(self.scope)

        if (
            not utente.is_authenticated
            or utente.pk != self.utente_id
        ):
            await self.close(code=4401)
            return

        # Controlliamo i permessi anche
        # prima di consegnare i messaggi.
        profilo_id = await self.verifica_accesso(
            self.utente_id,
            self.community_id
        )

        if profilo_id != self.profilo_id:
            await self.close(code=4403)
            return

        await self.send(text_data=json.dumps({
            'tipo': 'messaggio',
            **evento['messaggio']
        }))


    # ======================================
    # MESSAGGI DI ERRORE
    # ======================================

    async def invia_errore(self, testo):

        await self.send(text_data=json.dumps({
            'tipo': 'errore',
            'testo': testo
        }))


    # ======================================
    # CONTROLLO DEGLI ACCESSI
    # ======================================

    @database_sync_to_async
    def verifica_accesso(
        self,
        utente_id,
        community_id
    ):

        profilo = Profilo.objects.filter(
            user_id=utente_id
        ).first()

        if profilo is None:
            return None

        if not profilo.interessi.exists():
            return None

        gruppo = Community.objects.filter(
            pk=community_id
        ).first()

        if gruppo is None:
            return None

        # La community deve essere completa.
        if not gruppo.interessi.exists():
            return None

        organizzatore = (
            gruppo.organizzatore_id == profilo.pk
        )

        membro = gruppo.membri.filter(
            pk=profilo.pk
        ).exists()

        if not (organizzatore or membro):
            return None

        return profilo.pk


    # ======================================
    # VERIFICA ORGANIZZATORE
    # ======================================

    @database_sync_to_async
    def sono_organizzatore(
        self,
        profilo_id,
        community_id
    ):

        return Community.objects.filter(
            pk=community_id,
            organizzatore_id=profilo_id
        ).exists()


    # ======================================
    # SALVATAGGIO MESSAGGIO + NOTIFICHE
    # ======================================

    @database_sync_to_async
    def salva_messaggio(
        self,
        profilo_id,
        community_id,
        testo
    ):

        try:

            with transaction.atomic():

                profilo = Profilo.objects.get(
                    pk=profilo_id
                )

                gruppo = Community.objects.get(
                    pk=community_id
                )

                # Ricontrolliamo la partecipazione.
                organizzatore = (
                    gruppo.organizzatore_id == profilo.pk
                )

                membro = gruppo.membri.filter(
                    pk=profilo.pk
                ).exists()

                if not gruppo.interessi.exists():
                    return None

                if not (organizzatore or membro):
                    return None

                messaggio = MessaggioCommunity(
                    community=gruppo,
                    autore=profilo,
                    testo=testo
                )

                messaggio.full_clean()
                messaggio.save()

                # Manteniamo la stessa logica
                # delle notifiche nella view HTTP.
                altri_membri = gruppo.membri.exclude(
                    pk=profilo.pk
                )

                Notifica.objects.bulk_create([
                    Notifica(
                        destinatario=partecipante,
                        tipo='MESSAGGIO_COMMUNITY',
                        testo=(
                            f'{profilo.nome} ha scritto '
                            f'nella chat di {gruppo.titolo}.'
                        ),
                        profilo_collegato=profilo,
                        community_collegata=gruppo
                    )
                    for partecipante in altri_membri
                ])

            data_locale = timezone.localtime(
                messaggio.data_ora
            )

            return {
                'id': messaggio.pk,
                'autore_id': profilo.pk,
                'autore_nome': profilo.nome,
                'autore_foto': (
                    profilo.foto.url
                    if profilo.foto
                    else None
                ),
                'testo': messaggio.testo,
                'data_ora': data_locale.isoformat(),
                'giorno': data_locale.strftime('%Y-%m-%d'),
                'orario': data_locale.strftime('%H:%M'),
                'data_etichetta': date_format(
                    data_locale,
                    'j F Y'
                )
            }

        except (
            Profilo.DoesNotExist,
            Community.DoesNotExist,
            ValidationError
        ):
            return None
