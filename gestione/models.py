from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, MinLengthValidator
from django.utils import timezone
from decimal import Decimal

# MODEL INTERESSE
class Interesse(models.Model):

    nome = models.CharField(
        max_length=50
    )

    padre = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sottointeressi'
    )

    # verifica dei vincoli
    def clean(self):
        super().clean()

        # Un interesse non può essere padre di sé stesso
        if self.pk is not None and self.padre_id == self.pk:
            raise ValidationError({
                'padre': 'Un interesse non può essere padre di sé stesso.'
            })

        # La gerarchia può avere soltanto due livelli
        if self.padre_id is not None:

            if self.padre.padre_id is not None:
                raise ValidationError({
                    'padre': 'Un sotto-interesse non può avere altri sotto-interessi.'
                })

            # Un interesse con figli non può diventare sotto-interesse
            if self.pk is not None and self.sottointeressi.exists():
                raise ValidationError({
                    'padre': 'Un interesse che possiede sotto-interessi non può avere un padre.'
                })

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = 'Interessi'

# MODEL PROFILO
class Profilo(models.Model):

    # Scelte predefinite: servono per definire i field

    GENERI = [
        ('DONNA', 'Donna'),
        ('UOMO', 'Uomo'),
        ('NON_BINARIO', 'Non binario'),
        ('ALTRO', 'Altro'),
        ('PREFERISCO_NON_DIRLO', 'Preferisco non dirlo'),
    ]

    OCCUPAZIONI = [
        ('STUDENTE', 'Studente'),
        ('LAVORATORE', 'Lavoratore'),
        ('STUDENTE_LAVORATORE', 'Studente lavoratore'),
        ('DISOCCUPATO', 'Disoccupato'),
    ]

    LINGUE_DISPONIBILI = [
        'Italiano',
        'Inglese',
        'Spagnolo',
        'Francese',
        'Tedesco',
        'Portoghese',
        'Cinese',
        'Giapponese',
        'Arabo',
        'Russo',
    ]

    COSA_CERCA = [
        'AMICIZIE',
        'COMPAGNO_STUDIO',
        'COINQUILINO',
    ]

    # Field del modello

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profilo'
    )

    nome = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(2),
            RegexValidator(
                regex=r'^[^\W\d\_]+$',
                message='Il nome deve contenere solo lettere.'
            )
        ]
    )

    foto = models.ImageField(
        upload_to='profili/'
    )

    data_nascita = models.DateField()

    genere = models.CharField(
        max_length=25,
        choices=GENERI
    )

    citta = models.CharField(
        max_length=100
    )

    occupazione = models.CharField(
        max_length=20,
        choices=OCCUPAZIONI,
        blank=True,
        default=''
    )

    lingue = models.JSONField(
        default=list
    )

    descrizione = models.TextField(
        max_length=500,
        blank=True,
        default=''
    )

    cosa_cerca = models.JSONField(
        default=list
    )

    interessi = models.ManyToManyField(
        'Interesse',
        related_name='profili',
        blank=True
    )

    # Validazione vincoli

    def clean(self):
        super().clean()

        # Validazione età
        if self.data_nascita is not None:
            oggi = timezone.localdate()

            eta = oggi.year - self.data_nascita.year

            if (oggi.month, oggi.day) < (
                self.data_nascita.month,
                self.data_nascita.day
            ):
                eta -= 1

            if eta < 18:
                raise ValidationError({
                    'data_nascita': 'Devi essere maggiorenne.'
                })

        # Verifica della lingua
        if not isinstance(self.lingue, list):
            raise ValidationError({
                'lingue': 'Selezione delle lingue non valida.'
            })

        if not 1 <= len(self.lingue) <= 4:
            raise ValidationError({
                'lingue': 'Devi selezionare da 1 a 4 lingue.'
            })

        if len(self.lingue) != len(set(map(str, self.lingue))):
            raise ValidationError({
                'lingue': 'Non puoi selezionare la stessa lingua più volte.'
            })

        if any(
            lingua not in self.LINGUE_DISPONIBILI
            for lingua in self.lingue
        ):
            raise ValidationError({
                'lingue': 'Una o più lingue non sono valide.'
            })

        # Verifica cosa_cerca
        if not isinstance(self.cosa_cerca, list):
            raise ValidationError({
                'cosa_cerca': 'Selezione non valida.'
            })

        if not 1 <= len(self.cosa_cerca) <= 3:
            raise ValidationError({
                'cosa_cerca': 'Devi selezionare almeno una voce.'
            })

        if len(self.cosa_cerca) != len(set(map(str, self.cosa_cerca))):
            raise ValidationError({
                'cosa_cerca': 'Non puoi selezionare valori duplicati.'
            })

        if any(
            valore not in self.COSA_CERCA
            for valore in self.cosa_cerca
        ):
            raise ValidationError({
                'cosa_cerca': 'Una o più scelte non sono valide.'
            })

    # Informazioni derivate

    @property
    def eta(self):
        oggi = timezone.localdate()

        anni = oggi.year - self.data_nascita.year

        if (oggi.month, oggi.day) < (
            self.data_nascita.month,
            self.data_nascita.day
        ):
            anni -= 1

        return anni

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = 'Profili'

