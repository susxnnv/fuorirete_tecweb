
# utile durante lo sviluppo del sito: ho inserito relazioni di prova random per riuscire a testare il funzionamento del sito
# periodicamente eliminavo questi dati inseriti manualmente attraverso questo script 
# scopo: eliminare dati inseriti da browser, mantenere solo i dati dei file popola_persone e popola_community

from datetime import date
from pathlib import Path
from decimal import Decimal
import sqlite3
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.models import Q
from django.utils import timezone

from gestione.models import (
    Profilo,
    Interesse,
    Community,
    Evento,
    Like,
    Dislike,
    MessaggioPrivato,
    MessaggioCommunity,
    RichiestaCommunity,
    ValutazioneCommunity,
    Notifica,
)

from gestione.management.commands.popola_persone_demo import (
    PERSONE,
    normalizza,
    trova_interesse as trova_interesse_persona,
    trova_foto,
    data_nascita_demo,
)

from gestione.management.commands.popola_community_demo import (
    COMMUNITY_DEMO,
    EVENTI_DEMO,
    trova_interesse as trova_interesse_community,
    trova_fotografia,
    data_ora_locale,
)


class Command(BaseCommand):

    help = (
        "Ripristina il dataset demo originale di FuoriRete "
        "con anteprima, backup e controlli."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--applica",
            action="store_true",
            help="Esegue realmente il ripristino.",
        )

        parser.add_argument(
            "--conferma",
            default="",
            help="Frase di conferma per autorizzare la pulizia.",
        )

    def handle(self, *args, **options):

        applica = options["applica"]

        # -----------------------------------------
        # 1. VERIFICA DATABASE
        # -----------------------------------------

        configurazione = settings.DATABASES["default"]

        if configurazione["ENGINE"] != (
            "django.db.backends.sqlite3"
        ):
            raise CommandError(
                "Questo comando supporta soltanto SQLite."
            )

        database = Path(configurazione["NAME"]).resolve()

        if not database.is_file():
            raise CommandError(
                f"Database SQLite non trovato: {database}"
            )

        if settings.DEBUG is False:
            raise CommandError(
                "Ripristino bloccato: DEBUG=False. "
                "Utilizzare esclusivamente un ambiente "
                "locale di sviluppo."
            )

        if applica and options["conferma"] != (
            "RIPRISTINA_DEMO"
        ):
            raise CommandError(
                "Conferma mancante. Per applicare, "
                "usa --applica --conferma RIPRISTINA_DEMO"
            )

        # -----------------------------------------
        # 2. CONTROLLO DATASET
        # -----------------------------------------

        if (
            len(PERSONE) != 25
            or len(COMMUNITY_DEMO) != 15
            or len(EVENTI_DEMO) != 27
        ):
            raise CommandError(
                "Le dimensioni dei dataset originali "
                "non corrispondono a 25/15/27."
            )

        numeri_persone = [
            dati["numero"] for dati in PERSONE
        ]

        numeri_community = [
            dati["numero"] for dati in COMMUNITY_DEMO
        ]

        if sorted(numeri_persone) != list(range(1, 26)):
            raise CommandError(
                "Numerazione persone demo non valida."
            )

        if sorted(numeri_community) != list(range(1, 16)):
            raise CommandError(
                "Numerazione community demo non valida."
            )

        # -----------------------------------------
        # 3. IDENTIFICAZIONE PROFILI
        # -----------------------------------------

        profili = {}

        for dati in PERSONE:

            numero = dati["numero"]
            username = f"demo_{numero:02d}"

            utenti = User.objects.filter(
                username=username
            )

            if utenti.count() != 1:
                raise CommandError(
                    f"Account demo mancante: {username}"
                )

            utente = utenti.get()

            if utente.is_staff or utente.is_superuser:
                raise CommandError(
                    f"{username} è amministratore. "
                    "Operazione bloccata per sicurezza."
                )

            try:
                profilo = utente.profilo
            except Profilo.DoesNotExist:
                raise CommandError(
                    f"Profilo mancante per {username}"
                )

            profili[numero] = profilo

        # -----------------------------------------
        # 4. IDENTIFICAZIONE COMMUNITY
        # -----------------------------------------

        community = {}

        for dati in COMMUNITY_DEMO:

            numero = dati["numero"]

            trovate = Community.objects.filter(
                titolo=dati["titolo"],
                organizzatore=profili[
                    dati["organizzatore"]
                ],
            )

            if trovate.count() != 1:
                raise CommandError(
                    "Community originale assente o ambigua: "
                    f"{dati['titolo']}"
                )

            community[numero] = trovate.get()

        # -----------------------------------------
        # 5. IDENTIFICAZIONE EVENTI
        # -----------------------------------------

        eventi = {}

        for dati in EVENTI_DEMO:

            chiave = (
                dati["comunita"],
                dati["titolo"],
            )

            if chiave in eventi:
                raise CommandError(
                    f"Evento duplicato nel dataset: {chiave}"
                )

            trovati = Evento.objects.filter(
                community=community[dati["comunita"]],
                titolo=dati["titolo"],
            )

            if trovati.count() != 1:
                raise CommandError(
                    "Evento originale assente o ambiguo: "
                    f"{dati['titolo']}"
                )

            eventi[chiave] = trovati.get()

        # -----------------------------------------
        # 6. CONTROLLO INTERESSI
        # -----------------------------------------

        catalogo = list(Interesse.objects.all())

        if not catalogo:
            raise CommandError(
                "Catalogo interessi vuoto."
            )

        interessi_profili = {}

        for dati in PERSONE:

            risultato = []

            for categoria, sottointeresse in dati[
                "interessi"
            ]:

                interesse = trova_interesse_persona(
                    categoria,
                    sottointeresse,
                    catalogo,
                )

                if interesse not in risultato:
                    risultato.append(interesse)

            interessi_profili[dati["numero"]] = risultato

        interessi_community = {}

        for dati in COMMUNITY_DEMO:

            risultato = []

            for categoria, sottointeresse in dati[
                "interessi"
            ]:

                interesse = trova_interesse_community(
                    categoria,
                    sottointeresse,
                )

                if interesse not in risultato:
                    risultato.append(interesse)

            interessi_community[dati["numero"]] = risultato

        # -----------------------------------------
        # 7. VERIFICA IMMAGINI ORIGINALI
        # -----------------------------------------

        cartella_profili = (
            Path(settings.BASE_DIR)
            / "dati_demo"
            / "foto_profili"
        )

        cartella_community = (
            Path(settings.BASE_DIR)
            / "dati_demo"
            / "foto_community"
        )

        if (
            not cartella_profili.is_dir()
            or not cartella_community.is_dir()
        ):
            raise CommandError(
                "Cartelle delle immagini demo mancanti."
            )

        foto_profili = {}
        foto_community = {}

        for dati in PERSONE:

            numero = dati["numero"]

            percorso = trova_foto(
                cartella_profili,
                numero,
            )

            nome_file = (
                f"profili/demo_{numero:02d}"
                f"{percorso.suffix.lower()}"
            )

            profilo = profili[numero]

            if not profilo.foto.storage.exists(nome_file):
                raise CommandError(
                    "Immagine originale mancante nel "
                    f"media storage: {nome_file}"
                )

            foto_profili[numero] = nome_file

        for dati in COMMUNITY_DEMO:

            numero = dati["numero"]

            percorso = trova_fotografia(
                cartella_community,
                numero,
            )

            nome_file = (
                f"community/demo_community_{numero:02d}"
                f"{percorso.suffix.lower()}"
            )

            obj = community[numero]

            if not obj.immagine.storage.exists(nome_file):
                raise CommandError(
                    "Immagine originale mancante nel "
                    f"media storage: {nome_file}"
                )

            foto_community[numero] = nome_file

        # -----------------------------------------
        # 8. CALCOLO RECORD EXTRA
        # -----------------------------------------

        id_profili = [
            profilo.pk for profilo in profili.values()
        ]

        id_community = [
            obj.pk for obj in community.values()
        ]

        id_eventi = [
            obj.pk for obj in eventi.values()
        ]

        utenti_da_eliminare = User.objects.exclude(
            username__in=[
                f"demo_{n:02d}"
                for n in range(1, 26)
            ]
        ).exclude(
            Q(is_staff=True) | Q(is_superuser=True)
        )

        community_da_eliminare = (
            Community.objects.exclude(
                pk__in=id_community
            )
        )

        eventi_da_eliminare = Evento.objects.exclude(
            pk__in=id_eventi
        )

        interazioni = [
            ("Like", Like),
            ("Dislike", Dislike),
            ("Messaggi privati", MessaggioPrivato),
            ("Messaggi community", MessaggioCommunity),
            ("Richieste community", RichiestaCommunity),
            ("Valutazioni community", ValutazioneCommunity),
            ("Notifiche", Notifica),
        ]

        # -----------------------------------------
        # 9. ANTEPRIMA
        # -----------------------------------------

        self.stdout.write(
            "\n================================="
            "\n RIPRISTINO DATASET FUORIRETE"
            "\n================================="
        )

        self.stdout.write(
            "\nDATI ORIGINALI IDENTIFICATI:"
        )

        self.stdout.write(
            f"Profili demo: {len(profili)}"
        )

        self.stdout.write(
            f"Community demo: {len(community)}"
        )

        self.stdout.write(
            f"Eventi demo: {len(eventi)}"
        )

        self.stdout.write(
            "\nDATI DA ELIMINARE:"
        )

        self.stdout.write(
            "Utenti non demo e non amministrativi: "
            f"{utenti_da_eliminare.count()}"
        )

        self.stdout.write(
            "Community non demo: "
            f"{community_da_eliminare.count()}"
        )

        self.stdout.write(
            "Eventi non demo: "
            f"{eventi_da_eliminare.count()}"
        )

        for etichetta, modello in interazioni:
            self.stdout.write(
                f"{etichetta}: {modello.objects.count()}"
            )

        amministratori = User.objects.filter(
            Q(is_staff=True) | Q(is_superuser=True)
        )

        self.stdout.write(
            "\nACCOUNT AMMINISTRATIVI PROTETTI:"
        )

        for utente in amministratori:
            self.stdout.write(
                f"- {utente.username}"
            )

        if not applica:

            self.stdout.write(
                self.style.SUCCESS(
                    "\nANTEPRIMA COMPLETATA."
                    "\nNessun dato modificato."
                )
            )

            return

        # -----------------------------------------
        # 10. BACKUP SQLITE OBBLIGATORIO
        # -----------------------------------------

        cartella_backup = (
            Path(settings.BASE_DIR)
            / "backup_database"
        )

        cartella_backup.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = timezone.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        percorso_backup = (
            cartella_backup
            / f"fuorirete_prima_pulizia_{timestamp}.sqlite3"
        )

        try:

            with sqlite3.connect(
                str(database)
            ) as origine_db:

                with sqlite3.connect(
                    str(percorso_backup)
                ) as backup_db:

                    origine_db.backup(backup_db)

        except sqlite3.Error as errore:

            raise CommandError(
                f"Backup SQLite fallito: {errore}"
            )

        if (
            not percorso_backup.exists()
            or percorso_backup.stat().st_size == 0
        ):
            raise CommandError(
                "Backup non valido. Pulizia annullata."
            )

        with sqlite3.connect(
            str(percorso_backup)
        ) as verifica:

            controllo = verifica.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

        if controllo != "ok":
            raise CommandError(
                "Backup non integro. Pulizia annullata."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nBACKUP CREATO: {percorso_backup}"
            )
        )

        # -----------------------------------------
        # 11. RIPRISTINO TRANSAZIONALE
        # -----------------------------------------

        try:

            with transaction.atomic():

                # Eliminiamo le interazioni casuali.
                for _, modello in interazioni:
                    modello.objects.all().delete()

                # Eliminiamo gli eventi extra.
                Evento.objects.exclude(
                    pk__in=id_eventi
                ).delete()

                # Eliminiamo le community extra.
                Community.objects.exclude(
                    pk__in=id_community
                ).delete()

                # Eliminiamo gli account di test
                # che non appartengono al dataset.
                User.objects.exclude(
                    username__in=[
                        f"demo_{n:02d}"
                        for n in range(1, 26)
                    ]
                ).exclude(
                    Q(is_staff=True)
                    | Q(is_superuser=True)
                ).delete()

                # Ripristino dei profili originali.
                for dati in PERSONE:

                    numero = dati["numero"]
                    profilo = profili[numero]

                    profilo.nome = dati["nome"]

                    profilo.data_nascita = (
                        data_nascita_demo(
                            dati["eta"]
                        )
                    )

                    profilo.genere = dati["genere"]
                    profilo.citta = dati["citta"]

                    profilo.occupazione = (
                        dati["occupazione"]
                    )

                    profilo.lingue = list(
                        dati["lingue"]
                    )

                    profilo.cosa_cerca = list(
                        dati["cerca"]
                    )

                    profilo.descrizione = (
                        dati["descrizione"]
                    )

                    profilo.foto = (
                        foto_profili[numero]
                    )

                    profilo.full_clean()
                    profilo.save()

                    profilo.interessi.set(
                        interessi_profili[numero]
                    )

                # Ripristino community originali.
                for dati in COMMUNITY_DEMO:

                    numero = dati["numero"]
                    obj = community[numero]

                    obj.titolo = dati["titolo"]
                    obj.descrizione = dati["descrizione"]

                    obj.organizzatore = profili[
                        dati["organizzatore"]
                    ]

                    obj.citta = dati["citta"]
                    obj.immagine = foto_community[numero]

                    obj.full_clean()
                    obj.save()

                    obj.interessi.set(
                        interessi_community[numero]
                    )

                    obj.membri.set([
                        profili[n]
                        for n in dati["membri"]
                    ])

                # Ripristino dei 27 eventi.
                for dati in EVENTI_DEMO:

                    chiave = (
                        dati["comunita"],
                        dati["titolo"],
                    )

                    obj = eventi[chiave]

                    obj.community = community[
                        dati["comunita"]
                    ]

                    obj.titolo = dati["titolo"]
                    obj.descrizione = dati["descrizione"]

                    obj.inizio = data_ora_locale(
                        dati["inizio"]
                    )

                    obj.fine = data_ora_locale(
                        dati["fine"]
                    )

                    obj.luogo = dati["luogo"]

                    obj.costo = Decimal(
                        dati["costo"]
                    )

                    obj.cosa_portare = (
                        dati["cosa_portare"]
                    )

                    # Ripristina anche gli eventi storici del dataset, mantenendo i controlli sui campi e sui vincoli.
                    obj.clean_fields()
                    obj.validate_unique()
                    obj.validate_constraints()
                    obj.save()

                # ---------------------------------
                # RIPRISTINO RELAZIONI DEMO
                # ---------------------------------

                call_command(
                    "popola_relazioni_demo",
                    stdout=self.stdout,
                    stderr=self.stderr,
                )

                
                # ---------------------------------
                # 12. VERIFICA FINALE
                # ---------------------------------

                if Community.objects.count() != 15:
                    raise CommandError(
                        "Controllo fallito: "
                        "numero community inatteso."
                    )

                if Evento.objects.count() != 27:
                    raise CommandError(
                        "Controllo fallito: "
                        "numero eventi inatteso."
                    )

                # Verifica che lo scenario dimostrativo sia stato ricostruito correttamente.

                if Like.objects.count() != 6:
                    raise CommandError(
                        "Controllo fallito: numero Like demo inatteso."
                    )

                if Dislike.objects.count() != 1:
                    raise CommandError(
                        "Controllo fallito: numero Dislike demo inatteso."
                    )

                if MessaggioPrivato.objects.count() != 5:
                    raise CommandError(
                        "Controllo fallito: messaggi privati demo mancanti."
                    )

                if MessaggioCommunity.objects.count() != 4:
                    raise CommandError(
                        "Controllo fallito: messaggi Community demo mancanti."
                    )

                if RichiestaCommunity.objects.count() != 2:
                    raise CommandError(
                        "Controllo fallito: richieste Community demo mancanti."
                    )

                if ValutazioneCommunity.objects.count() != 1:
                    raise CommandError(
                        "Controllo fallito: valutazione Community demo mancante."
                    )

                if Notifica.objects.count() != 8:
                    raise CommandError(
                        "Controllo fallito: notifiche demo mancanti."
                    )

                for dati in PERSONE:

                    numero = dati["numero"]

                    if not profili[numero].interessi.exists():
                        raise CommandError(
                            "Profilo senza interessi: "
                            f"demo_{numero:02d}"
                        )

                for dati in COMMUNITY_DEMO:

                    numero = dati["numero"]
                    obj = community[numero]

                    if obj.organizzatore_id not in (
                        obj.membri.values_list(
                            "pk",
                            flat=True,
                        )
                    ):
                        raise CommandError(
                            "Organizzatore non membro: "
                            f"{obj.titolo}"
                        )

        except Exception as errore:

            raise CommandError(
                "RIPRISTINO NON COMPLETATO. "
                "Le modifiche al database sono "
                "state annullate dalla transazione. "
                f"Dettaglio: {errore}"
            ) from errore

        self.stdout.write(
            self.style.SUCCESS(
                "\nRIPRISTINO COMPLETATO!"
            )
        )

        self.stdout.write(
            "25 profili demo conservati e ripristinati."
        )

        self.stdout.write(
            "15 community demo ripristinate."
        )

        self.stdout.write(
            "27 eventi demo ripristinati."
        )

        self.stdout.write(
            "Interazioni di test eliminate e "
            "relazoini dimostrative ripristinate"
        )

        self.stdout.write(
            "Account amministrativi conservati."
        )

        self.stdout.write(
            f"\nBackup disponibile in: {percorso_backup}"
        )
