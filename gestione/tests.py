# SUITE DI TEST DI FuoriRete 
# per eseguire tutti i test -> python manage.py test gestione
# per eseguire 1 sola classe -> python manage.py test gestione gestione.tests.nome_classe
# per eseguire 1 solo piccolo test -> python manage.py test gestione.tests.nome_classe.nome_test

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import RegistrazioneForm, SelezioneInteressiForm, CreazioneCommunityForm
from .models import (
    Interesse, Profilo, Like, Dislike, MessaggioPrivato,
    Community, RichiestaCommunity, MessaggioCommunity,
    ValutazioneCommunity, Evento, Notifica,
)
from .views import calcola_punteggio_pubblico, calcola_compatibilita_community

# ============================================================
# DATI DI PROVA — funzioni ausiliarie, non modificano il database reale
# ============================================================

# crea un utente (utente, profilo) 
def crea_utente(numero, *, completo=True, citta='Modena', interessi=None):

    utente = User.objects.create_user(
        username=f'utente_test_{numero}',
        email=f'utente{numero}@example.test',
        password='PasswordTest123!',
    )
    if not completo:
        return utente, None
    
    profilo = Profilo.objects.create(
        user=utente,
        nome='Persona',
        foto=f'profili/test_{numero}.jpg',
        data_nascita=date(2000, 6, 15),
        genere='DONNA',
        citta=citta,
        occupazione='STUDENTE',
        lingue=['Italiano'],
        descrizione='Profilo di prova',
        cosa_cerca=['AMICIZIE'],
    )
    if interessi:
        profilo.interessi.set(interessi)
    return utente, profilo

# crea community 
def crea_community(organizzatore, *, titolo='Community test', citta='Modena', interessi=None):
   
    gruppo = Community.objects.create(
        organizzatore=organizzatore,
        titolo=titolo,
        descrizione='Descrizione della community di prova.',
        citta=citta,
    )
    gruppo.membri.add(organizzatore)
    if interessi:
        gruppo.interessi.set(interessi)
    return gruppo

# crea un match fra 2 utenti
def crea_match(profilo_a, profilo_b):
    Like.objects.create(mittente=profilo_a, destinatario=profilo_b)
    Like.objects.create(mittente=profilo_b, destinatario=profilo_a)

# ============================================================
# (17 classi, 65 test) TEST - ad ogni classe corrisponde una funzionalità esistente 
# usano la classe TestCase
# ============================================================

# ============================================================
# TEST SUI DATI --> interessi
# ============================================================

# TEST SUGLI INTERESSI -> riguarda la gerarchia degli interessi
class InteresseModelTests(TestCase):

    # t1: un interesse non può essere padre di sè stesso --> impostiamo il padre uguale a se stesso (ci aspettiamo un errore)
    def test_interesse_non_puo_essere_padre_di_se_stesso(self):
        categoria = Interesse.objects.create(nome='Categoria test')
        categoria.padre = categoria
        with self.assertRaises(ValidationError):
            categoria.full_clean()

    # t2: un interesse ha una gerarchia al max. a 2 livelli --> creiamo 3 livelli (ci aspettiamo un errore)
    def test_gerarchia_non_supera_due_livelli(self):
        padre = Interesse.objects.create(nome='Sport test')
        figlio = Interesse.objects.create(nome='Tennis test', padre=padre)
        nipote = Interesse(nome='Tennis doppio test', padre=figlio)
        with self.assertRaises(ValidationError):
            nipote.full_clean()

    # t3: un padre che ha dei figli, non può mai essere una sotto-categoria --> creo padre, creo figlio, creo un terzo interesse, l'interesse diventa padre del padre (ci aspettiamo un errore)
    def test_interesse_padre_con_figli_non_diventa_sottocategoria(self):
        padre = Interesse.objects.create(nome='Sport test')
        Interesse.objects.create(nome='Nuoto test', padre=padre)
        altro = Interesse.objects.create(nome='Attivita test')
        padre.padre = altro
        with self.assertRaises(ValidationError):
            padre.full_clean()

# ============================================================
# TEST PER LA REGISTRAZIONE DI UN UTENTE
# ============================================================