# MODEL LIKE
class Like(models.Model):

    mittente = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='like_inviati'
    )

    destinatario = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='like_ricevuti'
    )

    data_ora = models.DateTimeField(
        auto_now_add=True
    )

    # Validazione vincoli
    def clean(self):
        super().clean()

        # Un utente non può mettere Like a sé stesso
        if self.mittente_id is not None and self.mittente_id == self.destinatario_id:
            raise ValidationError(
                'Non puoi mettere Like a te stesso.'
            )

        # Non possono esistere contemporaneamente un Like e un Dislike per la stessa coppia
        if self.mittente_id is not None and self.destinatario_id is not None:

            if Dislike.objects.filter(
                mittente_id=self.mittente_id,
                destinatario_id=self.destinatario_id
            ).exists():
                raise ValidationError(
                    'Hai già espresso un Dislike verso questo profilo.'
                )

    def __str__(self):
        return f'{self.mittente} → {self.destinatario}'

    class Meta:
        verbose_name_plural = 'Like'

        constraints = [
            models.UniqueConstraint(
                fields=['mittente', 'destinatario'],
                name='like_unico_per_coppia'
            ),

            models.CheckConstraint(
                condition=~models.Q(mittente=models.F('destinatario')),
                name='like_no_autolike'
            )
        ]

# MODEL DISLIKE
class Dislike(models.Model):

    mittente = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='dislike_inviati'
    )

    destinatario = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='dislike_ricevuti'
    )

    data_ora = models.DateTimeField(
        auto_now_add=True
    )

    # Vincoli di validazione
    def clean(self):
        super().clean()

        # Un utente non può mettere Dislike a sé stesso
        if self.mittente_id is not None and self.mittente_id == self.destinatario_id:
            raise ValidationError(
                'Non puoi mettere Dislike a te stesso.'
            )

        # Non possono esistere contemporaneamentevA un Like e un Dislike per la stessa coppia
        if self.mittente_id is not None and self.destinatario_id is not None:

            if Like.objects.filter(
                mittente_id=self.mittente_id,
                destinatario_id=self.destinatario_id
            ).exists():
                raise ValidationError(
                    'Hai già espresso un Like verso questo profilo.'
                )

    def __str__(self):
        return f'{self.mittente} → {self.destinatario}'

    class Meta:
        verbose_name_plural = 'Dislike'

        constraints = [
            models.UniqueConstraint(
                fields=['mittente', 'destinatario'],
                name='dislike_unico_per_coppia'
            ),

            models.CheckConstraint(
                condition=~models.Q(mittente=models.F('destinatario')),
                name='dislike_no_autodislike'
            )
        ]

# MODEL MESSAGGIO_PRIVATO
class MessaggioPrivato(models.Model):

    mittente = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='messaggi_privati_inviati'
    )

    destinatario = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='messaggi_privati_ricevuti'
    )

    testo = models.TextField(
        max_length=2000
    )

    data_ora = models.DateTimeField(
        auto_now_add=True
    )

    # vincoli di validazione
    def clean(self):
        super().clean()

        if self.mittente_id is not None and self.destinatario_id is not None:

            # Un utente non può inviare messaggi a sé stesso
            if self.mittente_id == self.destinatario_id:
                raise ValidationError(
                    'Non puoi inviare un messaggio a te stesso.'
                )

            # Controllo dell'esistenza di un Match
            like_inviato = Like.objects.filter(
                mittente_id=self.mittente_id,
                destinatario_id=self.destinatario_id
            ).exists()

            like_ricevuto = Like.objects.filter(
                mittente_id=self.destinatario_id,
                destinatario_id=self.mittente_id
            ).exists()

            if not (like_inviato and like_ricevuto):
                raise ValidationError(
                    'Puoi inviare messaggi soltanto agli utenti con cui hai un Match.'
                )

    def __str__(self):
        return f'Messaggio da {self.mittente} a {self.destinatario}'

    class Meta:
        verbose_name_plural = 'Messaggi privati'
        ordering = ['data_ora', 'id']

