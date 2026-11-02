
from django.db import transaction
from gestione.models import Interesse

# CATALOGO DEGLI INTERESSI

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

# INIZIALIZZAZIONE DATABASE CON GLI INTERESSI

@transaction.atomic
def init_db():

    categorie_create = 0
    sottocategorie_create = 0

    for nome_categoria, sottocategorie in INTERESSI_INIZIALI.items():

        # Creazione della macrocategoria --> il padre = None perchè si trova al primo livello della gerarchia
        categoria, creata = Interesse.objects.get_or_create(
            nome=nome_categoria,
            padre=None
        )

        if creata:
            categorie_create += 1

        # Creazione delle sottocategorie --> ogni sotto categoria come padre la macro-categoria corrispondente
        for nome_sottocategoria in sottocategorie:

            _, creata = Interesse.objects.get_or_create(
                nome=nome_sottocategoria,
                padre=categoria
            )

            if creata:
                sottocategorie_create += 1

    print("Inizializzazione interessi completata!")
    print(f"Macrocategorie create: {categorie_create}")
    print(f"Sottocategorie create: {sottocategorie_create}")
    print("Interessi totali nel database:", Interesse.objects.count())


# ELIMINAZIONE CATALOGO INTERESSI

@transaction.atomic
def erase_db():

    # Individuiamo esattamente le categorie presenti nel catalogo ufficiale
    categorie = Interesse.objects.filter(
        nome__in=INTERESSI_INIZIALI.keys(),
        padre__isnull=True
    )

    # Recuperiamo le relative sottocategorie
    sottocategorie = Interesse.objects.filter(
        padre__in=categorie
    )

    # Prima di procedere, verifichiamo che nessun interesse sia associato a un profilo.
    interessi_catalogo = (
        categorie | sottocategorie
    )

    interessi_in_uso = interessi_catalogo.filter(
        profilo__isnull=False
    ).exists()

    if interessi_in_uso:
        print(
            "Cancellazione annullata: alcuni interessi "
            "sono associati ai profili degli utenti."
        )
        return

    # Il campo padre utilizza PROTECT: eliminiamo prima le sottocategorie.
    numero_sottocategorie = sottocategorie.count()
    sottocategorie.delete()

    # Poi eliminiamo le macrocategorie.
    numero_categorie = categorie.count()
    categorie.delete()

    print("Cancellazione interessi completata!")
    print(f"Macrocategorie eliminate: {numero_categorie}")
    print(f"Sottocategorie eliminate: {numero_sottocategorie}")
