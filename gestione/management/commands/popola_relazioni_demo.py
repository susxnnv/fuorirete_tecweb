
# contiene l'inizializzazione degli interessi demo 

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestione.models import (
    Profilo,
    Community,
    Like,
    Dislike,
    MessaggioPrivato,
    MessaggioCommunity,
    RichiestaCommunity,
    ValutazioneCommunity,
    Notifica,
)


class Command(BaseCommand):

    help = (
        "Crea le relazioni dimostrative di FuoriRete: "
        "Like, Match, conversazioni, richieste e notifiche."
    )

    def handle(self, *args, **options):

        if not settings.DEBUG:
            raise CommandError(
                "Le relazioni demo possono essere create "
                "soltanto in ambiente di sviluppo."
            )

        # ------------------------------------------
        # RECUPERO PROFILI
        # ------------------------------------------

        numeri = (2, 3, 4, 5, 6, 7, 11)
        profili = {}

        for numero in numeri:

            username = f"demo_{numero:02d}"

            try:
                profili[numero] = Profilo.objects.get(
                    user__username=username
                )

            except Profilo.DoesNotExist as errore:
                raise CommandError(
                    f"Profilo {username} non trovato. "
                    "Esegui prima il popolamento delle persone."
                ) from errore

        # ------------------------------------------
        # RECUPERO COMMUNITY
        # ------------------------------------------

        try:
            club = Community.objects.get(
                titolo="Club del libro 📚"
            )

            padel = Community.objects.get(
                titolo="Padel Social Club 🎾"
            )

            study = Community.objects.get(
                titolo="Study Together ☕"
            )

            f1 = Community.objects.get(
                titolo="F1 Watching 🏎️"
            )

        except (
            Community.DoesNotExist,
            Community.MultipleObjectsReturned,
        ) as errore:

            raise CommandError(
                "Community demo mancanti o ambigue. "
                "Esegui prima il popolamento delle Community."
            ) from errore

        # ------------------------------------------
        # ASSEGNAZIONE PROFILI
        # ------------------------------------------

        sara = profili[4]
        marco = profili[2]
        alice = profili[5]
        gaia = profili[6]
        alessandro = profili[7]

        persona_richiesta = profili[3]
        persona_like = profili[11]

        # ------------------------------------------
        # CONTROLLI PRELIMINARI
        # ------------------------------------------

        if club.organizzatore_id != sara.pk:
            raise CommandError(
                "Sara non è l'organizzatrice del Club del libro."
            )

        if not all([
            padel.membri.filter(pk=sara.pk).exists(),
            study.membri.filter(pk=sara.pk).exists(),
            club.membri.filter(pk=sara.pk).exists(),
        ]):
            raise CommandError(
                "Le appartenenze iniziali di Sara "
                "non corrispondono al dataset."
            )

        if f1.membri.filter(pk=sara.pk).exists():
            raise CommandError(
                "Sara è già membro di F1 Watching: "
                "non può avere una richiesta pendente."
            )

        if club.membri.filter(
            pk=persona_richiesta.pk
        ).exists():
            raise CommandError(
                "La richiedente è già membro del Club del libro."
            )

        # ------------------------------------------
        # CREAZIONE RELAZIONI
        # ------------------------------------------

        with transaction.atomic():

            # MATCH RECIPROCI

            for altro in (marco, alice):

                for mittente, destinatario in (
                    (sara, altro),
                    (altro, sara),
                ):

                    if Dislike.objects.filter(
                        mittente=mittente,
                        destinatario=destinatario,
                    ).exists():

                        raise CommandError(
                            "Un Dislike esistente impedisce "
                            "la creazione del Match demo."
                        )

                    Like.objects.get_or_create(
                        mittente=mittente,
                        destinatario=destinatario,
                    )

            # LIKE RICEVUTO NON RICAMBIATO

            if Dislike.objects.filter(
                mittente=persona_like,
                destinatario=sara,
            ).exists():

                raise CommandError(
                    "Dislike incompatibile con il Like ricevuto."
                )

            if Like.objects.filter(
                mittente=sara,
                destinatario=persona_like,
            ).exists():

                raise CommandError(
                    "Il Like ricevuto è già reciproco."
                )

            Like.objects.get_or_create(
                mittente=persona_like,
                destinatario=sara,
            )

            # LIKE ESPRESSO DA SARA

            if Dislike.objects.filter(
                mittente=sara,
                destinatario=gaia,
            ).exists():

                raise CommandError(
                    "Dislike incompatibile con il Like in uscita."
                )

            Like.objects.get_or_create(
                mittente=sara,
                destinatario=gaia,
            )

            # DISLIKE ESPRESSO DA SARA

            if Like.objects.filter(
                mittente=sara,
                destinatario=alessandro,
            ).exists():

                raise CommandError(
                    "Like incompatibile con il Dislike demo."
                )

            Dislike.objects.get_or_create(
                mittente=sara,
                destinatario=alessandro,
            )

            # --------------------------------------
            # MESSAGGI PRIVATI
            # --------------------------------------

            conversazioni = (
                (
                    marco,
                    sara,
                    "Ciao Sara! Ci vediamo per studiare domani?"
                ),
                (
                    sara,
                    marco,
                    "Volentieri! Possiamo trovarci "
                    "in biblioteca alle 15."
                ),
                (
                    marco,
                    sara,
                    "Perfetto, porto anche gli appunti!"
                ),
                (
                    alice,
                    sara,
                    "Ehi Sara! Hai ascoltato il nuovo album?"
                ),
                (
                    sara,
                    alice,
                    "Non ancora! Me lo consigli?"
                ),
            )

            for mittente, destinatario, testo in conversazioni:

                MessaggioPrivato.objects.get_or_create(
                    mittente=mittente,
                    destinatario=destinatario,
                    testo=testo,
                )

            # --------------------------------------
            # MESSAGGI COMMUNITY
            # --------------------------------------

            messaggi_gruppo = (
                (
                    club,
                    sara,
                    "Benvenuti nel Club del libro! "
                    "Quale titolo scegliamo?"
                ),
                (
                    club,
                    alice,
                    "Io propongo un romanzo breve, "
                    "così possiamo discuterne insieme!"
                ),
                (
                    study,
                    marco,
                    "Qualcuno viene a studiare "
                    "in biblioteca venerdì?"
                ),
                (
                    study,
                    sara,
                    "Io ci sono! Ci vediamo nel pomeriggio."
                ),
            )

            for gruppo, autore, testo in messaggi_gruppo:

                if not gruppo.membri.filter(
                    pk=autore.pk
                ).exists():

                    raise CommandError(
                        f"{autore.nome} non è membro "
                        f"di {gruppo.titolo}."
                    )

                MessaggioCommunity.objects.get_or_create(
                    community=gruppo,
                    autore=autore,
                    testo=testo,
                )

            # --------------------------------------
            # RICHIESTE COMMUNITY
            # --------------------------------------

            RichiestaCommunity.objects.get_or_create(
                utente=persona_richiesta,
                community=club,
                defaults={
                    "stato": "PENDING",
                },
            )

            RichiestaCommunity.objects.get_or_create(
                utente=sara,
                community=f1,
                defaults={
                    "stato": "PENDING",
                },
            )

            # --------------------------------------
            # VALUTAZIONI
            # --------------------------------------

            ValutazioneCommunity.objects.get_or_create(
                utente=sara,
                community=padel,
                defaults={
                    "voto": 5,
                },
            )

            # --------------------------------------
            # NOTIFICHE
            # --------------------------------------

            notifiche = (
                (
                    sara,
                    "MATCH",
                    "Hai un nuovo Match con Marco!",
                    marco,
                    None,
                ),
                (
                    sara,
                    "MATCH",
                    "Hai un nuovo Match con Alice!",
                    alice,
                    None,
                ),
                (
                    sara,
                    "LIKE_RICEVUTO",
                    "Hai ricevuto un Like!",
                    persona_like,
                    None,
                ),
                (
                    sara,
                    "MESSAGGIO_PRIVATO",
                    "Marco ti ha inviato un nuovo messaggio.",
                    marco,
                    None,
                ),
                (
                    sara,
                    "MESSAGGIO_PRIVATO",
                    "Alice ti ha inviato un nuovo messaggio.",
                    alice,
                    None,
                ),
                (
                    sara,
                    "MESSAGGIO_COMMUNITY",
                    "Nuovo messaggio nel Club del libro.",
                    None,
                    club,
                ),
                (
                    sara,
                    "RICHIESTA_COMMUNITY",
                    "Anna ha richiesto di partecipare "
                    "al Club del libro.",
                    persona_richiesta,
                    club,
                ),
                (
                    f1.organizzatore,
                    "RICHIESTA_COMMUNITY",
                    "Sara ha richiesto di partecipare "
                    "a F1 Watching.",
                    sara,
                    f1,
                ),
            )

            for destinatario, tipo, testo, profilo, gruppo in notifiche:

                Notifica.objects.get_or_create(
                    destinatario=destinatario,
                    tipo=tipo,
                    testo=testo,
                    profilo_collegato=profilo,
                    community_collegata=gruppo,
                    defaults={
                        "letta": False,
                    },
                )

        # ------------------------------------------
        # RIEPILOGO
        # ------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "\nRELAZIONI DIMOSTRATIVE CREATE!"
            )
        )

        self.stdout.write(
            "Profilo principale: demo_04 (Sara)"
        )

        self.stdout.write(
            "2 Match, 5 messaggi privati e 1 Like ricevuto."
        )

        self.stdout.write(
            "4 messaggi Community, 2 richieste "
            "e 1 valutazione."
        )

        self.stdout.write(
            "8 notifiche dimostrative."
        )