# MODEL COMMUNITY
class Community(models.Model):

    titolo = models.CharField(
        max_length=100
    )

    descrizione = models.TextField(
        max_length=1000
    )

    immagine = models.ImageField(
        upload_to='community/',
        blank=True,
        default='community/default.png'
    )

    organizzatore = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='community_organizzate'
    )

    citta = models.CharField(
        max_length=100
    )

    data_creazione = models.DateTimeField(
        auto_now_add=True
    )

    interessi = models.ManyToManyField(
        'Interesse',
        related_name='community',
        blank=True
    )

    membri = models.ManyToManyField(
        'Profilo',
        related_name='community_partecipate',
        blank=True
    )

    def __str__(self):
        return self.titolo

    class Meta:
        verbose_name_plural = 'Community'

# MODEL RICHIESTA_COMMUNITY
class RichiestaCommunity(models.Model):

    STATI_RICHIESTA = [
        ('PENDING', 'In attesa'),
        ('ACCEPTED', 'Accettata'),
        ('REJECTED', 'Rifiutata'),
    ]

    utente = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='richieste_community'
    )

    community = models.ForeignKey(
        'Community',
        on_delete=models.CASCADE,
        related_name='richieste_ricevute'
    )

    stato = models.CharField(
        max_length=10,
        choices=STATI_RICHIESTA,
        default='PENDING'
    )

    data_richiesta = models.DateTimeField(
        auto_now_add=True
    )

    # Vincoli di validazione
    def clean(self):
        super().clean()

        if self.utente_id is None or self.community_id is None:
            return

        # L'organizzatore è già membro della propria community
        if self.utente_id == self.community.organizzatore_id:
            raise ValidationError(
                'L’organizzatore non può richiedere di partecipare alla propria community.'
            )

        # Un membro non può richiedere di entrare nuovamente
        if self.community.membri.filter(
            pk=self.utente_id
        ).exists():
            if self.stato == 'PENDING':
                raise ValidationError(
                    'Sei già membro di questa community.'
                )

    def __str__(self):
        return f'{self.utente} - {self.community} ({self.get_stato_display()})'

    class Meta:
        verbose_name_plural = 'Richieste community'

        constraints = [
            models.UniqueConstraint(
                fields=['utente', 'community'],
                name='richiesta_unica_per_utente_community'
            )
        ]

#MODEL EVENTO
class Evento(models.Model):

    community = models.ForeignKey(
        'Community',
        on_delete=models.CASCADE,
        related_name='eventi'
    )

    titolo = models.CharField(
        max_length=100
    )

    descrizione = models.TextField(
        max_length=1000,
        blank=True,
        default=''
    )

    inizio = models.DateTimeField()

    # La data di fine è facoltativa.
    fine = models.DateTimeField(
        null=True,
        blank=True
    )

    luogo = models.CharField(
        max_length=200
    )

    costo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00'))
        ]
    )

    cosa_portare = models.TextField(
        max_length=500,
        blank=True,
        default=''
    )

    def clean(self):

        super().clean()

        # Se è presente una data di fine,
        # deve essere successiva all'inizio.
        if self.inizio is not None and self.fine is not None:

            if self.fine <= self.inizio:
                raise ValidationError({
                    'fine': (
                        'La fine deve essere successiva '
                        'all’inizio dell’evento.'
                    )
                })

        # Non si possono CREARE nuovi eventi
        # con data di inizio già trascorsa.
        if self._state.adding and self.inizio is not None:

            if self.inizio < timezone.now():
                raise ValidationError({
                    'inizio': (
                        'Non puoi creare un evento '
                        'con una data di inizio passata.'
                    )
                })

    def __str__(self):
        return self.titolo

    class Meta:
        verbose_name_plural = 'Eventi'
        ordering = ['inizio', 'id']


    community = models.ForeignKey(
        'Community',
        on_delete=models.CASCADE,
        related_name='eventi'
    )

    titolo = models.CharField(
        max_length=100
    )

    descrizione = models.TextField(
        max_length=1000,
        blank=True,
        default=''
    )

    inizio = models.DateTimeField()

    fine = models.DateTimeField()

    luogo = models.CharField(
        max_length=200
    )

    costo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    cosa_portare = models.TextField(
        max_length=500,
        blank=True,
        default=''
    )

    # Vincoli di validazione
    def clean(self):
        super().clean()

        if self.inizio is not None and self.fine is not None:

            # La fine deve essere successiva all'inizio
            if self.fine <= self.inizio:
                raise ValidationError({
                    'fine': 'La fine dell’evento deve essere successiva all’inizio.'
                })

        # Alla creazione non si possono inserire eventi già iniziati
        if self._state.adding and self.inizio is not None:

            if self.inizio < timezone.now():
                raise ValidationError({
                    'inizio': 'Non puoi creare un evento con una data di inizio passata.'
                })

    def __str__(self):
        return self.titolo

    class Meta:
        verbose_name_plural = 'Eventi'
        ordering = ['inizio', 'id']

