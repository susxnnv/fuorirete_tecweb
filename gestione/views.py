from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User
from django.db.models import ProtectedError, RestrictedError, Q, Count, Sum, prefetch_related_objects
from django.contrib import messages
from django.views import View
from django.http import HttpResponseRedirect, QueryDict, Http404
from django.core.exceptions import ValidationError
from django.utils import timezone

from django.views.generic import (
    TemplateView, 
    CreateView, 
    UpdateView, 
    DeleteView, 
    DetailView, 
    FormView,
)

from .models import (
    Community, 
    Profilo,
    Like,
    Dislike,
    Interesse,
    MessaggioPrivato,
    RichiestaCommunity,
    Notifica,
    MessaggioCommunity,
    ValutazioneCommunity,
    Evento,
)

from .forms import (
    RegistrazioneForm, 
    CreazioneProfiloForm, 
    SelezioneInteressiForm,
    CreazioneCommunityForm,
    EventoForm,
)

# HOME PUBBLICA

# ==========================================
# RANKING COMMUNITY
# ==========================================

def recupera_community_con_valutazioni():

    # Recuperiamo soltanto le community
    # che hanno completato la selezione interessi.

    community_complete = (
        Community.objects
        .filter(interessi__isnull=False)
        .values('pk')
    )

    return (
        Community.objects
        .filter(pk__in=community_complete)
        .select_related('organizzatore')
        .prefetch_related('interessi__padre')
        .annotate(
            numero_valutazioni=Count('valutazioni'),
            somma_valutazioni=Sum('valutazioni__voto')
        )
    )


def calcola_punteggio_pubblico(community):
    """
    Media ponderata bayesiana semplificata.

    Media iniziale: 3
    Peso iniziale: 5 valutazioni

    Restituisce un punteggio sulla scala 1-5.
    """

    numero = community.numero_valutazioni
    somma = community.somma_valutazioni or 0

    community.media_valutazioni = (
        somma / numero if numero else None
    )

    community.punteggio_pubblico = (
        somma + 5 * 3
    ) / (numero + 5)

    return community.punteggio_pubblico


def calcola_compatibilita_community(
    community,
    profilo
):
    """
    Compatibilità personale su scala 0-10.

    Stessa città: +4

    Interessi:
    - identici: +2
    - macro/sottocategoria: +1
    - massimo: 6

    Ogni interesse può essere abbinato
    una sola volta.
    """

    punteggio = 0

    if (
        community.citta.strip().casefold()
        == profilo.citta.strip().casefold()
    ):
        punteggio += 4

    miei_interessi = list(profilo.interessi.all())
    interessi_community = list(community.interessi.all())

    miei_ids = {
        interesse.pk for interesse in miei_interessi
    }

    community_ids = {
        interesse.pk for interesse in interessi_community
    }

    # Prima contiamo le corrispondenze esatte.
    esatti = miei_ids & community_ids

    punti_interessi = len(esatti) * 2

    # Gli interessi esatti non possono essere
    # utilizzati nuovamente negli abbinamenti parziali.
    miei_rimanenti = [
        interesse for interesse in miei_interessi
        if interesse.pk not in esatti
    ]

    community_rimanenti = [
        interesse for interesse in interessi_community
        if interesse.pk not in esatti
    ]

    community_usati = set()

    # Corrispondenze parziali:
    # macrocategoria e sottocategoria.
    for mio_interesse in miei_rimanenti:

        for interesse_community in community_rimanenti:

            if interesse_community.pk in community_usati:
                continue

            collegati = (
                mio_interesse.padre_id
                == interesse_community.pk
                or
                interesse_community.padre_id
                == mio_interesse.pk
            )

            if collegati:
                punti_interessi += 1

                community_usati.add(
                    interesse_community.pk
                )

                break

    punteggio += min(punti_interessi, 6)

    return punteggio

# home pubblica 

# ==========================================
# HOME PUBBLICA
# ==========================================

# ==========================================
# HOME PUBBLICA
# ==========================================

class HomePubblicaView(TemplateView):

    template_name = 'gestione/home_pubblica.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # ======================================
        # COMMUNITY PUBBLICHE
        # ======================================

        community = list(
            recupera_community_con_valutazioni()
        )

        for gruppo in community:
            calcola_punteggio_pubblico(gruppo)

        # Ordinamento:
        # 1. Punteggio ponderato decrescente
        # 2. ID crescente a parità di punteggio

        community.sort(
            key=lambda gruppo: (
                -gruppo.punteggio_pubblico,
                gruppo.pk
            )
        )

        context['community'] = community

        # ======================================
        # STATISTICHE GENERALI DI FUORIRETE
        # ======================================

        # Numero di utenti con un profilo creato.
        context['totale_utenti'] = (
            Profilo.objects.count()
        )

        # Numero di community complete,
        # con almeno un interesse associato.
        context['totale_community'] = (
            Community.objects
            .filter(interessi__isnull=False)
            .distinct()
            .count()
        )

        # Numero totale di eventi creati,
        # compresi quelli già trascorsi.
        context['totale_eventi'] = (
            Evento.objects.count()
        )

        return context


# GESTIONE PROFILO

# registrazione 
class RegistrazioneView(CreateView):
    form_class = RegistrazioneForm
    template_name = 'gestione/registrazione.html'
    success_url = reverse_lazy('creazione_profilo')

    # dispatch: metodo che decide se proseguire con il normale funzionamento della view
    def dispatch(self, request, *args, **kwargs):

        # se l'utente è autenticato
        if request.user.is_authenticated:

            # se l'utente è autenticato e ha un profilo associato --> home
            if hasattr(request.user, 'profilo'):
                return redirect('home')

            # se l'utente è autenticato ma non ha un profilo associato
            return redirect('creazione_profilo')

        return super().dispatch(request, *args, **kwargs)

    # se il form è valido
    def form_valid(self, form):

        # salvataggio dello user nel db
        response = super().form_valid(form)

        # autenticazione automatica
        login(self.request, self.object)

        return response

# creazione profilo 

# ==========================================
# CREAZIONE PROFILO - PASSAGGIO 1 DI 2
# ==========================================

class CreazioneProfiloView(LoginRequiredMixin, UpdateView):

    model = Profilo
    form_class = CreazioneProfiloForm

    template_name = 'gestione/creazione_profilo.html'

    success_url = reverse_lazy('selezione_interessi')

    # ======================================
    # CONTROLLO DEGLI ACCESSI
    # ======================================

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Se il profilo è già completo,
        # non permettiamo di ripetere la creazione.

        if hasattr(request.user, 'profilo'):

            if request.user.profilo.interessi.exists():
                return redirect('home')

        # Chi non ha ancora completato gli interessi
        # può accedere al primo passaggio anche
        # se il profilo è già stato creato.

        return super().dispatch(request, *args, **kwargs)

    # ======================================
    # RECUPERO DEL PROFILO
    # ======================================

    def get_object(self, queryset=None):

        # Recuperiamo esclusivamente il profilo
        # dell'utente autenticato, se esiste.

        # Se non esiste, restituiamo None:
        # il form consentirà di crearne uno nuovo.

        return Profilo.objects.filter(
            user=self.request.user
        ).first()

    # ======================================
    # SALVATAGGIO DEL PROFILO
    # ======================================

    def form_valid(self, form):

        # L'utente associato al profilo
        # è sempre quello autenticato.

        form.instance.user = self.request.user

        # Se il profilo esiste già, UpdateView
        # aggiorna la stessa istanza.
        #
        # Se non esiste, ne crea una nuova.

        with transaction.atomic():
            return super().form_valid(form)

# Selezione degli interessi nella creazione del profilo
class SelezioneInteressiView(LoginRequiredMixin, FormView):
    form_class = SelezioneInteressiForm
    template_name = 'gestione/selezione_interessi.html'
    success_url = reverse_lazy('home')

    # controllo degli accessi
    def dispatch(self, request, *args, **kwargs):

        # accesso consentito solo agli utenti autenticati
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Non è possibile scegliere gli interessi senza aver prima creato il profilo
        if not hasattr(request.user, 'profilo'):
            return redirect('creazione_profilo')

        # Se la selezione è già stata completata, non ripetiamo la creazione iniziale.
        if request.user.profilo.interessi.exists():
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # Recuperiamo soltanto le macrocategorie.
        # Le sottocategorie sono caricate attraverso la relazione inversa "sottointeressi".
        context['categorie'] = (
            Interesse.objects
            .filter(padre__isnull=True)
            .prefetch_related('sottointeressi')
            .order_by('nome')
        )

        return context

    # verifica se il form è valido
    def form_valid(self, form):

        profilo = self.request.user.profilo

        # Salviamo gli interessi scelti nella relazione ManyToMany già presente sul modello Profilo
        with transaction.atomic():
            profilo.interessi.set(
                form.cleaned_data['interessi']
            )

        return super().form_valid(form)


# login
class AccediView(LoginView):

    template_name = 'gestione/login.html'

    # decide dove mandare l'utente quando il login è riuscito 
    def get_success_url(self):

        # Utente con profilo già creato
        if hasattr(self.request.user, 'profilo'):

            # Non ha ancora scelto gli interessi
            if not self.request.user.profilo.interessi.exists():
                return str(reverse_lazy('selezione_interessi'))

            # Profilo completo
            return str(reverse_lazy('home'))

        # Non ha ancora creato il profilo
        return str(reverse_lazy('creazione_profilo'))


# logout
class EsciView(LogoutView):
    next_page = reverse_lazy('home_pubblica')

# CONTROLLO ACCESSO ALL'AREA AUTENTICATA
# mixin aggiunge un comportamento riutilizzabile ad altra classi attraverso ereditarietà:
# distingue le 3 tipologie di utente --> anonimo (deve fare login), autenticato senza profilo (deve creare il profilo), autenticato con profilo (accesso alla home)

class ProfiloRichiestoMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):

        # Utente non autenticato:
        # LoginRequiredMixin gestisce il redirect al login
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Utente autenticato senza profilo:
        # deve completare i dati personali
        if not hasattr(request.user, 'profilo'):
            return redirect('creazione_profilo')

        # Utente con profilo ma senza interessi:
        # deve completare il secondo passaggio
        if not request.user.profilo.interessi.exists():
            return redirect('selezione_interessi')

        # Profilo completo: accesso consentito
        return super().dispatch(request, *args, **kwargs)


# HOME AUTENTICATA 
# in questo caso tutte le classi sono protette dal mixin 
# (possono accedere solo utenti con profilo + account)


# ==========================================
# HOME AUTENTICATA
# ==========================================

