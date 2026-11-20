
# Dopo migrate viene eseguito inizializza_interessi sul db appena migrato

from django.apps import AppConfig
from django.db.models.signals import post_migrate

def inizializza_interessi_dopo_migrazioni(sender, using, **kwargs):
    from django.core.management import call_command

    call_command(
        "inizializza_interessi",
        database=using,
        verbosity=0,
    )

class GestioneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gestione"

    def ready(self):
        post_migrate.connect(
            inizializza_interessi_dopo_migrazioni,
            sender=self,
            dispatch_uid="gestione_inizializza_interessi",
        )