# TEST PER LA REGISTRAZIONE DELL'UTENTE -> riguarda i dati inseriti nel momento della registrazione
class RegistrazioneFormTests(TestCase):

    # t1: verifica che se la pww e la conferma pww non sono uguali vengano rifiutate
    def test_password_diverse_non_valide(self):
        form = RegistrazioneForm(data={
            'username': 'nuovo_utente',
            'email': 'nuovo@example.test',
            'password1': 'PasswordTest123!',
            'password2': 'AltraPassword123!',
        })
        self.assertFalse(form.is_valid()) 
        self.assertIn('password2', form.errors) 

    # t2: verifica che un utente non si può iscrivere se la sua mail risulta già iscritta --> crea uno user con una email, ne crea un altro con la stessa mail (errore di validazione)
    def test_email_duplicata_indipendentemente_dalle_maiuscole(self):
        User.objects.create_user('gia_esistente', 'Sara@Example.Test', 'PasswordTest123!')
        form = RegistrazioneForm(data={
            'username': 'nuovo_utente',
            'email': 'sara@example.test',
            'password1': 'PasswordTest123!',
            'password2': 'PasswordTest123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    # t3: verifica che il campo della mail sia normalizzato -> creo utente con email in maiuscolo, controllo che il form sia valido, controllo che mail inserita (maiusc) == mail in minuscolo
    def test_form_valido_normalizza_email(self):
        form = RegistrazioneForm(data={
            'username': 'nuovo_utente',
            'email': '  SARA@EXAMPLE.TEST  ',
            'password1': 'PasswordTest123!',
            'password2': 'PasswordTest123!',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['email'], 'sara@example.test')


# TEST PER LA CREAZIONE DEL PROFILO -> riguarda i dati inseriti da utente quando crea / modifica il profilo
class ProfiloModelTests(TestCase):

    # setUp dei dati di prova per il test (Il metodo appartiene alla classe)
    # prepara i dati di un utente (che restituisce utente, profilo)
    @classmethod
    def setUpTestData(cls):
        _, cls.profilo = crea_utente(1)

    # t1: calcolo dell'età -> imposto la data di nascita come quest'anno (1 gennaio) - 20, controllo che eta calcolata == 20 
    def test_eta_calcolata_a_partire_dalla_data(self):
        oggi = timezone.localdate()
        self.profilo.data_nascita = date(oggi.year - 20, 1, 1)
        self.assertEqual(self.profilo.eta, 20)

    # t2: accesso solo per i maggiorenni --> imposto la data di nascita == anno corrente - 17 anni, valido i dati (mi aspetto un'eccezione)
    # CASO LIMITE
    def test_minorenne_rifiutato(self):
        self.profilo.data_nascita = timezone.localdate() - timedelta(days=365 * 17)
        with self.assertRaises(ValidationError):
            self.profilo.full_clean()

    # t3: una persona non può inserire 2 volte la stessa lingua --> mi aspetto un'eccezione
    # CASO LIMITE
    def test_lingue_duplicate_rifiutate(self):
        self.profilo.lingue = ['Italiano', 'Italiano']
        with self.assertRaises(ValidationError):
            self.profilo.full_clean()

    # t4: una persona può inserire max 4 lingue --> mi aspetto un'eccezione
    # CASO LIMITE
    def test_piu_di_quattro_lingue_rifiutate(self):
        self.profilo.lingue = ['Italiano', 'Inglese', 'Spagnolo', 'Francese', 'Tedesco']
        with self.assertRaises(ValidationError):
            self.profilo.full_clean()

    # t5: validazione di tutti i dati del profilo
    def test_profilo_valido_supera_full_clean(self):
        self.profilo.full_clean()

# TEST PER LA SELEZIONE DEGL INTERESSI --> riguarda la selezione degli interessi da parte di un utente che si vuole registrare 
class SelezioneInteressiFormTests(TestCase):

    # setUp dei dati di prova: inizializza interesse padre, figlio, lista di altri 7 test
    @classmethod
    def setUpTestData(cls):
        cls.padre = Interesse.objects.create(nome='Cinema prova')
        cls.figlio = Interesse.objects.create(nome='Film prova', padre=cls.padre)
        cls.altri = [Interesse.objects.create(nome=f'Altro test {i}') for i in range(7)]

    # t1: deve essere inserito almeno 1 interesse
    # CASO LIMITE
    def test_nessun_interesse_non_valido(self):
        form = SelezioneInteressiForm(data={'interessi': []})
        self.assertFalse(form.is_valid())

    #t2: con 1 interesse il form è valido
    # CASO LIMITE
    def test_un_interesse_valido(self):
        form = SelezioneInteressiForm(data={'interessi': [self.padre.pk]})
        self.assertTrue(form.is_valid(), form.errors)

    # t3: fino a 6 interessi il form è valido
    # CASO LIMITE
    def test_sei_interessi_validi(self):
        form = SelezioneInteressiForm(data={'interessi': [i.pk for i in self.altri[:6]]})
        self.assertTrue(form.is_valid(), form.errors)

    # t4: da 7 interessi in poi il form non è valido 
    # CASO LIMITE
    def test_sette_interessi_non_validi(self):
        form = SelezioneInteressiForm(data={'interessi': [i.pk for i in self.altri]})
        self.assertFalse(form.is_valid())

    # t5: non posso inserire fra gli interessi sia la categoria generale che una sotto-categoria
    def test_padre_e_figlio_insieme_non_validi(self):
        form = SelezioneInteressiForm(data={'interessi': [self.padre.pk, self.figlio.pk]})
        self.assertFalse(form.is_valid())

# ============================================================
# TEST PER LA SEZIONE - PERSONE
# ============================================================

# TEST PER LIKE E DISLIKE -> riguarda la validazione dei modelli fra like e dislike
class LikeDislikeModelTests(TestCase):

    # setUp dei dati di prova: prepara 2 profili a, b
    @classmethod
    def setUpTestData(cls):
        _, cls.a = crea_utente(1)
        _, cls.b = crea_utente(2)

    # t1: una persona non può mettere like a se stessa --> prova a creare una situazione in cui mittente e destinatario sono la stessa persona, ci aspettiamo un'eccezione
    # CASO LIMITE 
    def test_autolike_rifiutato(self):
        with self.assertRaises(ValidationError):
            Like(
                mittente=self.a,
                destinatario=self.a
            ).full_clean()

    # t2: una persona non può mettere dislike a se stessa --> fa la stessa cosa di t1
    # CASO LIMITE
    def test_autodislike_rifiutato(self):
        with self.assertRaises(ValidationError):
            Dislike(
                mittente=self.a,
                destinatario=self.a
            ).full_clean()

    # t3: non posso mettere like dopo aver messo dislike con la stessa coppia di persone --> il like genera un'eccezione
    def test_like_dopo_dislike_rifiutato(self):
        Dislike.objects.create(
            mittente=self.a,
            destinatario=self.b
        )

        with self.assertRaises(ValidationError):
            Like(
                mittente=self.a,
                destinatario=self.b
            ).full_clean()

    # t4: non posso mettere dislike dopo aver messo like con la stessa coppia di persone --> stessa cosa di t3
    def test_dislike_dopo_like_rifiutato(self):
        Like.objects.create(
            mittente=self.a,
            destinatario=self.b
        )

        with self.assertRaises(ValidationError):
            Dislike(
                mittente=self.a,
                destinatario=self.b
            ).full_clean()

    # t5: non posso mettere 2 like alla stessa persona --> crea un like e poi un'altro identico, ci aspettiamo un'eccezione
    def test_due_like_stessa_direzione_vincolo_database(self):
        Like.objects.create(
            mittente=self.a,
            destinatario=self.b
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Like.objects.create(
                    mittente=self.a,
                    destinatario=self.b
                )


# TEST PER IL RANKING DELLE PERSONE --> riguarda il ranking delle persone
class PersoneRankingFiltriTests(TestCase):

    # setUp dei dati di prova: preperiamo 3 profili (a,b,c)
    # a - b : stessa città, stesso interesse
    # a - c, b - c: diversa città, stesso interesse
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(
            nome='Interesse ranking test'
        )

        cls.ua, cls.a = crea_utente(
            1,
            citta='Modena',
            interessi=[cls.interesse]
        )

        cls.ub, cls.b = crea_utente(
            2,
            citta='Modena',
            interessi=[cls.interesse]
        )

        cls.uc, cls.c = crea_utente(
            3,
            citta='Bologna',
            interessi=[cls.interesse]
        )

    # il client è ua --> ne viene forzato il login
    def setUp(self):
        self.client.force_login(self.ua)

    # t1: viene verificato che la persona a preferisce la persona b -> prendiamo la risposta quando entro nella sezione persone autenticato con utente a
    # prima cosa: controllo che lo status code == 200
    # seconda cosa: controllo che la prima persona mostrata sia b 
    def test_ranking_preferisce_persona_stessa_citta(self):
        risposta = self.client.get(reverse('persone'))

        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(
            risposta.context['persona'].pk,
            self.b.pk
        )

    # t2: test per il filtro della città 
    # prima cosa: controllo che status code == 200
    # seconda cosa: controllo che la prima persona mostrata sia c
    def test_filtro_citta_mostra_solo_candidati_coerenti(self):
        risposta = self.client.get(
            reverse('persone'),
            {'citta': 'Bologna'}
        )

        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(
            risposta.context['persona'].pk,
            self.c.pk
        )

    # t3: like e dislike escludono le persone 
    # A mette like a B, A mette dislike a C: quando riapre la pagina non compare nessun candidato
    # prima cosa: status code == 200
    # seconda cosa: quando riapre la pagina di persone la risposta è None
    def test_like_e_dislike_escludono_profili_dai_candidati(self):
        Like.objects.create(
            mittente=self.a,
            destinatario=self.b
        )

        Dislike.objects.create(
            mittente=self.a,
            destinatario=self.c
        )

        risposta = self.client.get(reverse('persone'))

        self.assertEqual(risposta.status_code, 200)
        self.assertIsNone(risposta.context['persona'])

    # t4: testa i filtri --> se filtro per una categoria padre, viene restituita anche la persona che ha come interesse una categoria figlia della categoria padre
    # crea 2 interessi (padre, figlio) e stabilisce la gerarchia
    # associa b - interesse figlio, c - nessun interesse, successivamente cerca di filtrare gli interessi in base all'interesse padre
    # prima cosa: verifica status code == 200
    # seconda cosa: verifica se la persona proposta == b (che ha associato interesse figlio)
    def test_filtro_interessi_riconosce_padre_e_figlio(self):
        padre = Interesse.objects.create(
            nome='Categoria test ranking'
        )

        figlio = Interesse.objects.create(
            nome='Sottocategoria test ranking',
            padre=padre
        )

        self.b.interessi.set([figlio])
        self.c.interessi.clear()

        risposta = self.client.get(
            reverse('persone'),
            {'interessi': [padre.pk]}
        )

        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(
            risposta.context['persona'].pk,
            self.b.pk
        )


# TEST PER I MATCH E LE CHAT -> riguarda la logica di formazione dei match e la distinazione fra match (no conversazione), match (chat iniziata)
class MatchChatViewTests(TestCase):

    # setUp dei dati: creo un interesse, creo utenti: a,b,c
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(
            nome='Interesse match'
        )

        cls.ua, cls.a = crea_utente(
            1, interessi=[cls.interesse]
        )
        cls.ub, cls.b = crea_utente(
            2, interessi=[cls.interesse]
        )
        cls.uc, cls.c = crea_utente(
            3, interessi=[cls.interesse]
        )

    # l'utente che fa i login forzato è utente a
    def setUp(self):
        self.client.force_login(self.ua)

    # t1: se non ci sono match, allora la lista è vuota --> apre la pagina match_chat quando non ci sono match ne chat e verifica che sia tutto vuoto
    # CASO LIMITE
    def test_nessun_match_liste_vuote(self):
        risposta = self.client.get(reverse('match_chat'))

        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(risposta.context['tutti_match'], [])
        self.assertEqual(risposta.context['chat_iniziate'], [])

    # t2: un like reciproco non crea un match --> crea like a -> b, prende la pagina match_chat e verifica che non ci siano match
    def test_like_non_reciproco_non_crea_match(self):
        Like.objects.create(
            mittente=self.a,
            destinatario=self.b
        )

        risposta = self.client.get(reverse('match_chat'))

        self.assertEqual(
            len(risposta.context['tutti_match']),
            0
        )

    # t3: 2 like reciproci creano un match --> viene creato un match a - b, viene verificato che nel profilo di a nella pagina match_chat ci sia (fra i match esistenti) anche quell con b mentre non ci sono chat iniziate
    def test_like_reciproci_nella_lista_match(self):
        crea_match(self.a, self.b)

        risposta = self.client.get(reverse('match_chat'))

        self.assertEqual(
            [
                x['persona'].pk
                for x in risposta.context['tutti_match']
            ],
            [self.b.pk]
        )

        self.assertEqual(
            len(risposta.context['chat_iniziate']),
            0
        )

    # t4: verifica che 2 persone con un match e una messaggio in passato, abbiano una chat nella pagina match_chat, e che la persona scompaia dai match
    def test_match_con_messaggio_passato_alla_lista_chat(self):
        crea_match(self.a, self.b)

        MessaggioPrivato.objects.create(
            mittente=self.a,
            destinatario=self.b,
            testo='Ciao!'
        )

        risposta = self.client.get(reverse('match_chat'))

        self.assertEqual(
            len(risposta.context['tutti_match']),
            0
        )

        self.assertEqual(
            [
                x['persona'].pk
                for x in risposta.context['chat_iniziate']
            ],
            [self.b.pk]
        )

    # t5: verifica che se esiste un messaggio fra b - c, l'utente a (autenticato) non riesce a vedere i messaggi fra i 2
    def test_messaggi_di_altri_non_visibili(self):
        crea_match(self.b, self.c)

        MessaggioPrivato.objects.create(
            mittente=self.b,
            destinatario=self.c,
            testo='Privato'
        )

        risposta = self.client.get(reverse('match_chat'))

        self.assertEqual(risposta.context['tutti_match'], [])
        self.assertEqual(risposta.context['chat_iniziate'], [])


# TEST PER LIKE E CHAT PRIVATA -> vengono verificate operazioni reali tramite richieste httè
class LikeEChatPrivateViewTests(TestCase):

    # setUp dei dati: inizializzo un interesse, utenti a - b
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(
            nome='Interesse chat'
        )

        cls.ua, cls.a = crea_utente(
            1, interessi=[cls.interesse]
        )

        cls.ub, cls.b = crea_utente(
            2, interessi=[cls.interesse]
        )

    # forzo il login dell'utente a
    def setUp(self):
        self.client.force_login(self.ua)

    # t1: un like crea una notifica per il destinatario 
    # A invia una POST alla view valuta_persona mettendo un like all'utente B
    # prima cosa: status code == 302 -> indica reindirizzamento
    # seconda cosa: deve esistere una notifica del like per B
    def test_like_crea_notifica_per_destinatario(self):
        risposta = self.client.post(
            reverse('valuta_persona', args=[self.b.pk]),
            {'azione': 'like'}
        )

        self.assertEqual(risposta.status_code, 302)

        self.assertTrue(
            Like.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

        self.assertTrue(
            Notifica.objects.filter(
                destinatario=self.b,
                tipo='LIKE_RICEVUTO'
            ).exists()
        )

    # t2: A prova ad aprire direttamente la chat privata con B senza che esistano like ricproci --> ci aspettiamo 404
    def test_chat_non_accessibile_senza_match(self):
        risposta = self.client.get(
            reverse('chat_privata', args=[self.b.pk])
        )

        self.assertEqual(risposta.status_code, 404)

    # t3: viene verificato che se esiste un match a - b, allora si può accedere alla chat --> ci aspettiamo sc = 200
    def test_chat_accessibile_con_match(self):
        crea_match(self.a, self.b)

        risposta = self.client.get(
            reverse('chat_privata', args=[self.b.pk])
        )

        self.assertEqual(risposta.status_code, 200)

    # t4: viene inviato un messaggio a -> b --> verifichiamo che il messaggio venga registrato nel db + b riceve la notifica
    def test_invio_messaggio_con_match(self):
        crea_match(self.a, self.b)

        risposta = self.client.post(
            reverse('chat_privata', args=[self.b.pk]),
            {'testo': 'Ciao dal test'}
        )

        self.assertEqual(risposta.status_code, 302)

        self.assertTrue(
            MessaggioPrivato.objects.filter(
                mittente=self.a,
                destinatario=self.b,
                testo='Ciao dal test'
            ).exists()
        )

        self.assertTrue(
            Notifica.objects.filter(
                destinatario=self.b,
                tipo='MESSAGGIO_PRIVATO'
            ).exists()
        )

    # t5: a prova ad inviare un messaggio che contiene solo spazi --> la view restituisce errore, non viene salvato il messaggio
    # CASO LIMITE
    def test_messaggio_vuoto_non_salvato(self):
        crea_match(self.a, self.b)

        risposta = self.client.post(
            reverse('chat_privata', args=[self.b.pk]),
            {'testo': '   '}
        )

        self.assertEqual(risposta.status_code, 400)
        self.assertFalse(MessaggioPrivato.objects.exists())

    # t6: a prova ad inviare un messaggio con più di 2000 caratteri --> la view restituisce errore, il messaggio non viene salvato
    # CASO LIMITE
    def test_messaggio_oltre_2000_caratteri_non_salvato(self):
        crea_match(self.a, self.b)

        risposta = self.client.post(
            reverse('chat_privata', args=[self.b.pk]),
            {'testo': 'a' * 2001}
        )

        self.assertEqual(risposta.status_code, 400)
        self.assertFalse(MessaggioPrivato.objects.exists())

    # t7: verifica che un messaggio di esattamente 2000 messaggi puo essere inviato
    # CASO LIMITE
    def test_messaggio_esattamente_2000_caratteri_valido(self):
        crea_match(self.a, self.b)

        testo = 'a' * 2000

        risposta = self.client.post(
            reverse('chat_privata', args=[self.b.pk]),
            {'testo': testo}
        )

        self.assertEqual(risposta.status_code, 302)

        self.assertTrue(
            MessaggioPrivato.objects.filter(
                mittente=self.a,
                destinatario=self.b,
                testo=testo
            ).exists()
        )



# TEST PER I LIKE RICEVUTI
class LikeRicevutiTests(TestCase):

    # setUp dei dati di prova: inizializzazione di un interesse, di utenti a - b
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(
            nome='Interesse like ricevuti'
        )

        cls.ua, cls.a = crea_utente(
            1, interessi=[cls.interesse]
        )

        cls.ub, cls.b = crea_utente(
            2, interessi=[cls.interesse]
        )

    # login forzato dell'utente a
    def setUp(self):
        self.client.force_login(self.ua)

    # t1: B mette like ad A --> A deve vedere il like nella pagina Like Ricevuti
    def test_like_ricevuto_non_ancora_valutato_visibile(self):
        Like.objects.create(
            mittente=self.b,
            destinatario=self.a
        )

        risposta = self.client.get(reverse('like_ricevuti'))

        self.assertEqual(risposta.status_code, 200)

        self.assertEqual(
            [
                like.mittente_id
                for like in risposta.context['like_ricevuti']
            ],
            [self.b.pk]
        )

    # t2: B mette like ad A, A risponde con like --> verifica che venga creato il like, verifica che venga notificato ad entrambi
    def test_risposta_like_crea_match_e_notifiche(self):
        Like.objects.create(
            mittente=self.b,
            destinatario=self.a
        )

        risposta = self.client.post(
            reverse('rispondi_like_ricevuto', args=[self.b.pk]),
            {'azione': 'like'}
        )

        self.assertRedirects(
            risposta,
            reverse('like_ricevuti')
        )

        self.assertTrue(
            Like.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

        self.assertEqual(
            Notifica.objects.filter(tipo='MATCH').count(),
            2
        )

    # t3: B mette like ad A, A risponde con dislike --> verifica che il dislike venga salvato
    def test_risposta_dislike_non_crea_match(self):
        Like.objects.create(
            mittente=self.b,
            destinatario=self.a
        )

        risposta = self.client.post(
            reverse('rispondi_like_ricevuto', args=[self.b.pk]),
            {'azione': 'dislike'}
        )

        self.assertRedirects(
            risposta,
            reverse('like_ricevuti')
        )

        self.assertTrue(
            Dislike.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

        self.assertFalse(
            Like.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

# TEST ANNULLAMENTO MATCH
# consigliato per l'orale, in part. test_annullamento_match_cancella_solo_dati_della_coppia
class AnnullamentoMatchIntegrazioneTests(TestCase):

    # setUp dei dati: inizializzo interesse, utente a-b-c
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(
            nome='Interesse annullamento'
        )

        cls.ua, cls.a = crea_utente(
            1, interessi=[cls.interesse]
        )

        cls.ub, cls.b = crea_utente(
            2, interessi=[cls.interesse]
        )

        cls.uc, cls.c = crea_utente(
            3, interessi=[cls.interesse]
        )

    # forzo il login dell'utente a
    def setUp(self):
        self.client.force_login(self.ua)

    # t1: in caso di annullamento, verifica che vengano eliminati solo i dati della coppia 
    def test_annullamento_match_cancella_solo_dati_della_coppia(self):

        # ARRANGE: prepariamo due Match indipendenti (a-b, a-c)
        crea_match(self.a, self.b)
        crea_match(self.a, self.c)

        # creo dei messaggi (a,b) (b,a) (a,c)
        MessaggioPrivato.objects.create(
            mittente=self.a,
            destinatario=self.b,
            testo='Messaggio A-B'
        )

        MessaggioPrivato.objects.create(
            mittente=self.b,
            destinatario=self.a,
            testo='Risposta B-A'
        )

        MessaggioPrivato.objects.create(
            mittente=self.a,
            destinatario=self.c,
            testo='Messaggio A-C'
        )

        self.assertEqual(MessaggioPrivato.objects.count(), 3)

        # viene annullato il match fra a - b 
        risposta = self.client.post(
            reverse('annulla_match', args=[self.b.pk])
        )

        # verifico che vengo reindirizzato alla pagina match chat
        self.assertRedirects(
            risposta,
            reverse('match_chat')
        )   

        # verifico che i like a-b e b-a non esistano piu, e che il dislike a-b esista
        self.assertFalse(
            Like.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

        self.assertTrue(
            Like.objects.filter(
                mittente=self.b,
                destinatario=self.a
            ).exists()
        )

        self.assertTrue(
            Dislike.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

        # verifico che non esistano i messaggi (a,b) (b,a) 
        self.assertFalse(
            MessaggioPrivato.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

        self.assertFalse(
            MessaggioPrivato.objects.filter(
                mittente=self.b,
                destinatario=self.a
            ).exists()
        )

        # verifico che i messaggi (a,c) e i rispettivi like esistano ancora -> e quindi è presente 1 solo messaggio in tutto
        self.assertTrue(
            Like.objects.filter(
                mittente=self.a,
                destinatario=self.c
            ).exists()
        )

        self.assertTrue(
            Like.objects.filter(
                mittente=self.c,
                destinatario=self.a
            ).exists()
        )

        self.assertTrue(
            MessaggioPrivato.objects.filter(
                mittente=self.a,
                destinatario=self.c
            ).exists()
        )

        self.assertEqual(MessaggioPrivato.objects.count(), 1)

        # veriico che A non può più accedere alla chat con B, e non lo visualizza neanche nei match
        risposta_chat = self.client.get(
            reverse('chat_privata', args=[self.b.pk])
        )

        self.assertEqual(risposta_chat.status_code, 404)

        elenco = self.client.get(reverse('match_chat'))

        self.assertNotIn(
            self.b.pk,
            [
                x['persona'].pk
                for x in elenco.context['tutti_match']
            ]
        )

        self.assertNotIn(
            self.b.pk,
            [
                x['persona'].pk
                for x in elenco.context['chat_iniziate']
            ]
        )

    # t2: non è possibile annullare un match se è inestitente -> provo ad annullare un match con b, mi aspetto risposta di errore e che non venga salvato il dislike a - b
    # il match non esiste perchè non è stato chiamato crea_match()
    def test_annullamento_senza_match_non_consentito(self):
        risposta = self.client.post(
            reverse('annulla_match', args=[self.b.pk])
        )

        self.assertEqual(risposta.status_code, 404)

        self.assertFalse(
            Dislike.objects.filter(
                mittente=self.a,
                destinatario=self.b
            ).exists()
        )

# ============================================================
# TEST PER LA SEZIONE - COMMUNITY 
# ============================================================

# TEST PER IL RANKING DELLA COMMUNITY --> riguarda filtraggio e ranking delle community
class FunzioniRankingCommunityTests(TestCase):

    # setUp dei dati di prova: creo 2 utenti (organizzatore e utente), creo 1 interesse padre, creo 1 interesse figlio, creo una community 
    @classmethod
    def setUpTestData(cls):
        _, cls.organizzatore = crea_utente(1)
        _, cls.utente = crea_utente(2)
        cls.sport = Interesse.objects.create(nome='Sport prova')
        cls.tennis = Interesse.objects.create(nome='Tennis prova', padre=cls.sport)
        cls.gruppo = crea_community(cls.organizzatore)

    # t1: verificare che il punteggio di una community venga calcolato usando la formula bayesiana --> imposto una media di 2 valutazioni da 5 stelle l'una, ma il punteggio pubblico tiene conto anche di un valore di riferimento
    # il test dimostra che calcolo del punteggio != calcolo della media
    def test_media_diversa_da_punteggio_bayesiano(self):
        self.gruppo.numero_valutazioni = 2
        self.gruppo.somma_valutazioni = 10

        self.assertAlmostEqual(
            calcola_punteggio_pubblico(self.gruppo), 25 / 7
        )
        self.assertEqual(self.gruppo.media_valutazioni, 5)

    # t2: verifico che il ranking riconosca 2 città uguali anche quando vengono scritte in maiusc / minusc
    def test_compatibilita_stessa_citta_case_insensitive(self):
        self.gruppo.citta = 'MODENA'
        self.utente.citta = 'modena'

        self.assertEqual(
            calcola_compatibilita_community(self.gruppo, self.utente), 4
        )

    # t3: verifica che il ranking riconosca una compatibilità parziale fra interessi appartenenti alla stessa gerarchia
    def test_compatibilita_padre_figlio(self):
        self.gruppo.citta = 'Bologna'
        self.gruppo.interessi.set([self.sport])
        self.utente.interessi.set([self.tennis])

        self.assertEqual(
            calcola_compatibilita_community(self.gruppo, self.utente), 1
        )

# TEST PER LE RICHIESTE DELLA COMMUNITY 
# esame test
class RichiesteCommunityIntegrazioneTests(TestCase):

    # setUp dei dati di prova: inizializzo interesse, inizializzo un utente organizzatore, uno membro e uno estraneo, inizializzo una community che ha un certo organizzatore e l'interesse
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(nome='Interesse richieste')
        cls.uo, cls.organizzatore = crea_utente(1, interessi=[cls.interesse])
        cls.um, cls.membro = crea_utente(2, interessi=[cls.interesse])
        cls.ux, cls.estraneo = crea_utente(3, interessi=[cls.interesse])
        cls.gruppo = crea_community(
            cls.organizzatore, interessi=[cls.interesse]
        )

    # t1: verifica l'intero processo di richiesta di partecipazione ad una community (dall'invio all'accettazione)
    def test_richiesta_e_accettazione_con_notifiche(self):

        # forzo il login di utente membro
        self.client.force_login(self.um)

        # invia una richiesta alla community
        invio = self.client.post(
            reverse('invia_richiesta_community', args=[self.gruppo.pk])
        )

        # controllo che venga effettuato redirect
        self.assertEqual(invio.status_code, 302)

        # creo la richiesta da membro al gruppo 
        richiesta = RichiestaCommunity.objects.get(
            utente=self.membro,
            community=self.gruppo
        )

        # lo stato deve essere in attesa
        self.assertEqual(richiesta.stato, 'PENDING')

        # verifica l'esistenza della notifica per l'organizzatore
        self.assertTrue(
            Notifica.objects.filter(
                destinatario=self.organizzatore,
                tipo='RICHIESTA_COMMUNITY'
            ).exists()
        )

        # verifica che il membro non faccia parte della community ancora
        self.assertFalse(
            self.gruppo.membri.filter(pk=self.membro.pk).exists()
        )

        # forzo il login dell'organizzatore: accetta la richiesta e verifichiamo l'esito dell'azione (deve essere redirect)
        self.client.force_login(self.uo)

        risposta = self.client.post(
            reverse(
                'gestisci_richiesta_community',
                args=[self.gruppo.pk, richiesta.pk]
            ),
            {'azione': 'accetta'}
        )

        self.assertEqual(risposta.status_code, 302)

        # eseguiamo refresh 
        richiesta.refresh_from_db()

        # ora la richiesta è accettata 
        self.assertEqual(richiesta.stato, 'ACCEPTED')

        # ora il membro fa parte della community
        self.assertTrue(
            self.gruppo.membri.filter(pk=self.membro.pk).exists()
        )
        
        # viene inviata una richiesta al membro
        self.assertTrue(
            Notifica.objects.filter(
                destinatario=self.membro,
                tipo='RICHIESTA_ACCETTATA'
            ).exists()
        )   

    # t2: caso in cui la richiesta viene rifiutata
    def test_rifiuto_non_aggiunge_membro(self):

        # inizializzazione della richiesta da parte del membro
        richiesta = RichiestaCommunity.objects.create(
            utente=self.membro,
            community=self.gruppo
        )

        # login forzato dell'organizzatore: rifiuta la richiesta, controlliamo che lo status code == redirect
        self.client.force_login(self.uo)

        risposta = self.client.post(
            reverse(
                'gestisci_richiesta_community',
                args=[self.gruppo.pk, richiesta.pk]
            ),
            {'azione': 'rifiuta'}
        )

        self.assertEqual(risposta.status_code, 302)

        # refresh dal db
        richiesta.refresh_from_db()

        # ora lo stato della richiesta deve essere rifiutata
        self.assertEqual(richiesta.stato, 'REJECTED')

        # il membro non deve fare parte dei membri della community
        self.assertFalse(   
            self.gruppo.membri.filter(pk=self.membro.pk).exists()
        )

    # t3: solo l'organizzatore può gestire le richieste di partecipazione
    def test_estraneo_non_puo_gestire_richiesta(self):

        # inizializzo la richiesta
        richiesta = RichiestaCommunity.objects.create(
            utente=self.membro,
            community=self.gruppo
        )
        
        # forzo il login dell'estraneo: se prova a fare accetta si viene rendirizzati ad errore
        self.client.force_login(self.ux)

        risposta = self.client.post(
            reverse(
                'gestisci_richiesta_community',
                args=[self.gruppo.pk, richiesta.pk]
            ),
            {'azione': 'accetta'}
        )

        self.assertEqual(risposta.status_code, 404)

        #refresh dal db
        richiesta.refresh_from_db()

        # lo stato della richiesta non è cambiato
        self.assertEqual(richiesta.stato, 'PENDING')

    # t4: verifica che un utente non può creare 2 richieste di partecipazione contemporanee alla stessa community
    def test_richiesta_duplicata_non_accettata(self):

        # inizializzata la richiesta di membro alla community
        RichiestaCommunity.objects.create(
            utente=self.membro,
            community=self.gruppo
        )

        # forzato il login del membro: invia di nuovo la richiesta, verifichiamo che generi errore e che nel db ci sia comunque 1 sola richiesta inviata da quel membro per quella community
        self.client.force_login(self.um)

        risposta = self.client.post(
            reverse('invia_richiesta_community', args=[self.gruppo.pk])
        )

        self.assertEqual(risposta.status_code, 404)

        self.assertEqual(
            RichiestaCommunity.objects.filter(
                utente=self.membro,
                community=self.gruppo
            ).count(),
            1
        )

# TEST PER LA VALUTAZIONE DELLA COMMUNITY
class ValutazioniCommunityTests(TestCase):

    # setUp dati: creo un interesse, un utente organizzatore che ha l'interesse, un utente membro che ha un interesse, una community che ha quell'interesse e come membro l'utente membro
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(nome='Interesse valutazioni')
        cls.uo, cls.organizzatore = crea_utente(1, interessi=[cls.interesse])
        cls.um, cls.membro = crea_utente(2, interessi=[cls.interesse])
        cls.gruppo = crea_community(
            cls.organizzatore, interessi=[cls.interesse]
        )
        cls.gruppo.membri.add(cls.membro)

    # t1: un membro può valutare e poi modificare il voto senza creare 2 diverse valutazioni
    def test_membro_puo_valutare_e_modificare_il_voto(self):

        # forzo il login del membro: controllo se 
        self.client.force_login(self.um)

        url = reverse('valuta_community', args=[self.gruppo.pk])

        # l'utente valuta la community con voto = 5, verifico che avvenga redirect
        self.assertEqual(
            self.client.post(url, {'voto': '5'}).status_code,
            302
        )
        
        # prendo il voto appena creato (dal membro per il gruppo) e verifico che == 5
        voto = ValutazioneCommunity.objects.get(
            utente=self.membro,
            community=self.gruppo
        )

        self.assertEqual(voto.voto, 5)

        # il membro vota nuovamente con voto = 3 
        self.assertEqual(
            self.client.post(url, {'voto': '3'}).status_code,
            302
        )

        # refresh del db 
        voto.refresh_from_db()

        # verifico che voto = 3 attualmente, ma anche che nel db c'è 1 solo elemento di valutazione
        self.assertEqual(voto.voto, 3)
        self.assertEqual(ValutazioneCommunity.objects.count(), 1)

    # t2: verifica che l'organizzatore non può valutare
    def test_organizzatore_non_puo_valutare(self):

        # forzo il login dell'organizzatore
        self.client.force_login(self.uo)

        # valuta la community con voto = 5
        risposta = self.client.post(
            reverse('valuta_community', args=[self.gruppo.pk]),
            {'voto': '5'}
        )

        # quest'azione restituisce un errore
        self.assertEqual(risposta.status_code, 404)

    # t3: verifica che la valutazione rimanga anche quando esco dalla community 
    def test_valutazione_rimane_dopo_uscita_community(self):

        # crea una valutazione per una community
        ValutazioneCommunity.objects.create(
            utente=self.membro,
            community=self.gruppo,
            voto=4
        )

        # forza il login del membro, che esce dalla community (inf. non fa più parte dei membri)
        self.client.force_login(self.um)

        risposta = self.client.post(
            reverse('esci_community', args=[self.gruppo.pk])
        )

        self.assertEqual(risposta.status_code, 302)

        self.assertFalse(
            self.gruppo.membri.filter(pk=self.membro.pk).exists()
        )

        # verifico che il voto che aveva messo il membro esista ancora
        self.assertTrue(
            ValutazioneCommunity.objects.filter(
                utente=self.membro,
                community=self.gruppo,
                voto=4
            ).exists()
        )

# TEST PER LA CHAT DELLA COMMUNITY 
class ChatCommunityTests(TestCase):

    # setUp dati di prova: inizializzo interesse, organizzatore, membro, estraneo, community che ha quell'interesse e quell'organizzatore e quel membro
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(nome='Interesse chat community')
        cls.uo, cls.organizzatore = crea_utente(1, interessi=[cls.interesse])
        cls.um, cls.membro = crea_utente(2, interessi=[cls.interesse])
        cls.ux, cls.estraneo = crea_utente(3, interessi=[cls.interesse])
        cls.gruppo = crea_community(
            cls.organizzatore, interessi=[cls.interesse]
        )
        cls.gruppo.membri.add(cls.membro)

    # t1: testo che un membro può accedere alla chat -> se il membro prova ad andare sulla chat di gruppo, ha come sc = 200
    def test_membro_puo_accedere_chat(self):
        self.client.force_login(self.um)

        risposta = self.client.get(
            reverse('chat_gruppo', args=[self.gruppo.pk])
        )

        self.assertEqual(risposta.status_code, 200)

    # t2: testo che un utente non membro non può accedere alla chat -> se l'utente prova ad andare sulla chat di gruppo, viene restituito 404
    def test_estraneo_non_puo_accedere_chat(self):
        self.client.force_login(self.ux)

        risposta = self.client.get(
            reverse('chat_gruppo', args=[self.gruppo.pk])
        )

        self.assertEqual(risposta.status_code, 404)

    # t3: testa che un membro può scrivere
    def test_membro_puo_scrivere(self):

        # login del membro: scrive un messaggio sulla chat di gruppo -> sc = redirect
        self.client.force_login(self.um)

        risposta = self.client.post(
            reverse('chat_gruppo', args=[self.gruppo.pk]),
            {'testo': 'Ciao gruppo'}
        )

        self.assertEqual(risposta.status_code, 302)

        # verifico che il messaggio esista veramente
        self.assertTrue(
            MessaggioCommunity.objects.filter(
                autore=self.membro,
                community=self.gruppo,
                testo='Ciao gruppo'
            ).exists()
        )

# TEST PER GLI EVENTI DELLA COMMUNITY
class EventiCommunityTests(TestCase):

    # setUp dati di prova: inizializzo interesse, organizzatore, membro, community che ha quell'interesse e il membro 
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(nome='Interesse eventi')
        cls.uo, cls.organizzatore = crea_utente(1, interessi=[cls.interesse])
        cls.um, cls.membro = crea_utente(2, interessi=[cls.interesse])
        cls.gruppo = crea_community(
            cls.organizzatore, interessi=[cls.interesse]
        )
        cls.gruppo.membri.add(cls.membro)

    # t1: non posso creare evento che ha data di fine precedente a quella di inizio
    # CASO LIMITE
    def test_evento_con_fine_precedente_inizio_rifiutato(self):
        inizio = timezone.now() + timedelta(days=7)

        evento = Evento(
            community=self.gruppo,
            titolo='Evento prova',
            luogo='Modena',
            inizio=inizio,
            fine=inizio - timedelta(hours=1),
            costo=Decimal('0.00')
        )

        # deve sollevare errore
        with self.assertRaises(ValidationError):
            evento.full_clean()

    # t2: un evento con date coerenti e dati validi deve superare la validazione
    def test_evento_futuro_valido(self):
        inizio = timezone.now() + timedelta(days=7)

        evento = Evento(
            community=self.gruppo,
            titolo='Evento futuro',
            luogo='Modena',
            inizio=inizio,
            fine=inizio + timedelta(hours=2),
            costo=Decimal('3.00')
        )

        evento.full_clean()

    # t3: solo l'organizzatore può aprire il form di creazione
    def test_solo_organizzatore_puo_aprire_form_creazione(self):

        url = reverse(
            'creazione_evento_community',
            args=[self.gruppo.pk]
        )

        # forzo il login del membro -> provo ad aprire l'url di creazione ma mi da errore
        self.client.force_login(self.um)
        self.assertEqual(self.client.get(url).status_code, 404)

        # forzo il login dell'organizzatore -> provo ad aprire l'url di creazione e restituisce che va bene
        self.client.force_login(self.uo)
        self.assertEqual(self.client.get(url).status_code, 200)

    # t5: verifica che un evento non può avere inizio esattamente uguale alla fine -> solleva un'eccezione
    # CASO LIMITE
    def test_evento_con_inizio_e_fine_uguali_rifiutato(self):
        inizio = timezone.now() + timedelta(days=7)

        evento = Evento(
            community=self.gruppo,
            titolo='Evento prova',
            luogo='Modena',
            inizio=inizio,
            fine=inizio,
            costo=Decimal('0.00')
        )

        with self.assertRaises(ValidationError):
            evento.full_clean()


# ============================================================
# TEST PER LA SEZIONE - NOTIFICHE
# ============================================================

# TEST PER LE NOTIFICHE
class NotificheTests(TestCase):

    # setUp dati di prova: inizializzo interesse, utente-a e utente-b che hanno quell'interesse
    @classmethod
    def setUpTestData(cls):
        cls.interesse = Interesse.objects.create(nome='Interesse notifiche')
        cls.ua, cls.a = crea_utente(1, interessi=[cls.interesse])
        cls.ub, cls.b = crea_utente(2, interessi=[cls.interesse])

    # t1: quando apro una pagina le notifiche sono segnate come lette
    def test_aprire_pagina_segna_notifiche_come_lette(self):

        # inizializzo una notifica destinata ad utente a (utenteb gli ha messo like)
        notifica = Notifica.objects.create(
            destinatario=self.a,
            tipo='LIKE_RICEVUTO',
            testo='Like ricevuto',
            profilo_collegato=self.b
        )

        # faccio login di utente a
        self.client.force_login(self.ua)

        risposta = self.client.get(reverse('notifiche'))

        self.assertEqual(risposta.status_code, 200)

        # facendo il refresh la notifica diventa letta
        notifica.refresh_from_db()

        self.assertTrue(notifica.letta)
    
    # t2: un utente non può aprire le notifiche di un altro utente
    def test_un_utente_non_puo_aprire_notifiche_altrui(self):

        # inizializzo notifica destinata ad A
        notifica = Notifica.objects.create(
            destinatario=self.a,
            tipo='LIKE_RICEVUTO',
            testo='Solo per A'
        )

        # forzo il login di B: prova ad aprire la notifica ma viene errore 404
        self.client.force_login(self.ub)

        risposta = self.client.post(
            reverse('apri_notifica', args=[notifica.pk])
        )

        self.assertEqual(risposta.status_code, 404)

        # se faccio refresh dal db, comunque la notifica rimane non letta
        notifica.refresh_from_db()

        self.assertFalse(notifica.letta)

    # t3: aprire una notifica di like da parte di qualcuno, mi porta a like_ricevuti
    def test_apertura_notifica_like_reindirizza_a_like_ricevuti(self):

        # inizializzo notifica destinata ad a
        notifica = Notifica.objects.create(
            destinatario=self.a,
            tipo='LIKE_RICEVUTO',
            testo='Like ricevuto',
            profilo_collegato=self.b
        )

        # forzo il login di a: apre la notifica, viene rendirizzata ad una pagina che inizia con 'like_ricevuti'
        self.client.force_login(self.ua)

        risposta = self.client.post(
            reverse('apri_notifica', args=[notifica.pk])
        )

        self.assertEqual(risposta.status_code, 302)

        self.assertTrue(
            risposta.url.startswith(reverse('like_ricevuti'))
        )

        # facendo un refresh, la notifica viene segnata come letta
        notifica.refresh_from_db()

        self.assertTrue(notifica.letta)


# ============================================================
# TEST PER LA SEZIONE - CONTROLLO DEGLI ACCESSI
# ============================================================

# TEST PER IL CONTROLLO DEGLI ACCESS
class ControlloAccessiViewTests(TestCase):

    # setUp dati prova: utente1 senza profilo, utente2 con profilo ma senza interessi, utente3 con profilo completo
    @classmethod
    def setUpTestData(cls):
        cls.utente_senza_profilo, _ = crea_utente(1, completo=False)
        cls.utente_senza_interessi, cls.profilo_senza_interessi = crea_utente(2)

        cls.interesse = Interesse.objects.create(nome='Interesse accessi')

        cls.utente_completo, cls.profilo_completo = crea_utente(
            3, interessi=[cls.interesse]
        )

    # t1: verifico che la home pubblica sia visibile anche senza aver effettuato il login --> corretto, 200
    def test_home_pubblica_visibile_senza_login(self):
        risposta = self.client.get(reverse('home_pubblica'))
        self.assertEqual(risposta.status_code, 200)

    # t2: le pagine riservate richiedono il login 
    def test_pagine_riservate_richiedono_login(self):

        # definisco l'insieme di pagine riservate (non tutte, solo alcune)
        pagine = (
            'home',
            'persone',
            'community',
            'profilo',
            'notifiche',
            'match_chat',
            'like_ricevuti',
            'community_gestite',
            'creazione_community',
            'modifica_profilo',
            'cambia_password',
        )

        # scorro tutte le pagine: prendendo in considerazione ogni pagina
        for nome in pagine:

            # creo un sottotest per ogni pagina e provo ad accederci
            with self.subTest(pagina=nome):
                risposta = self.client.get(reverse(nome))

                # controlla che la risposta http reindirizzi l'utente verso un URL specifico (creato come indicato li sotto)
                self.assertRedirects(
                    risposta,
                    f"{reverse('login')}?next={reverse(nome)}"
                )

    # t3: un utente che ha solo user prova ad entrare in pagine alle quali possono accedere solo utenti autenticati, verifica che non può fin quando non ha completato il profilo
    def test_senza_profilo_redirect_creazione(self):
        self.client.force_login(self.utente_senza_profilo)

        pagine = (
            'home',
            'persone',
            'community',
            'profilo',
            'notifiche',
        )

        for nome in pagine:
            with self.subTest(pagina=nome):
                risposta = self.client.get(reverse(nome))

                # viene reindirizzato alla creazione del profilo
                self.assertRedirects(
                    risposta,
                    reverse('creazione_profilo')
                )

    # t4: un utente che ha user + profilo prova ad entrare in pagine alle quali possono accedere solo utenti autenticati
    def test_senza_interessi_redirect_selezione(self):
        self.client.force_login(self.utente_senza_interessi)

        pagine = (
            'home',
            'persone',
            'community',
            'profilo',
            'notifiche',
        )

        for nome in pagine:
            with self.subTest(pagina=nome):
                risposta = self.client.get(reverse(nome))

                # reindirizzato alla selezione interessi
                self.assertRedirects(
                    risposta,
                    reverse('selezione_interessi')
                )

    # t5: verifica che un utente con profilo completo può accedere all'area riservata
    def test_utente_completo_accede_area_riservata(self):
        self.client.force_login(self.utente_completo)

        pagine = (
            'home',
            'persone',
            'community',
            'profilo',
            'notifiche',
            'match_chat',
        )

        for nome in pagine:
            with self.subTest(pagina=nome):
                risposta = self.client.get(reverse(nome))

                # verifica che lo status code == ok 
                self.assertEqual(risposta.status_code, 200)