class HomeView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/home.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # ======================================
        # STATISTICHE GENERALI DI FUORIRETE
        # ======================================

        # Utenti che hanno creato un profilo.
        context['totale_utenti'] = (
            Profilo.objects.count()
        )

        # Community pubblicate, con interessi
        # già selezionati e quindi complete.
        context['totale_community'] = (
            Community.objects
            .filter(interessi__isnull=False)
            .distinct()
            .count()
        )

        # Numero complessivo degli eventi creati,
        # inclusi quelli già trascorsi.
        context['totale_eventi'] = (
            Evento.objects.count()
        )

        return context


# COMMUNITY

# ==========================================
# SCOPERTA COMMUNITY AUTENTICATA
# ==========================================

class CommunityView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/community.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        mio_profilo = self.request.user.profilo
        parametri = self.request.GET

        # ======================================
        # 1. RECUPERO E VALIDAZIONE FILTRI
        # ======================================

        ricerca = parametri.get('ricerca', '').strip()
        citta = parametri.get('citta', '').strip()

        if len(ricerca) > 100:
            ricerca = ricerca[:100]

        if len(citta) > 100:
            citta = citta[:100]

        partecipazione = parametri.get(
            'partecipazione',
            'tutte'
        )

        if partecipazione not in (
            'tutte',
            'partecipate',
            'non_partecipate'
        ):
            partecipazione = 'tutte'

        interessi_ids = []

        for valore in parametri.getlist('interessi'):

            try:
                identificativo = int(valore)

                if identificativo > 0:
                    interessi_ids.append(identificativo)

            except (ValueError, TypeError):
                continue

        interessi_ids = list(
            dict.fromkeys(interessi_ids)
        )

        # Catalogo completo per il popup.
        catalogo = list(
            Interesse.objects
            .select_related('padre')
            .order_by('padre_id', 'nome')
        )

        interessi_per_id = {
            interesse.pk: interesse
            for interesse in catalogo
        }

        # Accettiamo solo gli ID realmente presenti.
        interessi_ids = [
            pk for pk in interessi_ids
            if pk in interessi_per_id
        ]

        # ======================================
        # 2. ESPANSIONE FILTRO INTERESSI
        # ======================================


        # ======================================
        # 2. ESPANSIONE FILTRO INTERESSI
        # ======================================

        # Una categoria generale comprende
        # anche le proprie sottocategorie.
        #
        # Una sottocategoria, invece, richiede
        # una corrispondenza esatta.

        interessi_ammessi = set(interessi_ids)

        if interessi_ids:

            for interesse in catalogo:

                # Includiamo le sottocategorie
                # delle categorie generali selezionate.

                if interesse.padre_id in interessi_ids:
                    interessi_ammessi.add(interesse.pk)

        # ======================================
        # 3. FILTRI RIGIDI SUL DATABASE
        # ======================================

        community = recupera_community_con_valutazioni()

        # Ricerca SOLO nel titolo.
        if ricerca:
            community = community.filter(
                titolo__icontains=ricerca
            )

        # Città esatta, senza distinguere
        # maiuscole e minuscole.
        if citta:
            community = community.filter(
                citta__iexact=citta
            )

        # Almeno un interesse corrispondente.
        if interessi_ids:

            community_corrispondenti = (
                Community.objects
                .filter(interessi__pk__in=interessi_ammessi)
                .values('pk')
            )

            community = community.filter(
                pk__in=community_corrispondenti
            )

        # Community a cui partecipo.
        community_partecipate_ids = set(
            mio_profilo.community_partecipate
            .values_list('pk', flat=True)
        )

        if partecipazione == 'partecipate':

            community = community.filter(
                pk__in=community_partecipate_ids
            )

        elif partecipazione == 'non_partecipate':

            community = community.exclude(
                pk__in=community_partecipate_ids
            )

        # ======================================
        # 4. RANKING PERSONALIZZATO
        # ======================================

        # Prefetch degli interessi del mio profilo.
        prefetch_related_objects(
            [mio_profilo],
            'interessi'
        )

        mio_profilo_interessi = list(
            mio_profilo.interessi.all()
        )

        # Lista utilizzata per evitare query
        # ripetute durante il calcolo.
        mio_profilo._prefetched_objects_cache = {
            'interessi': mio_profilo_interessi
        }

        risultati = list(community)

        for gruppo in risultati:

            # Qualità ponderata: scala 1-5.
            qualita = calcola_punteggio_pubblico(
                gruppo
            )

            # Compatibilità: scala 0-10.
            compatibilita = (
                calcola_compatibilita_community(
                    gruppo,
                    mio_profilo
                )
            )

            # Ranking finale:
            # 60% compatibilità
            # 40% qualità ponderata.
            gruppo.punteggio_finale = (
                0.6 * compatibilita
                + 0.4 * (qualita * 2)
            )

            gruppo.compatibilita = compatibilita

            gruppo.gia_membro = (
                gruppo.pk in community_partecipate_ids
            )

            gruppo.organizzata_da_me = (
                gruppo.organizzatore_id == mio_profilo.pk
            )

        # Risultati migliori prima.
        risultati.sort(
            key=lambda gruppo: (
                -gruppo.punteggio_finale,
                gruppo.pk
            )
        )

        # ======================================
        # 5. CONTEXT TEMPLATE
        # ======================================

        context['community'] = risultati
        context['ricerca'] = ricerca
        context['filtro_citta'] = citta
        context['filtro_interessi'] = interessi_ids
        context['filtro_partecipazione'] = partecipazione

        context['interessi_disponibili'] = catalogo

        context['categorie_filtri'] = (
            Interesse.objects
            .filter(padre__isnull=True)
            .prefetch_related('sottointeressi')
            .order_by('nome')
        )

        context['filtri_attivi'] = bool(
            citta
            or interessi_ids
            or partecipazione != 'tutte'
        )

        context['numero_risultati'] = len(risultati)

        context['community_da_completare'] = (
            Community.objects
            .filter(
                organizzatore=self.request.user.profilo,
                interessi__isnull=True
            )
            .order_by('-data_creazione')
        )

        return context


# NOTIFICHE

# ==========================================
# ELENCO NOTIFICHE
# ==========================================

# ==========================================
# ELENCO NOTIFICHE
# ==========================================

class NotificheView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/notifiche.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        mio_profilo = self.request.user.profilo

        notifiche = list(
            Notifica.objects
            .filter(destinatario=mio_profilo)
            .select_related(
                'profilo_collegato',
                'community_collegata'
            )
            .order_by('-data_ora', '-pk')
        )

        # Recuperiamo le richieste legate alle
        # notifiche di partecipazione ricevute.

        richieste = RichiestaCommunity.objects.filter(
            community__organizzatore=mio_profilo
        )

        richieste_per_coppia = {
            (richiesta.community_id, richiesta.utente_id):
                richiesta
            for richiesta in richieste
        }

        # Evitiamo che vecchie notifiche riferite
        # alla stessa richiesta mostrino nuovi pulsanti.

        coppie_gia_viste = set()

        for notifica in notifiche:

            notifica.richiesta_pendente = None
            notifica.stato_richiesta = None

            if notifica.tipo != 'RICHIESTA_COMMUNITY':
                continue

            if (
                notifica.community_collegata_id is None
                or notifica.profilo_collegato_id is None
            ):
                continue

            coppia = (
                notifica.community_collegata_id,
                notifica.profilo_collegato_id
            )

            richiesta = richieste_per_coppia.get(coppia)

            if richiesta is None:
                continue

            notifica.stato_richiesta = richiesta.stato

            if coppia in coppie_gia_viste:
                continue

            coppie_gia_viste.add(coppia)

            if richiesta.stato == 'PENDING':
                notifica.richiesta_pendente = richiesta

        # Aprendo la pagina Notifiche, tutte le
        # notifiche non lette diventano lette.

        Notifica.objects.filter(
            destinatario=mio_profilo,
            letta=False
        ).update(letta=True)

        # Aggiorniamo anche gli oggetti già recuperati,
        # così la pagina mostra lo stato corretto.

        for notifica in notifiche:
            notifica.letta = True

        context['notifiche'] = notifiche

        context['numero_non_lette'] = 0

        return context


# PROFILO PERSONALE

# Home profilo personale

# ==========================================
# HOME PROFILO PERSONALE
# ==========================================

class ProfiloView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/profilo.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        mio_profilo = self.request.user.profilo

        # ======================================
        # CONTEGGIO DEI MATCH
        # ======================================

        like_ricevuti = Like.objects.filter(
            destinatario=mio_profilo
        ).values('mittente_id')

        numero_match = Like.objects.filter(
            mittente=mio_profilo,
            destinatario_id__in=like_ricevuti
        ).count()

        context['numero_match'] = numero_match

        # ======================================
        # PERCENTUALE COMPLETAMENTO PROFILO
        # ======================================

        campi_compilati = [
            bool(mio_profilo.nome.strip()),
            bool(mio_profilo.foto),
            bool(mio_profilo.data_nascita),
            bool(mio_profilo.genere),
            bool(mio_profilo.citta.strip()),
            bool(mio_profilo.occupazione),
            bool(mio_profilo.lingue),
            bool(mio_profilo.descrizione.strip()),
            bool(mio_profilo.cosa_cerca),
            mio_profilo.interessi.exists(),
        ]

        percentuale = (
            sum(campi_compilati) * 10
        )

        context['percentuale_completamento'] = percentuale

        return context


# Anteprima profilo
class AnteprimaProfiloView(ProfiloRichiestoMixin, TemplateView):
    template_name = 'gestione/anteprima_profilo.html'

# Modifica profilo
class ModificaProfiloView(ProfiloRichiestoMixin, UpdateView):

    model = Profilo
    form_class = CreazioneProfiloForm
    template_name = 'gestione/modifica_profilo.html'
    success_url = reverse_lazy('profilo')

    # Recupera esclusivamente il profilo dell'utente autenticato
    def get_object(self, queryset=None):
        return self.request.user.profilo


    def form_valid(self, form):

        risposta = super().form_valid(form)

        messages.success(
            self.request,
            'Profilo aggiornato correttamente!'
        )

        return risposta    

# Modifica interessi dal profilo
class ModificaInteressiView(ProfiloRichiestoMixin, FormView):

    form_class = SelezioneInteressiForm
    template_name = 'gestione/selezione_interessi.html'
    success_url = reverse_lazy('modifica_profilo')

    def get_initial(self):

        initial = super().get_initial()

        initial['interessi'] = [
            str(pk)
            for pk in self.request.user.profilo.interessi.values_list(
                'pk',
                flat=True
            )
        ]

        return initial

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # Recuperiamo le macrocategorie e i satelliti.
        context['categorie'] = (
            Interesse.objects
            .filter(padre__isnull=True)
            .prefetch_related('sottointeressi')
            .order_by('nome')
        )

        # Permette al template di distinguere
        # fra creazione e modifica.
        context['modalita_modifica'] = True

        return context

    def form_valid(self, form):

        profilo = self.request.user.profilo

        with transaction.atomic():

            profilo.interessi.set(
                form.cleaned_data['interessi']
            )

        messages.success(
            self.request,
            'Interessi aggiornati correttamente!'
        )

        return super().form_valid(form)