#MODEL MESSAGGIO_COMMUNITY
class MessaggioCommunity(models.Model):

    community = models.ForeignKey(
        'Community',
        on_delete=models.CASCADE,
        related_name='messaggi'
    )

    autore = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='messaggi_community'
    )

    testo = models.TextField(
        max_length=2000
    )

    data_ora = models.DateTimeField(
        auto_now_add=True
    )

    # Vincoli di validazione
    def clean(self):
        super().clean()

        # Solo i membri della community possono inviare messaggi
        if self.community_id is not None and self.autore_id is not None:

            if not self.community.membri.filter(
                pk=self.autore_id
            ).exists():
                raise ValidationError(
                    'Solo i membri della community possono inviare messaggi.'
                )

    def __str__(self):
        return f'Messaggio di {self.autore} in {self.community}'

    class Meta:
        verbose_name_plural = 'Messaggi community'
        ordering = ['data_ora', 'id']

#MODEL VALUTAZIONE_COMMUNITY
class ValutazioneCommunity(models.Model):

    utente = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='valutazioni_community'
    )

    community = models.ForeignKey(
        'Community',
        on_delete=models.CASCADE,
        related_name='valutazioni'
    )

    voto = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    data_ora = models.DateTimeField(
        auto_now_add=True
    )

    # Validazione dei vincoli
    def clean(self):
        super().clean()

        if self.utente_id is None or self.community_id is None:
            return

        # L'organizzatore non può valutare la propria community
        if self.utente_id == self.community.organizzatore_id:
            raise ValidationError(
                'Non puoi valutare una community di cui sei organizzatore.'
            )

        # Controlliamo che l'utente sia membro della community
        # soltanto quando crea o modifica una valutazione
        if self._state.adding or self._valutazione_modificata():

            if not self.community.membri.filter(
                pk=self.utente_id
            ).exists():
                raise ValidationError(
                    'Solo i membri della community possono lasciare o modificare una valutazione.'
                )

    # IndicA se la valutazione è stata modificata
    def _valutazione_modificata(self):

        if self.pk is None:
            return True

        precedente = ValutazioneCommunity.objects.filter(
            pk=self.pk
        ).first()

        if precedente is None:
            return True

        return (
            precedente.voto != self.voto
            or precedente.utente_id != self.utente_id
            or precedente.community_id != self.community_id
        )

    def __str__(self):
        return f'{self.utente} - {self.community}: {self.voto}/5'

    class Meta:
        verbose_name_plural = 'Valutazioni community'

        constraints = [
            models.UniqueConstraint(
                fields=['utente', 'community'],
                name='valutazione_unica_per_utente_community'
            )
        ]

# MODEL NOTIFICA 
class Notifica(models.Model):

    TIPI_NOTIFICA = [
        ('MATCH', 'Nuovo match'),
        ('MESSAGGIO_PRIVATO', 'Nuovo messaggio privato'),
        ('MESSAGGIO_COMMUNITY', 'Nuovo messaggio community'),
        ('RICHIESTA_COMMUNITY', 'Nuova richiesta community'),
        ('RICHIESTA_ACCETTATA', 'Richiesta accettata'),
        ('RICHIESTA_RIFIUTATA', 'Richiesta rifiutata'),
        ('NUOVO_EVENTO_COMMUNITY', 'Nuovo evento community'),
        ('EVENTO_MODIFICATO', 'Evento modificato'),
        ('LIKE_RICEVUTO', 'Nuovo Like Ricevuto')
    ]

    destinatario = models.ForeignKey(
        'Profilo',
        on_delete=models.CASCADE,
        related_name='notifiche'
    )

    testo = models.CharField(
        max_length=255
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPI_NOTIFICA
    )

    data_ora = models.DateTimeField(
        auto_now_add=True
    )

    letta = models.BooleanField(
        default=False
    )

    profilo_collegato = models.ForeignKey(
        'Profilo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifiche_collegate'
    )

    community_collegata = models.ForeignKey(
        'Community',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifiche_collegate'
    )

    def __str__(self):
        return f'Notifica per {self.destinatario}: {self.testo}'

    class Meta:
        verbose_name_plural = 'Notifiche'
        ordering = ['-data_ora', '-id']