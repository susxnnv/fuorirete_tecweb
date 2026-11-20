
from django.core.management.base import BaseCommand
from django.db import transaction

from gestione.models import Interesse


# Catalogo ufficiale degli interessi di FuoriRete.
# Le categorie vengono create una sola volta e non dipendono dai dati dimostrativi

INTERESSI_INIZIALI = {

    "MUSICA": [
        "Rock",
        "Pop",
        "Rap e hip-hop",
        "Indie",
        "Elettronica",
        "Jazz",
    ],

    "CINEMA": [
        "Serie TV",
        "Horror",
        "Commedia",
        "Fantascienza",
        "Anime",
        "Film d'azione",
        "Documentari",
    ],

    "ARTE E CREATIVITÀ": [
        "DIY e artigianato",
        "Pittura",
        "Fotografia",
        "Scrittura creativa",
        "Club del libro",
    ],

    "SPORT": [
        "Calcio",
        "Basket",
        "Pallavolo",
        "Tennis e padel",
        "Sport acquatici",
        "Atletica",
    ],

    "FITNESS E BENESSERE": [
        "Palestra e pesi",
        "Yoga e pilates",
        "Meditazione e mindfulness",
        "SPA",
    ],

    "NATURA": [
        "Trekking",
        "Campeggio",
        "Montagna",
        "Mare",
        "Birdwatching",
        "Giardinaggio",
    ],

    "VIAGGI": [
        "Avventura",
        "On the road",
        "Weekend e gite fuori porta",
        "Cultura",
        "Scambio linguistico",
    ],

    "CIBO E GASTRONOMIA": [
        "Cucina italiana",
        "Cucine dal mondo",
        "Pasticceria e dolci",
        "Cucinare in compagnia",
        "Cucina vegana",
    ],

    "GIOCHI": [
        "Videogiochi",
        "Escape room",
        "Giochi di carte",
        "Giochi da tavolo",
    ],

    "SCIENZA E CONOSCENZA": [
        "Astronomia",
        "Biologia e natura",
        "Psicologia",
        "Storia",
        "Filosofia",
        "Informatica",
    ],

    "MODA E STILE": [
        "Streetwear",
        "Thrift shop e vintage",
        "Beauty e skincare",
        "Sneakers",
    ],

    "EVENTI": [
        "Teatro e spettacoli",
        "Cinema",
        "Concerti",
        "Festival",
    ],

    "SOCIALITÀ": [
        "Mangiare fuori",
        "Eventi in città",
        "Caffè",
        "Aperitivi",
        "Discoteca",
        "Passeggiate",
    ],

    "VOLONTARIATO": [
        "Tutela dell'ambiente",
        "Diritti LGBT",
        "Diritti per gli animali",
    ],

    "ANIMALI": [
        "Cani",
        "Gatti",
        "Fattoria",
        "Animali esotici",
    ],

    "MOTORI": [
        "Macchine e velocità",
        "Formula 1",
        "Motociclismo",
        "Macchine d'epoca",
    ],
}


class Command(BaseCommand):

    help = "Inizializza il catalogo ufficiale degli interessi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Database da inizializzare.",
        )

    def handle(self, *args, **options):

        database = options["database"]

        categorie_create = 0
        sottointeressi_creati = 0

        with transaction.atomic(using=database):

            for nome, sottointeressi in INTERESSI_INIZIALI.items():

                categoria, creata = (
                    Interesse.objects.using(database).get_or_create(
                        nome=nome,
                        padre=None,
                    )
                )

                if creata:
                    categorie_create += 1

                for nome_sottointeresse in sottointeressi:

                    _, creato = (
                        Interesse.objects.using(database).get_or_create(
                            nome=nome_sottointeresse,
                            padre=categoria,
                        )
                    )

                    if creato:
                        sottointeressi_creati += 1

        if options["verbosity"] > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Catalogo interessi inizializzato.\n"
                    f"Nuove categorie: {categorie_create}\n"
                    f"Nuovi sottointeressi: {sottointeressi_creati}"
                )
            )