# cambio password
class CambiaPasswordView(ProfiloRichiestoMixin, PasswordChangeView):

    template_name = 'gestione/cambia_password.html'
    success_url = reverse_lazy('profilo')

    def form_valid(self, form):

        risposta = super().form_valid(form)

        messages.success(
            self.request,
            'Password modificata correttamente!'
        )

        return risposta


# eliminazione del proprio account
class EliminaAccountView(ProfiloRichiestoMixin, DeleteView):

    model = User
    template_name = 'gestione/elimina_account.html'
    success_url = reverse_lazy('home_pubblica')

    # Permette di eliminare esclusivamente l'utente autenticato.
    def get_object(self, queryset=None):
        return self.request.user

    # La cancellazione può avvenire solo dopo una richiesta POST.
    def form_valid(self, form):
        utente = self.get_object()

        try:
            with transaction.atomic():
                # Conserviamo il comportamento standard di eliminazione di Django, incluse le relazioni CASCADE.
                risposta = super().form_valid(form)

        except (ProtectedError, RestrictedError):
            messages.error(
                self.request,
                'Non è possibile eliminare l’account perché '
                'alcuni dati collegati ne impediscono la cancellazione.'
            )
            return redirect('elimina_account')

        # Invalidiamo la sessione dopo la cancellazione
        logout(self.request)

        return risposta

# SCOPERTA DELLE PERSONE 
class PersoneView(ProfiloRichiestoMixin, TemplateView):
    template_name = 'gestione/persone.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        mio_profilo = self.request.user.profilo
        parametri = self.request.GET

        # 1. RECUPERO FILTRI

        try:
            eta_minima = int(parametri.get('eta_minima', '18'))
        except (ValueError, TypeError):
            eta_minima = 18

        try:
            eta_massima = int(parametri.get('eta_massima', '100'))
        except (ValueError, TypeError):
            eta_massima = 100

        eta_minima = max(18, min(eta_minima, 100))
        eta_massima = max(18, min(eta_massima, 100))

        # Manteniamo un intervallo valido anche se l'URL viene modificato manualmente
        if eta_minima > eta_massima:
            eta_minima = eta_massima

        citta = parametri.get('citta', '').strip()

        # Filtri multipli
        occupazioni_richieste = parametri.getlist('occupazione')
        lingue_richieste = parametri.getlist('lingua')
        cosa_cerca_richiesto = parametri.getlist('cosa_cerca')
        interessi_raw = parametri.getlist('interessi')

        # 2. VALIDAZIONE DEI VALORI

        occupazioni_valide = {
            valore
            for valore, etichetta in Profilo.OCCUPAZIONI
        }

        lingue_valide = {
            lingua.casefold(): lingua
            for lingua in Profilo.LINGUE_DISPONIBILI
        }

        cerca_valide = set(Profilo.COSA_CERCA)

        occupazioni = list(dict.fromkeys(
            valore
            for valore in occupazioni_richieste
            if valore in occupazioni_valide
        ))

        lingue = list(dict.fromkeys(
            lingue_valide[valore.casefold()]
            for valore in lingue_richieste
            if valore.casefold() in lingue_valide
        ))

        cosa_cerca = list(dict.fromkeys(
            valore
            for valore in cosa_cerca_richiesto
            if valore in cerca_valide
        ))

        interessi_ids = []

        for valore in interessi_raw:
            try:
                identificativo = int(valore)

                if identificativo > 0:
                    interessi_ids.append(identificativo)

            except (ValueError, TypeError):
                continue

        interessi_ids = list(dict.fromkeys(interessi_ids))

        # 3. ESCLUSIONE PROFILI GIA VALUTATI

        profili_like = Like.objects.filter(
            mittente=mio_profilo
        ).values_list('destinatario_id', flat=True)

        profili_dislike = Dislike.objects.filter(
            mittente=mio_profilo
        ).values_list('destinatario_id', flat=True)

        candidati = (
            Profilo.objects
            .select_related('user')
            .prefetch_related('interessi')
            .exclude(pk=mio_profilo.pk)
            .exclude(pk__in=profili_like)
            .exclude(pk__in=profili_dislike)
        )

        # 4. FILTRI SUL DATABASE

        if citta:
            candidati = candidati.filter(
                citta__iexact=citta
            )

        # OR tra le occupazioni selezionate
        if occupazioni:
            candidati = candidati.filter(
                occupazione__in=occupazioni
            )

        # OR tra gli interessi selezionati.
        # Consideriamo anche la relazione tra
        # macrocategorie e sottocategorie.

        if interessi_ids:

            catalogo_interessi = list(
                Interesse.objects.values('pk', 'padre_id')
            )

            interessi_per_id = {
                interesse['pk']: interesse
                for interesse in catalogo_interessi
            }

            # Ignoriamo eventuali ID non validi.
            interessi_ids = [
                pk for pk in interessi_ids
                if pk in interessi_per_id
            ]

            interessi_ammessi = set(interessi_ids)

            for interesse in catalogo_interessi:

                # Se seleziono Musica, includo
                # anche tutte le sue sottocategorie.
                if interesse['padre_id'] in interessi_ids:
                    interessi_ammessi.add(interesse['pk'])

            for pk in interessi_ids:

                # Se seleziono Rock, includo anche
                # chi ha scelto Musica generale.
                padre_id = interessi_per_id[pk]['padre_id']

                if padre_id is not None:
                    interessi_ammessi.add(padre_id)

            candidati = candidati.filter(
                interessi__pk__in=interessi_ammessi
            ).distinct()

        # 5. FILTRI FINALI E RANKING

        # Informazioni del mio profilo da confrontare
        mia_citta = mio_profilo.citta.strip().casefold()
        mia_occupazione = mio_profilo.occupazione

        miei_interessi = list(
            mio_profilo.interessi.all()
        )

        mie_lingue = {
            lingua.casefold()
            for lingua in (mio_profilo.lingue or [])
        }

        mio_cosa_cerca = set(
            mio_profilo.cosa_cerca or []
        )

        # Valori dei filtri richiesti dall'utente
        lingue_selezionate = {
            lingua.casefold()
            for lingua in lingue
        }

        cosa_cerca_selezionato = set(cosa_cerca)

        # Contiene coppie (punteggio, profilo)
        candidati_ordinabili = []

        for candidato in candidati:

            # --------------------------------------
            # FILTRI RIGIDI RIMANENTI
            # --------------------------------------

            # Intervallo di eta
            if not (eta_minima <= candidato.eta <= eta_massima):
                continue

            lingue_candidato = {
                lingua.casefold()
                for lingua in (candidato.lingue or [])
            }

            # Filtro lingue: almeno una selezionata
            if lingue_selezionate:
                if not lingue_candidato.intersection(
                    lingue_selezionate
                ):
                    continue

            cerca_candidato = set(
                candidato.cosa_cerca or []
            )

            # Filtro cosa cerca: almeno una selezionata
            if cosa_cerca_selezionato:
                if not cerca_candidato.intersection(
                    cosa_cerca_selezionato
                ):
                    continue

            # A questo punto il candidato rispetta
            # tutti i filtri rigidi.

            # --------------------------------------
            # CALCOLO DELLA COMPATIBILITA
            # --------------------------------------

            punteggio = 0

            # 1. Stessa citta: +4
            if candidato.citta.strip().casefold() == mia_citta:
                punteggio += 4

            # 2. Compatibilità degli interessi:
            # +2 corrispondenza esatta
            # +1 macrocategoria / sottocategoria
            #  0 negli altri casi
            # Massimo 10 punti.

            interessi_candidato = list(
                candidato.interessi.all()
            )

            miei_ids = {
                interesse.pk
                for interesse in miei_interessi
            }

            candidato_ids = {
                interesse.pk
                for interesse in interessi_candidato
            }

            # CORRISPONDENZE ESATTE

            esatti = miei_ids & candidato_ids

            punti_interessi = len(esatti) * 2

            # Escludiamo gli interessi già abbinati
            # esattamente, evitando il doppio conteggio.

            miei_rimanenti = [
                interesse
                for interesse in miei_interessi
                if interesse.pk not in esatti
            ]

            candidato_rimanenti = [
                interesse
                for interesse in interessi_candidato
                if interesse.pk not in esatti
            ]

            candidato_usati = set()

            # CORRISPONDENZE PARZIALI:
            # padre e figlio nella gerarchia.

            for mio_interesse in miei_rimanenti:

                for interesse_candidato in candidato_rimanenti:

                    if interesse_candidato.pk in candidato_usati:
                        continue

                    collegati = (
                        mio_interesse.padre_id
                        == interesse_candidato.pk
                        or
                        interesse_candidato.padre_id
                        == mio_interesse.pk
                    )

                    if collegati:

                        punti_interessi += 1

                        candidato_usati.add(
                            interesse_candidato.pk
                        )

                        break

            # Massimo 10 punti per gli interessi.

            punteggio += min(punti_interessi, 10)

            # 3. Lingue comuni: +2 ciascuna, max 4
            numero_lingue_comuni = len(
                mie_lingue.intersection(
                    lingue_candidato
                )
            )

            punteggio += min(numero_lingue_comuni, 2) * 2

            # 4. Stessa occupazione: +2
            # Nessun punto se il dato non e' inserito.
            if (
                mia_occupazione
                and candidato.occupazione
                and mia_occupazione == candidato.occupazione
            ):
                punteggio += 2

            # 5. Cosa cercano in comune: +3, max 6
            numero_obiettivi_comuni = len(
                mio_cosa_cerca.intersection(
                    cerca_candidato
                )
            )

            punteggio += min(numero_obiettivi_comuni, 2) * 3

            # Memorizziamo il punteggio soltanto
            # in memoria, non nel database.
            candidati_ordinabili.append(
                (punteggio, candidato)
            )

        # ==========================================
        # ORDINAMENTO PER COMPATIBILITA
        # ==========================================

        # Primo criterio: punteggio decrescente.
        # Secondo criterio: ID crescente in caso di parita', per un risultato stabile.

        candidati_ordinabili.sort(
            key=lambda elemento: (
                -elemento[0],
                elemento[1].pk
            )
        )

        # Proponiamo una sola persona alla volta.

        # Per impostazione predefinita mostriamo il candidato con il ranking più alto.
        persona = (
            candidati_ordinabili[0][1]
            if candidati_ordinabili
            else None
        )

        # Se stiamo tornando da DettaglioPersona, proviamo a ripristinare il candidato corrente.
        candidato_richiesto = self.request.GET.get('candidato')

        if candidato_richiesto:

            try:
                candidato_id = int(candidato_richiesto)
            except (TypeError, ValueError):
                candidato_id = None

            if candidato_id is not None:

                # Cerchiamo il candidato SOLO fra quelli che hanno superato tutti i filtri rigidi e le esclusioni Like/Dislike.
                for punteggio, candidato in candidati_ordinabili:

                    if candidato.pk == candidato_id:
                        persona = candidato
                        break

        # ==========================================
        # 6. DATI PER IL TEMPLATE
        # ==========================================

        context['persona'] = persona

        context['eta_minima'] = eta_minima
        context['eta_massima'] = eta_massima
        context['filtro_citta'] = citta

        context['filtro_occupazioni'] = occupazioni
        context['filtro_lingue'] = lingue
        context['filtro_cosa_cerca'] = cosa_cerca
        context['filtro_interessi'] = interessi_ids

        context['occupazioni_disponibili'] = Profilo.OCCUPAZIONI
        context['lingue_disponibili'] = Profilo.LINGUE_DISPONIBILI
        context['opzioni_cosa_cerca'] = Profilo.COSA_CERCA

        context['interessi_disponibili'] = (
            Interesse.objects
            .select_related('padre')
            .order_by('padre_id', 'nome')
        )

        context['categorie_filtri'] = (
            Interesse.objects
            .filter(padre__isnull=True)
            .prefetch_related('sottointeressi')
            .order_by('nome')
        )

        context['filtri_attivi'] = bool(
            eta_minima != 18
            or eta_massima != 100
            or citta
            or occupazioni
            or lingue
            or cosa_cerca
            or interessi_ids
        )

        # Eventuale Match appena riconosciuto.
        # Lo mostriamo una sola volta dopo il redirect.
        context['match_recente'] = self.request.session.pop(
            'match_recente',
            None
        )

        return context

