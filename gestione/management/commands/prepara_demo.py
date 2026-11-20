# permette l'inizializzazione dei dati demo 

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):

    help = (
        "Prepara tutti i dati dimostrativi di FuoriRete: "
        "persone, Community, eventi e relazioni."
    )

    def handle(self, *args, **options):

        if not settings.DEBUG:
            raise CommandError(
                "Il popolamento dimostrativo è consentito "
                "soltanto in ambiente di sviluppo."
            )

        self.stdout.write(
            "\n=================================="
            "\n PREPARAZIONE DEMO FUORIRETE"
            "\n=================================="
        )

        with transaction.atomic():

            self.stdout.write(
                "\n1. Popolamento delle persone..."
            )

            call_command(
                "popola_persone_demo",
                stdout=self.stdout,
                stderr=self.stderr,
            )

            self.stdout.write(
                "\n2. Popolamento delle Community e degli eventi..."
            )

            call_command(
                "popola_community_demo",
                stdout=self.stdout,
                stderr=self.stderr,
            )

            self.stdout.write(
                "\n3. Popolamento delle relazioni..."
            )

            call_command(
                "popola_relazioni_demo",
                stdout=self.stdout,
                stderr=self.stderr,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nDEMO FUORIRETE PREPARATA CON SUCCESSO!"
            )
        )