# dettaglio profilo di un'altra persona
class DettaglioPersonaView(ProfiloRichiestoMixin, DetailView):

    model = Profilo
    template_name = 'gestione/dettaglio_persona.html'
    context_object_name = 'persona'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        # Non consentiamo di aprire sé stessi attraverso DettaglioPersona
        return (
            Profilo.objects
            .select_related('user')
            .prefetch_related('interessi__padre')
            .exclude(user=self.request.user)
        )
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        persona = self.object
        mio_profilo = self.request.user.profilo

        # Controlliamo se esiste un Match reciproco.
        mio_like = Like.objects.filter(
            mittente=mio_profilo,
            destinatario=persona
        ).exists()

        suo_like = Like.objects.filter(
            mittente=persona,
            destinatario=mio_profilo
        ).exists()

        match_esistente = mio_like and suo_like

        context['origine_match_chat'] = (
            self.request.GET.get('origine') == 'match_chat'
            and match_esistente
        )
  
        # Arrivo dalla pagina Like ricevuti.
        # Il collegamento è valido solo se ho realmente ricevuto un Like ancora in attesa.
        like_in_attesa = (
            Like.objects.filter(
                mittente=persona,
                destinatario=mio_profilo
            ).exists()
            and not Like.objects.filter(
                mittente=mio_profilo,
                destinatario=persona
            ).exists()
            and not Dislike.objects.filter(
                mittente=mio_profilo,
                destinatario=persona
            ).exists()
        )

        context['origine_like_ricevuti'] = (
            self.request.GET.get('origine') == 'like_ricevuti'
            and like_in_attesa
        )

        # La provenienza "chat" viene riconosciuta
        # soltanto se esiste davvero il Match.
        context['origine_chat'] = (
            self.request.GET.get('origine') == 'chat'
            and match_esistente
        )

        context['match_esistente'] = match_esistente

        context['origine_notifiche'] = (
        self.request.GET.get('origine') == 'notifiche'
        )

        return context


# like e dislike dalla pagina persone
class ValutaPersonaView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        # Profilo destinatario dell'azione
        destinatario = get_object_or_404(
            Profilo,
            pk=kwargs['pk']
        )

        azione = request.POST.get('azione')

        # Recuperiamo soltanto i parametri dei filtri per mantenere la ricerca dopo l'azione.
        parametri_originali = QueryDict(
            request.POST.get('filtri', '')
        )

        parametri_consentiti = {
            'eta_minima',
            'eta_massima',
            'citta',
            'occupazione',
            'lingua',
            'cosa_cerca',
            'interessi',
        }

        parametri_filtri = QueryDict('', mutable=True)

        for chiave in parametri_consentiti:
            for valore in parametri_originali.getlist(chiave):
                parametri_filtri.appendlist(chiave, valore)

        url_ritorno = reverse('persone')

        if parametri_filtri:
            url_ritorno += '?' + parametri_filtri.urlencode()

        # Accettiamo soltanto le due azioni previste.
        if azione not in ('like', 'dislike'):
            return HttpResponseRedirect(url_ritorno)

        # Non si può valutare sé stessi.
        if destinatario.pk == mio_profilo.pk:
            return HttpResponseRedirect(url_ritorno)

        nuovo_match = False

        try:
            with transaction.atomic():

                # La stessa coppia non può essere valutata
                # più volte, neppure con azioni differenti.
                gia_like = Like.objects.filter(
                    mittente=mio_profilo,
                    destinatario=destinatario
                ).exists()

                gia_dislike = Dislike.objects.filter(
                    mittente=mio_profilo,
                    destinatario=destinatario
                ).exists()

                if gia_like or gia_dislike:
                    return HttpResponseRedirect(url_ritorno)

                if azione == 'like':

                    Like.objects.create(
                        mittente=mio_profilo,
                        destinatario=destinatario
                    )

                    
                    # Notifica del Like ricevuto.

                    Notifica.objects.create(
                        destinatario=destinatario,
                        tipo='LIKE_RICEVUTO',
                        testo=(
                            f'{mio_profilo.nome} '
                            f'ti ha messo Like.'
                        ),
                        profilo_collegato=mio_profilo
                    )


                    # Match derivato da due Like reciproci.
                    nuovo_match = Like.objects.filter(
                        mittente=destinatario,
                        destinatario=mio_profilo
                    ).exists()

                else:

                    Dislike.objects.create(
                        mittente=mio_profilo,
                        destinatario=destinatario
                    )

        except IntegrityError:
            # Protezione aggiuntiva in caso di richieste
            # concorrenti o vincoli di unicità violati.
            return HttpResponseRedirect(url_ritorno)

        # Conserviamo il nuovo Match nella sessione
        # per comunicarlo alla pagina Persone.
        if nuovo_match:

            # Notifica del nuovo Match a entrambi.
            Notifica.objects.create(
                destinatario=mio_profilo,
                tipo='MATCH',
                testo=(
                    f'Hai un nuovo Match con '
                    f'{destinatario.nome}!'
                ),
                profilo_collegato=destinatario
            )

            Notifica.objects.create(
                destinatario=destinatario,
                tipo='MATCH',
                testo=(
                    f'Hai un nuovo Match con '
                    f'{mio_profilo.nome}!'
                ),
                profilo_collegato=mio_profilo
            )


            request.session['match_recente'] = {
                'profilo_id': destinatario.pk,
                'nome': destinatario.nome,
            }

        # Dopo l'azione NON portiamo con noi "candidato":
        # Persone selezionerà il prossimo tramite il ranking.
        return HttpResponseRedirect(url_ritorno)

# chat privata 
class ChatPrivataView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/chat_privata.html'

    def get_partecipanti(self):

        mio_profilo = self.request.user.profilo

        altra_persona = get_object_or_404(
            Profilo,
            pk=self.kwargs['pk']
        )

        # Non posso conversare con me stessa.
        if altra_persona.pk == mio_profilo.pk:
            raise Http404

        # Il Match esiste solo con due Like reciproci.
        mio_like = Like.objects.filter(
            mittente=mio_profilo,
            destinatario=altra_persona
        ).exists()

        suo_like = Like.objects.filter(
            mittente=altra_persona,
            destinatario=mio_profilo
        ).exists()

        if not (mio_like and suo_like):
            raise Http404

        return mio_profilo, altra_persona

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        mio_profilo, altra_persona = self.get_partecipanti()

        # Recuperiamo esclusivamente i messaggi
        # scambiati fra questi due profili.
        messaggi = (
            MessaggioPrivato.objects
            .filter(
                Q(
                    mittente=mio_profilo,
                    destinatario=altra_persona
                )
                |
                Q(
                    mittente=altra_persona,
                    destinatario=mio_profilo
                )
            )
            .order_by('data_ora', 'id')
        )

        context['mio_profilo'] = mio_profilo
        context['altra_persona'] = altra_persona
        context['messaggi'] = messaggi

        return context

    def post(self, request, *args, **kwargs):

        # Controlliamo il Match anche per le POST.
        # Non basta verificarlo nella GET.
        mio_profilo, altra_persona = self.get_partecipanti()

        testo = request.POST.get('testo', '').strip()

        errore = None

        if not testo:
            errore = 'Scrivi un messaggio prima di inviarlo.'

        elif len(testo) > 2000:
            errore = 'Il messaggio non può superare 2000 caratteri.'

        if errore is None:

            messaggio = MessaggioPrivato(
                mittente=mio_profilo,
                destinatario=altra_persona,
                testo=testo
            )

            try:
                # Esegue anche la validazione definita
                # nel modello MessaggioPrivato.
                messaggio.full_clean()
                messaggio.save()

                # Notifica al destinatario del messaggio.
                Notifica.objects.create(
                    destinatario=altra_persona,
                    tipo='MESSAGGIO_PRIVATO',
                    testo=(
                        f'{mio_profilo.nome} ti ha inviato '
                        f'un nuovo messaggio.'
                    ),
                    profilo_collegato=mio_profilo
                )


            except ValidationError:
                errore = (
                    'Non è stato possibile inviare il messaggio. '
                    'Verifica che il Match sia ancora valido.'
                )

        if errore is not None:

            context = self.get_context_data()
            context['errore_messaggio'] = errore
            context['testo_inserito'] = testo

            return self.render_to_response(
                context,
                status=400
            )

        # Manteniamo la provenienza anche dopo
        # l'invio di un messaggio.

        destinazione = reverse(
            'chat_privata',
            kwargs={'pk': altra_persona.pk}
        )

        origine = request.POST.get('origine')

        if origine in ('notifiche', 'persone', 'like_ricevuti'):
            destinazione += f'?origine={origine}'

        return redirect(destinazione)



# Annulla match
class AnnullaMatchView(ProfiloRichiestoMixin, View):

    # La modifica dei dati è consentita soltanto via POST.
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        altra_persona = get_object_or_404(
            Profilo,
            pk=kwargs['pk']
        )

        # Non posso annullare un Match con me stessa.
        if altra_persona.pk == mio_profilo.pk:
            raise Http404

        with transaction.atomic():

            # Verifichiamo che esistano entrambi i Like.
            mio_like = Like.objects.select_for_update().filter(
                mittente=mio_profilo,
                destinatario=altra_persona
            ).first()

            suo_like = Like.objects.filter(
                mittente=altra_persona,
                destinatario=mio_profilo
            ).exists()

            # Senza reciprocità non esiste un Match da annullare.
            if mio_like is None or not suo_like:
                raise Http404

            # 1. Eliminiamo il mio Like.
            mio_like.delete()

            # 2. Registriamo il mio Dislike.
            # Questo impedirà che la persona venga
            # nuovamente proposta nella pagina Persone.
            Dislike.objects.get_or_create(
                mittente=mio_profilo,
                destinatario=altra_persona
            )

            # 3. Eliminiamo tutta la cronologia
            # dei messaggi scambiati nelle due direzioni.
            MessaggioPrivato.objects.filter(
                Q(
                    mittente=mio_profilo,
                    destinatario=altra_persona
                )
                |
                Q(
                    mittente=altra_persona,
                    destinatario=mio_profilo
                )
            ).delete()


        # Conferma dell'annullamento del Match.

        messages.success(
            request,
            'Match annullato correttamente!'
        )

        # Manteniamo la pagina di provenienza.

        if request.POST.get('origine') == 'notifiche':
            return redirect('notifiche')

        return redirect('match_chat')

# PROFILO --> GESTIONE PERSONE

# MatchChat --> Match e conversazioni
class MatchChatView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/match_chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        mio_profilo = self.request.user.profilo

        # Profili che hanno messo Like a me,
        # con la data di ciascun Like.
        like_ricevuti = {
            like.mittente_id: like.data_ora
            for like in Like.objects.filter(
                destinatario=mio_profilo
            )
        }

        # Profili a cui ho messo Like e che
        # hanno ricambiato: sono i miei Match.
        like_reciproci = Like.objects.filter(
            mittente=mio_profilo,
            destinatario_id__in=like_ricevuti.keys()
        )

        # La data di creazione del Match e' quella
        # del secondo Like, quindi la piu' recente.
        date_match = {}

        for like in like_reciproci:
            date_match[like.destinatario_id] = max(
                like.data_ora,
                like_ricevuti[like.destinatario_id]
            )

        # Recuperiamo i profili con cui ho un Match.
        profili_match = (
            Profilo.objects
            .filter(pk__in=date_match.keys())
            .prefetch_related('interessi')
        )

        # Le due liste sono separate:
        # una persona puo' comparire soltanto in una.
        tutti_match = []
        chat_iniziate = []

        for persona in profili_match:

            # Ultimo messaggio scambiato
            # tra me e questa persona.
            ultimo_messaggio = (
                MessaggioPrivato.objects
                .filter(
                    Q(
                        mittente=mio_profilo,
                        destinatario=persona
                    )
                    |
                    Q(
                        mittente=persona,
                        destinatario=mio_profilo
                    )
                )
                .order_by('-data_ora', '-id')
                .first()
            )

            if ultimo_messaggio:

                # Esiste almeno un messaggio:
                # la persona compare nelle CHAT.
                chat_iniziate.append({
                    'persona': persona,
                    'ultimo_messaggio': ultimo_messaggio,
                    'inviato_da_me': (
                        ultimo_messaggio.mittente_id
                        == mio_profilo.pk
                    ),
                })

            else:

                # Non esistono messaggi:
                # la persona compare nei MATCH.
                tutti_match.append({
                    'persona': persona,
                    'data_match': date_match[persona.pk],
                })

        # MATCH:
        # Dal piu' recente al meno recente.
        # Il primo comparira' a sinistra.
        tutti_match.sort(
            key=lambda elemento: (
                elemento['data_match'],
                elemento['persona'].pk
            ),
            reverse=True
        )

        # CHAT:
        # Ultimo messaggio piu' recente in alto.
        chat_iniziate.sort(
            key=lambda elemento: (
                elemento['ultimo_messaggio'].data_ora,
                elemento['ultimo_messaggio'].pk
            ),
            reverse=True
        )

        context['tutti_match'] = tutti_match
        context['chat_iniziate'] = chat_iniziate

        return context

# Like ricevuti 
class LikeRicevutiView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/like_ricevuti.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        mio_profilo = self.request.user.profilo

        # Profili a cui ho già messo Like.
        like_inviati = Like.objects.filter(
            mittente=mio_profilo
        ).values_list('destinatario_id', flat=True)

        # Profili a cui ho già messo Dislike.
        dislike_inviati = Dislike.objects.filter(
            mittente=mio_profilo
        ).values_list('destinatario_id', flat=True)

        # Recuperiamo soltanto i Like ricevuti
        # ai quali non ho ancora risposto.
        like_ricevuti = (
            Like.objects
            .filter(destinatario=mio_profilo)
            .exclude(mittente_id__in=like_inviati)
            .exclude(mittente_id__in=dislike_inviati)
            .select_related('mittente')
            .prefetch_related('mittente__interessi')
            .order_by('-data_ora', '-id')
        )

        context['like_ricevuti'] = like_ricevuti

        context['match_recente'] = self.request.session.pop(
            'match_recente',
            None
        )

        return context


# Risposta ad un like ricevuto

# ==========================================
# RISPOSTA A UN LIKE RICEVUTO
# ==========================================

class RispondiLikeRicevutoView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        altra_persona = get_object_or_404(
            Profilo,
            pk=kwargs['pk']
        )

        azione = request.POST.get('azione')

        if azione not in ('like', 'dislike'):
            raise Http404

        # Non posso valutare me stessa.
        if altra_persona.pk == mio_profilo.pk:
            raise Http404

        with transaction.atomic():

            # Deve esistere un Like ricevuto
            # da questa persona.
            like_ricevuto = Like.objects.filter(
                mittente=altra_persona,
                destinatario=mio_profilo
            ).exists()

            if not like_ricevuto:
                raise Http404

            # Non posso rispondere due volte.
            mio_like = Like.objects.filter(
                mittente=mio_profilo,
                destinatario=altra_persona
            ).exists()

            mio_dislike = Dislike.objects.filter(
                mittente=mio_profilo,
                destinatario=altra_persona
            ).exists()

            if mio_like or mio_dislike:
                raise Http404

            if azione == 'like':

                # REGISTRIAMO IL LIKE RECIPROCO.
                # Ora esistono due Like:
                # P1 -> P2 e P2 -> P1.

                nuovo_like = Like(
                    mittente=mio_profilo,
                    destinatario=altra_persona
                )

                nuovo_like.full_clean()
                nuovo_like.save()

                # Il Match è ora effettivo.
                # Notifichiamo entrambi gli utenti.

                Notifica.objects.create(
                    destinatario=mio_profilo,
                    tipo='MATCH',
                    testo=(
                        f'Hai un nuovo Match con '
                        f'{altra_persona.nome}!'
                    ),
                    profilo_collegato=altra_persona
                )

                Notifica.objects.create(
                    destinatario=altra_persona,
                    tipo='MATCH',
                    testo=(
                        f'Hai un nuovo Match con '
                        f'{mio_profilo.nome}!'
                    ),
                    profilo_collegato=mio_profilo
                )

                request.session['match_recente'] = {
                'profilo_id': altra_persona.pk,
                'nome': altra_persona.nome,
            }

            else:

                # RIFIUTO DEL LIKE RICEVUTO.

                nuovo_dislike = Dislike(
                    mittente=mio_profilo,
                    destinatario=altra_persona
                )

                nuovo_dislike.full_clean()
                nuovo_dislike.save()

        # In entrambi i casi rimaniamo
        # nella pagina Like ricevuti.

        if request.POST.get('origine') == 'notifiche':
            return redirect(
                reverse('like_ricevuti') + '?origine=notifiche'
            )

        return redirect('like_ricevuti')


# ==========================================
# DETTAGLIO COMMUNITY
# ==========================================

class DettaglioCommunityView(DetailView):

    model = Community
    context_object_name = 'community'
    pk_url_kwarg = 'pk'

    def get_queryset(self):

        # Le community incomplete non sono pubbliche.
        community_complete = (
            Community.objects
            .filter(interessi__isnull=False)
            .values('pk')
        )

        return (
            Community.objects
            .filter(pk__in=community_complete)
            .select_related('organizzatore')
            .prefetch_related('interessi', 'membri')
        )


    def get_template_names(self):

        # Utente autenticato con profilo completo:
        # utilizza il layout dell'area autenticata.

        if (
            self.request.user.is_authenticated
            and hasattr(self.request.user, 'profilo')
            and self.request.user.profilo.interessi.exists()
        ):
            return [
                'gestione/dettaglio_community_autenticata.html'
            ]

        # Utente anonimo o con profilo incompleto.
        return [
            'gestione/dettaglio_community.html'
        ]

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        gruppo = self.object
        utente = self.request.user

        # ======================================
        # STATISTICHE PUBBLICHE
        # ======================================

        statistiche = gruppo.valutazioni.aggregate(
            numero=Count('pk'),
            somma=Sum('voto')
        )

        numero = statistiche['numero']
        somma = statistiche['somma'] or 0

        context['numero_valutazioni'] = numero

        context['media_valutazioni'] = (
            somma / numero if numero else None
        )

        context['numero_membri'] = gruppo.membri.count()

        # ======================================
        # STATO DEL VISITATORE
        # ======================================

        context['profilo_completo'] = False
        context['organizzatore'] = False
        context['membro'] = False
        context['stato_richiesta'] = None
        context['mia_valutazione'] = None

        profilo_completo = (
            utente.is_authenticated
            and hasattr(utente, 'profilo')
            and utente.profilo.interessi.exists()
        )

        context['profilo_completo'] = profilo_completo

        if profilo_completo:

            mio_profilo = utente.profilo

            context['organizzatore'] = (
                gruppo.organizzatore_id == mio_profilo.pk
            )

            context['anteprima_esterna'] = (
                self.request.GET.get('anteprima') == '1'
                and context['organizzatore']
            )

            context['membro'] = (
                gruppo.membri.filter(
                    pk=mio_profilo.pk
                ).exists()
            )

            # Recuperiamo l'eventuale valutazione
            # già lasciata dall'utente.

            context['mia_valutazione'] = (
                ValutazioneCommunity.objects
                .filter(
                    utente=mio_profilo,
                    community=gruppo
                )
                .first()
            )

            richiesta = RichiestaCommunity.objects.filter(
                utente=mio_profilo,
                community=gruppo
            ).first()

            if richiesta:
                context['stato_richiesta'] = richiesta.stato

        # ======================================
        # NAVIGAZIONE
        # ======================================

        origine = self.request.GET.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        context['origine_community'] = origine

        if origine == 'notifiche' and profilo_completo:

            context['url_ritorno'] = reverse('notifiche')
            context['testo_ritorno'] = 'Torna alle Notifiche'

        elif origine == 'community_gestite' and profilo_completo:
            context['url_ritorno'] = reverse('community_gestite')
            context['testo_ritorno'] = 'Torna alle Community gestite'

        elif origine == 'profilo' and profilo_completo:
            context['url_ritorno'] = reverse('profilo')
            context['testo_ritorno'] = 'Torna al Profilo'

        elif origine == 'community' and profilo_completo:

            context['url_ritorno'] = reverse('community')
            context['testo_ritorno'] = 'Torna alle community'

        elif profilo_completo:

            context['url_ritorno'] = reverse('community')
            context['testo_ritorno'] = 'Torna alle community'

        else:

            context['url_ritorno'] = reverse('home_pubblica')
            context['testo_ritorno'] = 'Torna alla Home pubblica'

        return context


# ==========================================
# CREAZIONE COMMUNITY - PASSAGGIO 1
# ==========================================

class CreazioneCommunityView(
    ProfiloRichiestoMixin,
    CreateView
):

    model = Community
    form_class = CreazioneCommunityForm
    template_name = 'gestione/creazione_community.html'

    def form_valid(self, form):

        # L'organizzatore è sempre
        # il profilo dell'utente autenticato.
        form.instance.organizzatore = (
            self.request.user.profilo
        )

        with transaction.atomic():

            # Salvataggio della nuova community.
            self.object = form.save()

            # L'organizzatore diventa
            # automaticamente il primo membro.
            self.object.membri.add(
                self.request.user.profilo
            )


        # Recuperiamo la pagina di provenienza.
        origine = (
            self.request.POST.get('origine')
            or self.request.GET.get('origine')
        )

        # Accettiamo soltanto le provenienze previste.
        if origine != 'community_gestite':
            origine = 'community'

        # Passaggio 2: scelta degli interessi.
        url = reverse(
            'selezione_interessi_community',
            kwargs={'pk': self.object.pk}
        )

        return redirect(f'{url}?origine={origine}')



# ==========================================
# CREAZIONE COMMUNITY - PASSAGGIO 2
# ==========================================

class SelezioneInteressiCommunityView(
    ProfiloRichiestoMixin,
    FormView
):

    form_class = SelezioneInteressiForm

    template_name = (
        'gestione/selezione_interessi_community.html'
    )

    def dispatch(self, request, *args, **kwargs):

        # Prima applichiamo gli stessi controlli
        # di accesso dell'area autenticata.
        if not request.user.is_authenticated:
            return super().dispatch(
                request, *args, **kwargs
            )

        if not hasattr(request.user, 'profilo'):
            return super().dispatch(
                request, *args, **kwargs
            )

        if not request.user.profilo.interessi.exists():
            return super().dispatch(
                request, *args, **kwargs
            )

        # Soltanto l'organizzatore può
        # completare questa community.
        gruppo = get_object_or_404(
            Community,
            pk=kwargs['pk'],
            organizzatore=request.user.profilo
        )

        # La selezione iniziale non va ripetuta.
        if gruppo.interessi.exists():
            return redirect(
                'dettaglio_community',
                pk=gruppo.pk
            )

        return super().dispatch(
            request, *args, **kwargs
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['categorie'] = (
            Interesse.objects
            .filter(padre__isnull=True)
            .prefetch_related('sottointeressi')
            .order_by('nome')
        )

        context['community'] = get_object_or_404(
            Community,
            pk=self.kwargs['pk'],
            organizzatore=self.request.user.profilo
        )

        return context

    def form_valid(self, form):

        gruppo = get_object_or_404(
            Community,
            pk=self.kwargs['pk'],
            organizzatore=self.request.user.profilo
        )

        # Controlliamo nuovamente che
        # la community sia ancora incompleta.
        if gruppo.interessi.exists():
            return redirect(
                'dettaglio_community',
                pk=gruppo.pk
            )

        with transaction.atomic():

            gruppo.interessi.set(
                form.cleaned_data['interessi']
            )


        # Al termine della creazione torniamo
        # alla pagina dalla quale siamo partiti.

        origine = (
            self.request.POST.get('origine')
            or self.request.GET.get('origine')
        )

        if origine == 'community_gestite':
            return redirect('community_gestite')

        return redirect('community')



# ==========================================
# COMMUNITY GESTITE
# ==========================================

class CommunityGestiteView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/community_gestite.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # Mostriamo esclusivamente le community
        # organizzate dall'utente autenticato.

        context['community_gestite'] = (
            Community.objects
            .filter(
                organizzatore=self.request.user.profilo
            )
            .prefetch_related('interessi')
            .annotate(
                numero_richieste=Count(
                    'richieste_ricevute',
                    filter=Q(
                        richieste_ricevute__stato='PENDING'
                    ),
                    distinct=True
                )
            )
            .order_by('-data_creazione')
        )

        return context

# ==========================================
# MODIFICA COMMUNITY
# ==========================================

class ModificaCommunityView(ProfiloRichiestoMixin, UpdateView):

    model = Community
    form_class = CreazioneCommunityForm
    template_name = 'gestione/modifica_community.html'
    context_object_name = 'community'

    def get_queryset(self):

        # Soltanto l'organizzatore può modificare
        # le proprie community.
        return Community.objects.filter(
            organizzatore=self.request.user.profilo
        )

    def get_success_url(self):

        origine = self.request.POST.get(
            'origine',
            'community_gestite'
        )

        if origine == 'community':
            return (
                reverse(
                    'dettaglio_community',
                    kwargs={'pk': self.object.pk}
                )
                + '?origine=community'
            )

        if origine == 'profilo':
            return (
                reverse(
                    'dettaglio_community',
                    kwargs={'pk': self.object.pk}
                )
                + '?origine=profilo'
            )

        return reverse('community_gestite')

    def form_valid(self, form):

        risposta = super().form_valid(form)

        messages.success(
            self.request,
            'Community aggiornata correttamente!'
        )

        return risposta



# ==========================================
# MODIFICA INTERESSI COMMUNITY
# ==========================================

class ModificaInteressiCommunityView(
    ProfiloRichiestoMixin,
    FormView
):

    form_class = SelezioneInteressiForm

    template_name = (
        'gestione/selezione_interessi_community.html'
    )

    def get_community(self):

        gruppo = get_object_or_404(
            Community,
            pk=self.kwargs['pk'],
            organizzatore=self.request.user.profilo
        )

        # La modifica degli interessi è consentita
        # soltanto per una community già completata.
        if not gruppo.interessi.exists():
            raise Http404

        return gruppo

    def get_initial(self):

        initial = super().get_initial()

        gruppo = self.get_community()

        initial['interessi'] = [
            str(pk)
            for pk in gruppo.interessi.values_list(
                'pk',
                flat=True
            )
        ]

        return initial

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['community'] = self.get_community()

        context['modalita_modifica'] = True

        context['categorie'] = (
            Interesse.objects
            .filter(padre__isnull=True)
            .prefetch_related('sottointeressi')
            .order_by('nome')
        )

        return context

    def form_valid(self, form):

        gruppo = self.get_community()

        with transaction.atomic():

            gruppo.interessi.set(
                form.cleaned_data['interessi']
            )

        messages.success(
            self.request,
            'Interessi della community aggiornati.'
        )

        origine = self.request.POST.get(
            'origine'
        ) or self.request.GET.get(
            'origine'
        )

        if origine not in (
            'profilo',
            'community',
            'community_gestite'
        ):
            origine = 'community_gestite'

        destinazione = reverse(
            'modifica_community',
            kwargs={'pk': gruppo.pk}
        )

        return redirect(
            f'{destinazione}?origine={origine}'
        )


# ==========================================
# ELIMINAZIONE COMMUNITY
# ==========================================
class EliminaCommunityView(ProfiloRichiestoMixin, DeleteView):

    model = Community

    # L'eliminazione è consentita soltanto via POST.
    http_method_names = ['post']

    def get_queryset(self):

        # Soltanto l'organizzatore può eliminare
        # una community di sua proprietà.
        return Community.objects.filter(
            organizzatore=self.request.user.profilo
        )

    def get_success_url(self):

        # Recuperiamo la pagina di provenienza.
        origine = self.request.POST.get('origine')

        # Dal Profilo torniamo al Profilo.
        if origine == 'profilo':
            return reverse('profilo')

        # Da Esplora community torniamo a Community.
        if origine == 'community':
            return reverse('community')

        # Da Community gestite, oppure se manca
        # una provenienza valida, torniamo
        # all'elenco delle community gestite.
        return reverse('community_gestite')

    def form_valid(self, form):

        risposta = super().form_valid(form)

        messages.success(
            self.request,
            'Community eliminata correttamente.'
        )

        return risposta

# ==========================================
# INVIO RICHIESTA COMMUNITY
# ==========================================

class InviaRichiestaCommunityView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        with transaction.atomic():

            gruppo = get_object_or_404(
                Community.objects.select_for_update(),
                pk=kwargs['pk']
            )

            # Non si possono inviare richieste
            # per una community incompleta.
            if not gruppo.interessi.exists():
                raise Http404

            # L'organizzatore non può richiedere
            # di partecipare alla propria community.
            if gruppo.organizzatore_id == mio_profilo.pk:
                raise Http404

            # Un membro non può richiedere
            # di entrare nuovamente.
            if gruppo.membri.filter(
                pk=mio_profilo.pk
            ).exists():
                raise Http404

            richiesta = RichiestaCommunity.objects.filter(
                utente=mio_profilo,
                community=gruppo
            ).first()

            # Non consentiamo richieste duplicate
            # quando una richiesta è già in attesa.
            if richiesta and richiesta.stato == 'PENDING':
                raise Http404

            if richiesta:

                # Dopo un rifiuto o un'uscita,
                # riutilizziamo la richiesta esistente.
                richiesta.stato = 'PENDING'
                richiesta.data_richiesta = timezone.now()

                richiesta.full_clean()

                richiesta.save(
                    update_fields=['stato', 'data_richiesta']
                )

            else:

                richiesta = RichiestaCommunity(
                    utente=mio_profilo,
                    community=gruppo,
                    stato='PENDING'
                )

                richiesta.full_clean()
                richiesta.save()

            # Notifica all'organizzatore.
            Notifica.objects.create(
                destinatario=gruppo.organizzatore,
                tipo='RICHIESTA_COMMUNITY',
                testo=(
                    f'{mio_profilo.nome} ha richiesto '
                    f'di partecipare a {gruppo.titolo}.'
                ),
                profilo_collegato=mio_profilo,
                community_collegata=gruppo
            )

        messages.success(
            request,
            'Richiesta di partecipazione inviata!'
        )

        origine = request.POST.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        destinazione = reverse(
            'dettaglio_community',
            kwargs={'pk': gruppo.pk}
        )

        return redirect(
            f'{destinazione}?origine={origine}'
        )


# ==========================================
# ANNULLAMENTO RICHIESTA COMMUNITY
# ==========================================

class AnnullaRichiestaCommunityView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        with transaction.atomic():

            gruppo = get_object_or_404(
                Community.objects.select_for_update(),
                pk=kwargs['pk']
            )

            richiesta = get_object_or_404(
                RichiestaCommunity,
                utente=mio_profilo,
                community=gruppo,
                stato='PENDING'
            )

            richiesta.delete()

        messages.success(
            request,
            'Hai annullato la richiesta di partecipazione.'
        )

        origine = request.POST.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        destinazione = reverse(
            'dettaglio_community',
            kwargs={'pk': gruppo.pk}
        )

        return redirect(
            f'{destinazione}?origine={origine}'
        )


# ==========================================
# GESTIONE RICHIESTE COMMUNITY
# ==========================================

class GestioneRichiesteCommunityView(
    ProfiloRichiestoMixin,
    TemplateView
):

    template_name = 'gestione/gestione_richieste_community.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # Soltanto l'organizzatore può
        # visualizzare le richieste ricevute.
        gruppo = get_object_or_404(
            Community,
            pk=self.kwargs['pk'],
            organizzatore=self.request.user.profilo
        )

        richieste = (
            RichiestaCommunity.objects
            .filter(
                community=gruppo,
                stato='PENDING'
            )
            .select_related('utente')
            .order_by('data_richiesta', 'pk')
        )

        context['community'] = gruppo
        context['richieste'] = richieste
        context['numero_richieste'] = richieste.count()

        return context


# ==========================================
# ACCETTAZIONE / RIFIUTO RICHIESTA
# ==========================================


# ==========================================
# ACCETTAZIONE / RIFIUTO RICHIESTA
# ==========================================

class GestisciRichiestaCommunityView(
    ProfiloRichiestoMixin,
    View
):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        azione = request.POST.get('azione')
        origine = request.POST.get('origine')

        if azione not in ('accetta', 'rifiuta'):
            raise Http404

        with transaction.atomic():

            gruppo = get_object_or_404(
                Community.objects.select_for_update(),
                pk=kwargs['pk'],
                organizzatore=request.user.profilo
            )

            richiesta = get_object_or_404(
                RichiestaCommunity.objects.select_for_update(),
                pk=kwargs['richiesta_pk'],
                community=gruppo,
                stato='PENDING'
            )

            if azione == 'accetta':

                gruppo.membri.add(richiesta.utente)

                richiesta.stato = 'ACCEPTED'
                richiesta.save(update_fields=['stato'])

                Notifica.objects.create(
                    destinatario=richiesta.utente,
                    tipo='RICHIESTA_ACCETTATA',
                    testo=(
                        f'La tua richiesta di partecipazione '
                        f'a {gruppo.titolo} è stata accettata.'
                    ),
                    community_collegata=gruppo
                )

                messaggio = 'Richiesta accettata.'

            else:

                richiesta.stato = 'REJECTED'
                richiesta.save(update_fields=['stato'])

                Notifica.objects.create(
                    destinatario=richiesta.utente,
                    tipo='RICHIESTA_RIFIUTATA',
                    testo=(
                        f'La tua richiesta di partecipazione '
                        f'a {gruppo.titolo} è stata rifiutata.'
                    ),
                    community_collegata=gruppo
                )

                messaggio = 'Richiesta rifiutata.'

        messages.success(request, messaggio)

        # Se l'azione arriva dalle notifiche,
        # torniamo alle notifiche.

        if origine == 'notifiche':
            return redirect('notifiche')

        # Altrimenti manteniamo il comportamento
        # originale della gestione richieste.

        destinazione = reverse(
            'gestione_richieste_community',
            kwargs={'pk': gruppo.pk}
        )

        if origine in ('community', 'profilo', 'community_gestite'):
            destinazione += f'?origine={origine}'

        return redirect(destinazione)

# ==========================================
# USCITA DALLA COMMUNITY
# ==========================================

class EsciCommunityView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        with transaction.atomic():

            gruppo = get_object_or_404(
                Community.objects.select_for_update(),
                pk=kwargs['pk']
            )

            # L'organizzatore non può uscire.
            if gruppo.organizzatore_id == mio_profilo.pk:
                raise Http404

            # Deve essere un membro effettivo.
            if not gruppo.membri.filter(
                pk=mio_profilo.pk
            ).exists():
                raise Http404

            # Rimuoviamo soltanto la partecipazione.
            gruppo.membri.remove(mio_profilo)

            # Non cancelliamo la richiesta storica,
            # le valutazioni o gli altri dati collegati.

        messages.success(
            request,
            'Hai lasciato la community.'
        )

        origine = request.POST.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        destinazione = reverse(
            'dettaglio_community',
            kwargs={'pk': gruppo.pk}
        )

        return redirect(
            f'{destinazione}?origine={origine}'
        )


# ==========================================
# CHAT DI GRUPPO COMMUNITY
# ==========================================

class ChatGruppoView(ProfiloRichiestoMixin, TemplateView):

    template_name = 'gestione/chat_gruppo.html'

    # Recupera la community verificando che
    # l'utente possa realmente accedere alla chat.
    def get_community(self):

        gruppo = get_object_or_404(
            Community.objects.select_related('organizzatore'),
            pk=self.kwargs['pk']
        )

        mio_profilo = self.request.user.profilo

        # L'organizzatore può sempre accedere
        # alla chat della propria community.
        organizzatore = (
            gruppo.organizzatore_id == mio_profilo.pk
        )

        # Gli altri utenti devono essere membri.
        membro = gruppo.membri.filter(
            pk=mio_profilo.pk
        ).exists()

        if not (organizzatore or membro):
            raise Http404

        # Le community incomplete non hanno
        # ancora una chat accessibile.
        if not gruppo.interessi.exists():
            raise Http404

        return gruppo

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        gruppo = self.get_community()
        mio_profilo = self.request.user.profilo

        # Recuperiamo i messaggi della community
        # in ordine cronologico.
        messaggi = (
            MessaggioCommunity.objects
            .filter(community=gruppo)
            .select_related('autore')
            .order_by('data_ora', 'pk')
        )

        context['community'] = gruppo
        context['mio_profilo'] = mio_profilo
        context['messaggi'] = messaggi

        context['numero_membri'] = gruppo.membri.count()

        # Anteprima della chat riservata
        # all'organizzatore della community.
        context['anteprima_membro'] = (
            self.request.GET.get('anteprima') == '1'
            and gruppo.organizzatore_id == mio_profilo.pk
        )

        origine = self.request.GET.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        context['origine_community'] = origine

        return context

    def post(self, request, *args, **kwargs):

        # Ricontrolliamo i permessi anche
        # durante l'invio del messaggio.
        gruppo = self.get_community()

        mio_profilo = request.user.profilo

        # La modalità Anteprima è di sola lettura.
        # Non consentiamo l'invio di messaggi.
        if (
            request.GET.get('anteprima') == '1'
            and gruppo.organizzatore_id == mio_profilo.pk
        ):
            raise Http404

        testo = request.POST.get('testo', '').strip()

        errore = None

        if not testo:
            errore = 'Scrivi un messaggio prima di inviarlo.'

        elif len(testo) > 2000:
            errore = (
                'Il messaggio non può superare '
                '2000 caratteri.'
            )

        if errore is None:

            messaggio = MessaggioCommunity(
                community=gruppo,
                autore=mio_profilo,
                testo=testo
            )

            try:

                # Valida anche il vincolo del modello:
                # soltanto i membri possono scrivere.
                messaggio.full_clean()
                messaggio.save()

                # Notifichiamo tutti gli altri membri
                # della community, escluso il mittente.

                altri_membri = gruppo.membri.exclude(
                    pk=mio_profilo.pk
                )

                Notifica.objects.bulk_create([
                    Notifica(
                        destinatario=partecipante,
                        tipo='MESSAGGIO_COMMUNITY',
                        testo=(
                            f'{mio_profilo.nome} ha scritto '
                            f'nella chat di {gruppo.titolo}.'
                        ),
                        profilo_collegato=mio_profilo,
                        community_collegata=gruppo
                    )
                    for partecipante in altri_membri
                ])
                        

            except ValidationError:

                errore = (
                    'Non è stato possibile inviare il messaggio. '
                    'Verifica di essere ancora membro.'
                )

        if errore is not None:

            context = self.get_context_data()

            context['errore_messaggio'] = errore
            context['testo_inserito'] = testo

            return self.render_to_response(
                context,
                status=400
            )

        destinazione = reverse(
            'chat_gruppo',
            kwargs={'pk': gruppo.pk}
        )

        origine = request.POST.get('origine')

        if origine in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            destinazione += f'?origine={origine}'

        return redirect(destinazione)


# ==========================================
# VALUTAZIONE COMMUNITY
# ==========================================

class ValutaCommunityView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        origine = request.POST.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        destinazione = (
            reverse(
                'dettaglio_community',
                kwargs={'pk': kwargs['pk']}
            )
            + f'?origine={origine}'
        )

        valore = request.POST.get('voto', '')

        # Il voto deve essere un intero da 1 a 5.
        if valore not in ('1', '2', '3', '4', '5'):
            messages.error(
                request,
                'Seleziona un voto da 1 a 5 stelle.'
            )
            
            return redirect(destinazione)

        voto = int(valore)

        with transaction.atomic():

            # Blocchiamo la community durante
            # la verifica e il salvataggio.
            gruppo = get_object_or_404(
                Community.objects.select_for_update(),
                pk=kwargs['pk']
            )

            if not gruppo.interessi.exists():
                raise Http404

            # L'organizzatore non può valutare.
            if gruppo.organizzatore_id == mio_profilo.pk:
                raise Http404

            # Soltanto un membro attuale
            # può creare o modificare il voto.
            if not gruppo.membri.filter(
                pk=mio_profilo.pk
            ).exists():
                raise Http404

            valutazione = (
                ValutazioneCommunity.objects
                .filter(
                    utente=mio_profilo,
                    community=gruppo
                )
                .first()
            )

            if valutazione is None:

                # Prima valutazione.
                valutazione = ValutazioneCommunity(
                    utente=mio_profilo,
                    community=gruppo,
                    voto=voto
                )

                messaggio = 'Valutazione pubblicata!'

            else:

                # Modifichiamo la valutazione esistente.
                valutazione.voto = voto

                messaggio = 'Valutazione aggiornata!'

            # Eseguiamo anche le validazioni
            # previste nel modello.
            valutazione.full_clean()
            valutazione.save()

        messages.success(request, messaggio)

        return redirect(destinazione)


# ==========================================
# PERMESSI EVENTI COMMUNITY
# ==========================================

class AccessoEventiCommunityMixin(ProfiloRichiestoMixin):

    def get_community(self):

        gruppo = get_object_or_404(
            Community,
            pk=self.kwargs['pk']
        )

        mio_profilo = self.request.user.profilo

        organizzatore = (
            gruppo.organizzatore_id == mio_profilo.pk
        )

        membro = gruppo.membri.filter(
            pk=mio_profilo.pk
        ).exists()

        # Solo organizzatore e membri.
        if not (organizzatore or membro):
            raise Http404

        # La community deve essere completa.
        if not gruppo.interessi.exists():
            raise Http404

        return gruppo


class OrganizzatoreEventiMixin(AccessoEventiCommunityMixin):

    def get_community(self):

        gruppo = super().get_community()

        # Le operazioni di gestione sono riservate
        # esclusivamente all'organizzatore.
        if gruppo.organizzatore_id != self.request.user.profilo.pk:
            raise Http404

        return gruppo


# ==========================================
# EVENTI COMMUNITY - CONSULTAZIONE
# ==========================================

class EventiCommunityView(
    AccessoEventiCommunityMixin,
    TemplateView
):

    template_name = 'gestione/eventi_community.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        gruppo = self.get_community()
        adesso = timezone.now()

        eventi = Evento.objects.filter(
            community=gruppo
        )

        # Eventi non ancora terminati:
        # se non hanno fine, consideriamo l'inizio.
        eventi_futuri = eventi.filter(
            Q(fine__gte=adesso)
            |
            Q(
                fine__isnull=True,
                inizio__gte=adesso
            )
        ).order_by('inizio', 'pk')

        eventi_passati = eventi.exclude(
            pk__in=eventi_futuri.values('pk')
        ).order_by('-inizio', '-pk')

        context['community'] = gruppo
        context['eventi_futuri'] = eventi_futuri
        context['eventi_passati'] = eventi_passati

        # Riconosciamo l'accesso agli eventi
        # dalla modalità Anteprima.
        context['anteprima_membro'] = (
            self.request.GET.get('anteprima') == '1'
            and gruppo.organizzatore_id
                == self.request.user.profilo.pk
        )

        origine = self.request.GET.get('origine')

        if origine not in (
            'profilo',
            'community',
            'community_gestite',
            'notifiche'
        ):
            origine = 'community'

        context['origine_community'] = origine

        context['anteprima_membro'] = (
            self.request.GET.get('anteprima') == '1'
            and gruppo.organizzatore_id
                == self.request.user.profilo.pk
        )

        return context


# ==========================================
# PANNELLO GESTISCI EVENTI
# ==========================================

class GestioneEventiCommunityView(
    OrganizzatoreEventiMixin,
    TemplateView
):

    template_name = 'gestione/gestione_eventi_community.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        gruppo = self.get_community()
        adesso = timezone.now()

        eventi = Evento.objects.filter(
            community=gruppo
        )

        eventi_futuri = eventi.filter(
            Q(fine__gte=adesso)
            |
            Q(
                fine__isnull=True,
                inizio__gte=adesso
            )
        ).order_by('inizio', 'pk')

        eventi_passati = eventi.exclude(
            pk__in=eventi_futuri.values('pk')
        ).order_by('-inizio', '-pk')

        context['community'] = gruppo
        context['eventi_futuri'] = eventi_futuri
        context['eventi_passati'] = eventi_passati

        return context


# ==========================================
# CREAZIONE EVENTO
# ==========================================

class CreazioneEventoCommunityView(
    OrganizzatoreEventiMixin,
    CreateView
):

    model = Evento
    form_class = EventoForm
    template_name = 'gestione/form_evento_community.html'

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated and hasattr(request.user, 'profilo'):

            if request.user.profilo.interessi.exists():
                self.get_community()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['community'] = self.get_community()
        context['modalita_modifica'] = False

        return context

    def form_valid(self, form):

        gruppo = self.get_community()

        # La community viene assegnata dal server.
        form.instance.community = gruppo

        risposta = super().form_valid(form)
                
        # Notifica ai membri della community,
        # escluso l'organizzatore che crea l'evento.

        partecipanti = gruppo.membri.exclude(
            pk=gruppo.organizzatore_id
        )

        Notifica.objects.bulk_create([
            Notifica(
                destinatario=partecipante,
                tipo='NUOVO_EVENTO_COMMUNITY',
                testo=(
                    f'Nuovo evento in {gruppo.titolo}: '
                    f'{self.object.titolo}.'
                ),
                community_collegata=gruppo
            )
            for partecipante in partecipanti
        ])


        messages.success(
            self.request,
            'Evento creato correttamente.'
        )

        return risposta

    def get_success_url(self):

        origine = self.request.POST.get('origine')

        if origine not in (
            'community',
            'profilo',
            'community_gestite'
        ):
            origine = 'community_gestite'

        destinazione = reverse(
            'gestione_eventi_community',
            kwargs={'pk': self.kwargs['pk']}
        )

        return f'{destinazione}?origine={origine}'


# ==========================================
# MODIFICA EVENTO
# ==========================================

class ModificaEventoCommunityView(
    OrganizzatoreEventiMixin,
    UpdateView
):

    model = Evento
    form_class = EventoForm
    template_name = 'gestione/form_evento_community.html'

    pk_url_kwarg = 'evento_pk'

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated and hasattr(request.user, 'profilo'):

            if request.user.profilo.interessi.exists():
                self.get_community()

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):

        gruppo = self.get_community()

        # Soltanto eventi di quella community.
        return Evento.objects.filter(
            community=gruppo
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['community'] = self.get_community()
        context['modalita_modifica'] = True

        return context

    def form_valid(self, form):

        risposta = super().form_valid(form)

        gruppo = self.get_community()

        partecipanti = gruppo.membri.exclude(
            pk=gruppo.organizzatore_id
        )

        Notifica.objects.bulk_create([
            Notifica(
                destinatario=partecipante,
                tipo='EVENTO_MODIFICATO',
                testo=(
                    f'L’evento {self.object.titolo} '
                    f'di {gruppo.titolo} è stato modificato.'
                ),
                community_collegata=gruppo
            )
            for partecipante in partecipanti
        ])


        messages.success(
            self.request,
            'Evento modificato correttamente.'
        )

        return risposta

    def get_success_url(self):

        origine = self.request.POST.get('origine')

        if origine not in (
            'community',
            'profilo',
            'community_gestite'
        ):
            origine = 'community_gestite'

        destinazione = reverse(
            'gestione_eventi_community',
            kwargs={'pk': self.kwargs['pk']}
        )

        return f'{destinazione}?origine={origine}'


# ==========================================
# ELIMINAZIONE EVENTO
# ==========================================

class EliminaEventoCommunityView(
    OrganizzatoreEventiMixin,
    DeleteView
):

    model = Evento

    pk_url_kwarg = 'evento_pk'
    http_method_names = ['post']

    def get_queryset(self):

        gruppo = self.get_community()

        return Evento.objects.filter(
            community=gruppo
        )

    def get_success_url(self):

        origine = self.request.GET.get('origine')

        if origine not in (
            'community',
            'profilo',
            'community_gestite'
        ):
            origine = 'community_gestite'

        destinazione = reverse(
            'gestione_eventi_community',
            kwargs={'pk': self.kwargs['pk']}
        )

        return f'{destinazione}?origine={origine}'

    def form_valid(self, form):

        risposta = super().form_valid(form)

        messages.success(
            self.request,
            'Evento eliminato correttamente.'
        )

        return risposta


# ==========================================
# APERTURA NOTIFICA
# ==========================================

# ==========================================
# APERTURA NOTIFICA
# ==========================================

class ApriNotificaView(ProfiloRichiestoMixin, View):

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        mio_profilo = request.user.profilo

        with transaction.atomic():

            notifica = get_object_or_404(
                Notifica.objects.select_for_update(),
                pk=kwargs['pk'],
                destinatario=mio_profilo
            )

            if not notifica.letta:
                notifica.letta = True
                notifica.save(update_fields=['letta'])

        tipo = notifica.tipo
        profilo = notifica.profilo_collegato
        gruppo = notifica.community_collegata

        # Destinazione predefinita sicura.
        destinazione = reverse('notifiche')

        # MATCH -> DETTAGLIO PERSONA

        if tipo == 'MATCH':

            if (
                profilo is not None
                and profilo.pk != mio_profilo.pk
            ):
                destinazione = reverse(
                    'dettaglio_persona',
                    kwargs={'pk': profilo.pk}
                ) + '?origine=notifiche'

        # LIKE RICEVUTO -> LIKE RICEVUTI

        elif tipo == 'LIKE_RICEVUTO':

            destinazione = (
                reverse('like_ricevuti')
                + '?origine=notifiche'
            )

        # MESSAGGIO PRIVATO -> CHAT PRIVATA

        elif tipo == 'MESSAGGIO_PRIVATO':

            if profilo is not None:

                mio_like = Like.objects.filter(
                    mittente=mio_profilo,
                    destinatario=profilo
                ).exists()

                suo_like = Like.objects.filter(
                    mittente=profilo,
                    destinatario=mio_profilo
                ).exists()

                if mio_like and suo_like:

                    destinazione = reverse(
                        'chat_privata',
                        kwargs={'pk': profilo.pk}
                    ) + '?origine=notifiche'

        # NOTIFICHE RELATIVE ALLE COMMUNITY

        # RICHIESTE DI PARTECIPAZIONE

        elif tipo in (
            'RICHIESTA_COMMUNITY',
            'RICHIESTA_ACCETTATA',
            'RICHIESTA_RIFIUTATA'
        ):

            if (
                gruppo is not None
                and gruppo.interessi.exists()
            ):

                destinazione = reverse(
                    'dettaglio_community',
                    kwargs={'pk': gruppo.pk}
                ) + '?origine=notifiche'

        # MESSAGGIO COMMUNITY -> CHAT DI GRUPPO

        elif tipo == 'MESSAGGIO_COMMUNITY':

            if (
                gruppo is not None
                and gruppo.interessi.exists()
            ):

                organizzatore = (
                    gruppo.organizzatore_id == mio_profilo.pk
                )

                membro = gruppo.membri.filter(
                    pk=mio_profilo.pk
                ).exists()

                if organizzatore or membro:

                    destinazione = reverse(
                        'chat_gruppo',
                        kwargs={'pk': gruppo.pk}
                    ) + '?origine=notifiche'

        # EVENTI -> ELENCO EVENTI COMMUNITY

        elif tipo in (
            'NUOVO_EVENTO_COMMUNITY',
            'EVENTO_MODIFICATO'
        ):

            if (
                gruppo is not None
                and gruppo.interessi.exists()
            ):

                organizzatore = (
                    gruppo.organizzatore_id == mio_profilo.pk
                )

                membro = gruppo.membri.filter(
                    pk=mio_profilo.pk
                ).exists()

                if organizzatore or membro:

                    destinazione = reverse(
                        'eventi_community',
                        kwargs={'pk': gruppo.pk}
                    ) + '?origine=notifiche'
        
        return redirect(destinazione)