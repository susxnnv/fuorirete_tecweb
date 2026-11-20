# script che popola il sito di dati demo, per permettere di avere già qualcosa nel db al momento dell'esposizione

from datetime import date
from pathlib import Path
import re
import unicodedata

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestione.models import (
    Profilo, Interesse, Community, Like, Dislike,
    MessaggioPrivato, MessaggioCommunity,
    RichiestaCommunity, ValutazioneCommunity, Notifica,
)


# ==================================================
# CONFIGURAZIONE
# ==================================================

# pww usata da tutti gli utenti
PASSWORD_DEMO = "FuoriReteDemo2026!"

# definizione di un profilo con i suoi dati
def persona(numero, nome, eta, genere, citta, occupazione, lingue, cerca, interessi, descrizione):
    return {
        "numero": numero,
        "nome": nome,
        "eta": eta,
        "genere": genere,
        "citta": citta,
        "occupazione": occupazione,
        "lingue": lingue,
        "cerca": cerca,
        "interessi": interessi,
        "descrizione": descrizione,
    }


# ==================================================
# PERSONE
# ==================================================

PERSONE = [

    # 01 - ELENA
    persona(
        1, "Elena", 21, "DONNA", "Milano", "STUDENTE",
        ["Italiano", "Inglese", "Portoghese"],
        ["COINQUILINO", "AMICIZIE"],
        [
            ("VIAGGI", "Scambio linguistico"),
            ("VOLONTARIATO", "Diritti LGBT"),
            ("ANIMALI", "Cani"),
            ("EVENTI", "Concerti"),
        ],
        "Ciaoo! Sono Elena, studio Economia a Milano e cerco "
        "coinquilini 🏡💌 Mi piacerebbe trovare persone con cui "
        "non condividere solo casa, ma anche serate, concerti "
        "e nuove esperienze in città. Bonus se avete voglia "
        "di organizzare qualche viaggio insieme! ✈️"
    ),

    # 02 - MARCO
    persona(
        2, "Marco", 18, "UOMO", "Modena",
        "STUDENTE_LAVORATORE",
        ["Italiano"],
        ["AMICIZIE", "COMPAGNO_STUDIO"],
        [
            ("MUSICA", "Rap e hip-hop"),
            ("CINEMA", "Anime"),
            ("SPORT", "Calcio"),
            ("SCIENZA E CONOSCENZA", "Informatica"),
        ],
        "Oscillo tra una canzone di Tony Boy e le vibes de "
        "La città incantata. Maratona di anime o partita "
        "della Juve insieme? 🎧⚽ Cerco gente con cui studiare, "
        "uscire e condividere qualche nuova playlist."
    ),

    # 03 - ANNA
    persona(
        3, "Anna", 20, "DONNA", "Parma", "STUDENTE",
        ["Italiano", "Portoghese"],
        ["AMICIZIE", "COMPAGNO_STUDIO"],
        [
            ("CINEMA", None),
            ("SPORT", "Pallavolo"),
            ("VIAGGI", None),
            ("CIBO E GASTRONOMIA", None),
        ],
        "Studio a Parma e cerco nuove amicizie con cui fare "
        "un po' di tutto: una partita a pallavolo, un cinema "
        "improvvisato o una gita fuori porta 🏐✈️ Sempre "
        "disponibile anche per una pausa studio, soprattutto "
        "se prevede qualcosa di buono da mangiare!"
    ),

    # 04 - SARA
    persona(
        4, "Sara", 21, "DONNA", "Modena",
        "STUDENTE_LAVORATORE",
        ["Italiano", "Spagnolo"],
        ["AMICIZIE", "COMPAGNO_STUDIO"],
        [
            ("ARTE E CREATIVITÀ", "Club del libro"),
            ("FITNESS E BENESSERE", "Yoga e pilates"),
            ("GIOCHI", None),
            ("SOCIALITÀ", None),
        ],
        "Tra università e lavoro cerco sempre di ritagliarmi "
        "del tempo per le cose che mi piacciono 📚 Pilates, "
        "libri, giochi da tavolo e chiacchiere infinite "
        "davanti a un caffè. Cerco nuove amicizie e qualcuno "
        "con cui rendere le sessioni di studio un po' meno tragiche!"
    ),

    # 05 - ALICE
    persona(
        5, "Alice", 22, "DONNA", "Modena",
        "STUDENTE_LAVORATORE",
        ["Italiano"],
        ["COMPAGNO_STUDIO", "AMICIZIE"],
        [
            ("MUSICA", "Indie"),
            ("VIAGGI", None),
            ("SCIENZA E CONOSCENZA", "Biologia e natura"),
            ("ANIMALI", "Cani"),
            ("ANIMALI", "Gatti"),
        ],
        "Tra studio, lavoro e playlist indie, cerco sempre "
        "una scusa per organizzare qualcosa 🌿 Mi piacciono "
        "la biologia, gli animali e i viaggi, soprattutto "
        "quelli decisi all'ultimo minuto. Se hai un cane "
        "o un gatto, abbiamo già un argomento di "
        "conversazione assicurato 🐈"
    ),

    # 06 - GAIA
    persona(
        6, "Gaia", 23, "DONNA", "Modena",
        "STUDENTE_LAVORATORE",
        ["Italiano", "Arabo"],
        ["COMPAGNO_STUDIO", "COINQUILINO"],
        [
            ("SPORT", "Tennis e padel"),
            ("VIAGGI", None),
            ("VOLONTARIATO", "Diritti per gli animali"),
            ("ANIMALI", "Fattoria"),
        ],
        "Tra studio e lavoro passo un sacco di tempo sui "
        "campi da padel, ma dall'altra parte del bancone 🎾 "
        "Nel tempo libero amo viaggiare e stare a contatto "
        "con gli animali, soprattutto le mie vacche🐮 "
        "Cerco qualcuno con cui studiare e magari anche "
        "una persona con cui condividere casa!"
    ),

    # 07 - ALESSANDRO
    persona(
        7, "Alessandro", 23, "UOMO", "Parma",
        "LAVORATORE",
        ["Italiano", "Inglese", "Spagnolo", "Francese"],
        ["AMICIZIE"],
        [
            ("CIBO E GASTRONOMIA", "Cucinare in compagnia"),
            ("MODA E STILE", "Streetwear"),
            ("SOCIALITÀ", None),
        ],
        "Mi piace cucinare, soprattutto quando c'è qualcuno "
        "con cui condividere il risultato 🍝 Appassionato "
        "di streetwear, buona compagnia e serate organizzate "
        "senza troppi programmi. Cerco nuove amicizie a Parma, "
        "magari iniziando da una cena fatta in casa!"
    ),

    # 08 - GIORGIA
    persona(
        8, "Giorgia", 24, "DONNA", "Roma", "LAVORATORE",
        ["Italiano", "Inglese", "Russo"],
        ["AMICIZIE", "COINQUILINO"],
        [
            ("MUSICA", "Pop"),
            ("CIBO E GASTRONOMIA", None),
            ("EVENTI", None),
            ("SOCIALITÀ", None),
        ],
        "A Roma da un po', ma ho ancora mille posti da "
        "scoprire! 🎀 Amo la musica pop, provare ristoranti "
        "nuovi e organizzare uscite con gli amici. Cerco "
        "persone con cui esplorare la città e magari anche "
        "qualcuno con cui condividere appartamento."
    ),

    # 09 - ELENA
    persona(
        9, "Elena", 25, "DONNA", "Parma", "LAVORATORE",
        ["Italiano", "Giapponese"],
        ["AMICIZIE"],
        [
            ("ARTE E CREATIVITÀ", "DIY e artigianato"),
            ("SPORT", None),
            ("ANIMALI", "Cani"),
        ],
        "Nel tempo libero mi piace creare cose con le mani, "
        "sperimentare piccoli progetti DIY e passare tempo "
        "all'aperto 🎨🐶 Cerco nuove amicizie a Parma per "
        "fare sport, passeggiare o semplicemente prendere "
        "un caffè e chiacchierare."
    ),

    # 10 - MICHELE
    persona(
        10, "Michele", 24, "UOMO", "Milano",
        "STUDENTE_LAVORATORE",
        ["Italiano", "Inglese", "Arabo"],
        ["AMICIZIE", "COINQUILINO"],
        [
            ("MUSICA", "Rap e hip-hop"),
            ("VIAGGI", "Scambio linguistico"),
            ("SCIENZA E CONOSCENZA", "Storia"),
            ("MODA E STILE", "Streetwear"),
        ],
        "Hip hop nelle cuffie, sneakers ai piedi e sempre "
        "voglia di partire per qualche posto nuovo 🎧 "
        "Mi piacciono lo streetwear, la storia e conoscere "
        "persone di culture diverse. Cerco nuove amicizie "
        "a Milano e magari qualcuno con cui condividere casa."
    ),

    # 11 - CRISTIAN
    persona(
        11, "Cristian", 25, "UOMO", "Modena", "STUDENTE",
        ["Italiano", "Inglese", "Giapponese"],
        ["AMICIZIE"],
        [
            ("CINEMA", None),
            ("GIOCHI", "Videogiochi"),
            ("GIOCHI", "Giochi da tavolo"),
            ("SCIENZA E CONOSCENZA", "Informatica"),
            ("CIBO E GASTRONOMIA", "Cucina vegana"),
        ],
        "Appassionato di informatica, videogiochi e cinema 🎮 "
        "Se proponi una serata giochi da tavolo, difficilmente "
        "dico di no. Mi piace anche sperimentare ricette "
        "vegane, con risultati non sempre garantiti. "
        "Cerco gente con cui condividere queste passioni!"
    ),

    # 12 - VALERIO
    persona(
        12, "Valerio", 23, "NON_BINARIO", "Roma", "STUDENTE",
        ["Italiano", "Tedesco"],
        ["COINQUILINO", "COMPAGNO_STUDIO", "AMICIZIE"],
        [
            ("ARTE E CREATIVITÀ", "Scrittura creativa"),
            ("SCIENZA E CONOSCENZA", "Filosofia"),
            ("EVENTI", "Teatro e spettacoli"),
            ("MOTORI", "Macchine e velocità"),
        ],
        "Mi piace scrivere, andare a teatro e perdermi in "
        "discussioni filosofiche che durano più del previsto 📖 "
        "Tra una passione per i motori e un'idea per un nuovo "
        "romanzo, cerco persone con cui studiare, uscire e "
        "magari condividere un appartamento a Roma."
    ),

    # 13 - SOFIA
    persona(
        13, "Sofia", 23, "DONNA", "Milano",
        "STUDENTE_LAVORATORE",
        ["Italiano"],
        ["AMICIZIE", "COINQUILINO"],
        [
            ("CINEMA", "Horror"),
            ("ARTE E CREATIVITÀ", "Fotografia"),
            ("SPORT", "Pallavolo"),
            ("SOCIALITÀ", None),
        ],
        "Fotografia, film horror e pallavolo sono le mie tre "
        "grandi passioni 📸🖤 Mi piace uscire, conoscere "
        "persone nuove e trovare posti carini in città. "
        "Cerco amicizie a Milano e, perché no, anche "
        "coinquilini con cui guardare film horror senza "
        "doverli vedere da sola!"
    ),

    # 14 - SIMONE
    persona(
        14, "Simone", 29, "UOMO", "Modena", "LAVORATORE",
        ["Italiano", "Inglese", "Portoghese", "Tedesco"],
        ["COINQUILINO"],
        [
            ("MUSICA", None),
            ("FITNESS E BENESSERE", "Palestra e pesi"),
            ("NATURA", "Campeggio"),
            ("EVENTI", None),
        ],
        "Lavoro a Modena e cerco una persona con cui "
        "condividere appartamento 🏡 Nel tempo libero "
        "vado in palestra, produco musica e appena posso "
        "scappo in montagna per un weekend in campeggio. "
        "Mi piacerebbe trovare coinquilini tranquilli, "
        "ma anche disponibili a organizzare qualcosa insieme."
    ),

    # 15 - ALESSIA
    persona(
        15, "Alessia", 27, "DONNA", "Parma", "LAVORATORE",
        ["Italiano", "Inglese", "Spagnolo", "Tedesco"],
        ["AMICIZIE"],
        [
            ("VIAGGI", "Cultura"),
            ("VIAGGI", "Weekend e gite fuori porta"),
            ("MODA E STILE", "Beauty e skincare"),
            ("SOCIALITÀ", "Aperitivi"),
        ],
        "Sempre pronta a prenotare un weekend fuori, scoprire "
        "un posto nuovo o organizzare un aperitivo dopo il "
        "lavoro ✈️🍸 Mi piacciono anche il beauty e la skincare. "
        "Cerco nuove amicizie a Parma con cui condividere "
        "chiacchiere, viaggi e uscite!"
    ),

    # 16 - KAL
    persona(
        16, "Kal", 28, "UOMO", "Milano", "LAVORATORE",
        ["Inglese", "Arabo"],
        ["AMICIZIE", "COINQUILINO"],
        [
            ("ANIMALI", "Gatti"),
            ("MODA E STILE", "Thrift shop e vintage"),
            ("CIBO E GASTRONOMIA", "Cucina italiana"),
            ("FITNESS E BENESSERE", "Palestra e pesi"),
        ],
        "Hey! I'm Kal, recently moved to Milan for work "
        "and still figuring out the city 🇮🇹 I work in "
        "digital marketing and I'm looking for new friends "
        "and possibly a flatmate. Amo i gatti, il vintage "
        "shopping, la cucina italiana e andare in palestra. "
        "Always up for coffee or exploring new places!"
    ),

    # 17 - FRANCESCO
    persona(
        17, "Francesco", 26, "UOMO", "Modena", "STUDENTE",
        ["Italiano"],
        ["AMICIZIE", "COMPAGNO_STUDIO"],
        [
            ("MUSICA", "Rock"),
            ("NATURA", "Mare"),
            ("SOCIALITÀ", "Discoteca"),
            ("MOTORI", "Formula 1"),
        ],
        "Siciliano a Modena per 🏎️"
    ),

    # 18 - GIACOMO
    persona(
        18, "Giacomo", 28, "UOMO", "Parma", "STUDENTE",
        ["Italiano", "Russo"],
        ["COINQUILINO"],
        [
            ("MODA E STILE", "Streetwear"),
            ("ANIMALI", "Cani"),
            ("MOTORI", None),
        ],
        "Studio a Parma e sono alla ricerca di coinquilini 🏡 "
        "Mi piacciono lo streetwear, le macchine e i cani. "
        "Cerco una casa tranquilla dove si possa convivere "
        "bene, magari con persone con cui fare anche "
        "qualche uscita ogni tanto."
    ),

    # 19 - GIOELE
    persona(
        19, "Gioele", 29, "UOMO", "Roma", "LAVORATORE",
        ["Italiano", "Francese", "Inglese"],
        ["AMICIZIE", "COINQUILINO"],
        [
            ("MUSICA", "Rock"),
            ("SPORT", "Calcio"),
            ("NATURA", "Trekking"),
            ("SCIENZA E CONOSCENZA", "Storia"),
        ],
        "Calciatore professionale nel Lazio, ma sono in "
        "terra nemica! Tra allenamenti di calcio e musica "
        "rock, le mie giornate sono sempre abbastanza piene "
        "⚽🎸 Ma appena posso organizzo trekking o gite fuori porta."
    ),

    # 20 - GIULIA
    persona(
        20, "Giulia", 26, "DONNA", "Roma",
        "STUDENTE_LAVORATORE",
        ["Italiano", "Inglese"],
        ["AMICIZIE", "COMPAGNO_STUDIO"],
        [
            ("MUSICA", None),
            ("NATURA", "Trekking"),
            ("VIAGGI", None),
            ("EVENTI", "Concerti"),
        ],
        "Tra studio e lavoro cerco di non perdermi le cose "
        "belle: concerti, weekend fuori e camminate nella "
        "natura 🎶⛰️ Cerco nuove amicizie a Roma e qualcuno "
        "con cui studiare, magari alternando biblioteca "
        "e pause caffè!"
    ),

    # 21 - ALBERTO
    persona(
        21, "Alberto", 33, "UOMO", "Roma", "LAVORATORE",
        ["Italiano", "Inglese"],
        ["AMICIZIE"],
        [
            ("NATURA", None),
            ("CIBO E GASTRONOMIA", "Cucinare in compagnia"),
            ("SOCIALITÀ", None),
            ("ANIMALI", "Fattoria"),
        ],
        "Mi piace stare all'aria aperta, cucinare per gli "
        "amici e organizzare pranzi che finiscono a cena 🌿🍝 "
        "Amo gli animali e preferisco una bella giornata "
        "nella natura a un pomeriggio chiuso in casa. "
        "Cerco nuove amicizie a Roma!"
    ),

    # 22 - TOMMASO
    persona(
        22, "Tommaso", 32, "UOMO", "Bologna", "LAVORATORE",
        ["Italiano", "Inglese", "Francese"],
        ["AMICIZIE", "COINQUILINO"],
        [
            ("CINEMA", None),
            ("CIBO E GASTRONOMIA", "Cucinare in compagnia"),
            ("ARTE E CREATIVITÀ", "Fotografia"),
            ("NATURA", "Trekking"),
        ],
        "Fotografo freelance a Bologna 📸 Mi piace perdermi "
        "tra mercatini, cinema indipendenti e trattorie "
        "nascoste. Nel weekend, se non sono in giro a fare "
        "foto, probabilmente sono su qualche sentiero in "
        "montagna. Cerco nuove amicizie e qualcuno con "
        "cui condividere casa!"
    ),

    # 23 - ANDREA
    persona(
        23, "Andrea", 30, "NON_BINARIO", "Bologna",
        "STUDENTE_LAVORATORE",
        ["Italiano", "Inglese", "Spagnolo"],
        ["AMICIZIE", "COMPAGNO_STUDIO"],
        [
            ("MUSICA", "Indie"),
            ("ARTE E CREATIVITÀ", None),
            ("GIOCHI", "Giochi da tavolo"),
            ("VOLONTARIATO", "Diritti LGBT"),
        ],
        "Studio Design e lavoro part-time a Bologna 🎨 "
        "Tra concertini indie, sketchbook sempre nello zaino "
        "e serate giochi da tavolo, cerco di ritagliarmi tempo "
        "per conoscere persone nuove. Se ti va un caffè, "
        "una mostra o una partita a qualche gioco improbabile, "
        "scrivimi! 🌈"
    ),

    # 24 - MARCO
    persona(
        24, "Marco", 47, "UOMO", "Modena", "LAVORATORE",
        ["Italiano", "Inglese", "Tedesco"],
        ["AMICIZIE"],
        [
            ("CINEMA", "Fantascienza"),
            ("NATURA", "Montagna"),
            ("SCIENZA E CONOSCENZA", "Astronomia"),
            ("MOTORI", "Macchine e velocità"),
        ],
        "Appassionato di fantascienza, astronomia e motori 🚀 "
        "Nel tempo libero mi piace andare in montagna, "
        "scoprire nuovi posti e seguire tutto ciò che "
        "riguarda le auto. Cerco persone con cui condividere "
        "queste passioni e organizzare qualche uscita."
    ),

    # 25 - ROSANNA
    persona(
        25, "Rosanna", 43, "DONNA", "Modena", "LAVORATORE",
        ["Italiano"],
        ["AMICIZIE"],
        [
            ("FITNESS E BENESSERE", None),
            ("CIBO E GASTRONOMIA", "Pasticceria e dolci"),
            ("SCIENZA E CONOSCENZA", "Psicologia"),
            ("SOCIALITÀ", None),
        ],
        "Mi piace tenermi attiva, ma anche assaporare dolci🍰 "
        "Amo la psicologia e le chiacchiere davanti a un "
        "buon caffè. Cerco nuove amicizie a Modena per "
        "organizzare uscite, attività e qualche bella serata "
        "in compagnia."
    ),
]


# ==================================================
# FUNZIONI DI SUPPORTO
# ==================================================

def normalizza(testo):

    # confronta nomi ignorando maiuscole, accenti, differenze di spaziatura
    testo = unicodedata.normalize("NFKD", testo)

    testo = "".join(
        carattere for carattere in testo
        if not unicodedata.combining(carattere)
    )

    testo = testo.casefold()
    testo = testo.replace("–", "-").replace("—", "-")
    testo = re.sub(r"\s*-\s*", "-", testo)
    testo = re.sub(r"\s+", " ", testo)

    return testo.strip()


def trova_interesse(categoria, sottointeresse, catalogo):

    # cerca la macro - categoria e il sottointeresse rispettando la gerarchia
    # se un sotto-interesse esiste ma non è collegato alla categoria corretta, genera un errore esplicito

    padri = [
        interesse for interesse in catalogo
        if interesse.padre_id is None
        and normalizza(interesse.nome) == normalizza(categoria)
    ]

    if len(padri) != 1:
        raise CommandError(
            f"Categoria '{categoria}': trovate "
            f"{len(padri)} corrispondenze come macrocategoria."
        )

    padre = padri[0]

    if sottointeresse is None:
        return padre

    figli = [
        interesse for interesse in catalogo
        if interesse.padre_id == padre.pk
        and normalizza(interesse.nome)
        == normalizza(sottointeresse)
    ]

    if len(figli) == 1:
        return figli[0]

    if len(figli) > 1:
        raise CommandError(
            f"Interesse duplicato sotto '{categoria}': "
            f"'{sottointeresse}'."
        )

    # Diagnostica: l'interesse potrebbe essere presente ma collegato a un altro padre
    altrove = [
        interesse for interesse in catalogo
        if normalizza(interesse.nome)
        == normalizza(sottointeresse)
    ]

    if altrove:
        posizioni = []

        for interesse in altrove:
            genitore = next(
                (
                    elemento.nome
                    for elemento in catalogo
                    if elemento.pk == interesse.padre_id
                ),
                "NESSUN PADRE"
            )

            posizioni.append(
                f"id={interesse.pk}, padre={genitore}"
            )

        raise CommandError(
            f"'{categoria} > {sottointeresse}' non trovato "
            f"nel padre corretto. Nel DB esiste in: "
            + "; ".join(posizioni)
        )

    raise CommandError(
        f"Sottointeresse assente nel database: "
        f"{categoria} > {sottointeresse}"
    )


def trova_foto(cartella, numero):
    estensioni = {".jpg", ".jpeg", ".png", ".webp"}

    fotografie = [
        percorso
        for percorso in cartella.iterdir()
        if percorso.is_file()
        and percorso.suffix.lower() in estensioni
        and re.match(
            rf"^{numero:02d}[_\-.]",
            percorso.name
        )
    ]

    if len(fotografie) != 1:
        raise CommandError(
            f"Persona #{numero}: trovate "
            f"{len(fotografie)} fotografie. "
            f"Ne serve esattamente una."
        )

    return fotografie[0]

# genera una data di nascita corrispondente all'età indicata
def data_nascita_demo(eta):
    oggi = date.today()
    return date(oggi.year - eta, oggi.month, oggi.day)


# ==================================================
# RELAZIONI E DATI FRA DIVERSI PROFILI -> serve per l'esame, riguarda l'utente demo_04 (sara)
# ==================================================

def prepara_relazioni_esame(stdout):
    if not settings.DEBUG:
        raise CommandError("Scenario d'esame consentito solo in sviluppo (DEBUG=True).")

    numeri = (2, 3, 4, 5, 6, 7, 11)
    profili = {}

    for numero in numeri:
        username = f"demo_{numero:02d}"
        try:
            profili[numero] = Profilo.objects.get(user__username=username)
        except Profilo.DoesNotExist as errore:
            raise CommandError(
                f"Manca il profilo {username}. Prima ripristina il dataset demo."
            ) from errore

    try:
        club = Community.objects.get(titolo="Club del libro 📚")
        padel = Community.objects.get(titolo="Padel Social Club 🎾")
        study = Community.objects.get(titolo="Study Together ☕")
        f1 = Community.objects.get(titolo="F1 Watching 🏎️")
    except (Community.DoesNotExist, Community.MultipleObjectsReturned) as errore:
        raise CommandError(
            "Community demo mancanti o ambigue. Ripristina il dataset originale."
        ) from errore

    sara = profili[4]
    marco = profili[2]
    alice = profili[5]
    gaia = profili[6]
    alessandro = profili[7]
    persona_richiesta = profili[3]
    persona_like = profili[11]

    if club.organizzatore_id != sara.pk:
        raise CommandError("Sara non è l'organizzatrice del Club del libro.")
    if not all([
        padel.membri.filter(pk=sara.pk).exists(),
        study.membri.filter(pk=sara.pk).exists(),
        club.membri.filter(pk=sara.pk).exists(),
    ]):
        raise CommandError("Le appartenenze iniziali di Sara non corrispondono al dataset.")
    if f1.membri.filter(pk=sara.pk).exists():
        raise CommandError("Sara è già membro di F1 Watching: richiesta pendente non valida.")
    if club.membri.filter(pk=persona_richiesta.pk).exists():
        raise CommandError("La richiedente è già membro del Club del libro.")

    with transaction.atomic():
        for altro in (marco, alice):
            for mittente, destinatario in ((sara, altro), (altro, sara)):
                if Dislike.objects.filter(mittente=mittente, destinatario=destinatario).exists():
                    raise CommandError("Un Dislike esistente impedisce il Match demo.")
                Like.objects.get_or_create(mittente=mittente, destinatario=destinatario)

        if Dislike.objects.filter(mittente=persona_like, destinatario=sara).exists():
            raise CommandError("Dislike incompatibile con il Like in attesa.")
        if Like.objects.filter(mittente=sara, destinatario=persona_like).exists():
            raise CommandError("Il Like in attesa è già reciproco: ripristina prima i dati.")
        Like.objects.get_or_create(mittente=persona_like, destinatario=sara)

        if Dislike.objects.filter(mittente=sara, destinatario=gaia).exists():
            raise CommandError("Dislike incompatibile con il Like in uscita.")
        Like.objects.get_or_create(mittente=sara, destinatario=gaia)

        if Like.objects.filter(mittente=sara, destinatario=alessandro).exists():
            raise CommandError("Like incompatibile con il Dislike demo.")
        Dislike.objects.get_or_create(mittente=sara, destinatario=alessandro)

        conversazioni = (
            (marco, sara, "Ciao Sara! Ci vediamo per studiare domani?"),
            (sara, marco, "Volentieri! Possiamo trovarci in biblioteca alle 15."),
            (marco, sara, "Perfetto, porto anche gli appunti!"),
            (alice, sara, "Ehi Sara! Hai ascoltato il nuovo album?"),
            (sara, alice, "Non ancora! Me lo consigli?"),
        )
        for mittente, destinatario, testo in conversazioni:
            MessaggioPrivato.objects.get_or_create(
                mittente=mittente, destinatario=destinatario, testo=testo
            )

        messaggi_gruppo = (
            (club, sara, "Benvenuti nel Club del libro! Quale titolo scegliamo?"),
            (club, alice, "Io propongo un romanzo breve, così possiamo discuterne insieme!"),
            (study, marco, "Qualcuno viene a studiare in biblioteca venerdì?"),
            (study, sara, "Io ci sono! Ci vediamo nel pomeriggio."),
        )
        for gruppo, autore, testo in messaggi_gruppo:
            if not gruppo.membri.filter(pk=autore.pk).exists():
                raise CommandError(f"{autore.nome} non è membro di {gruppo.titolo}.")
            MessaggioCommunity.objects.get_or_create(
                community=gruppo, autore=autore, testo=testo
            )

        RichiestaCommunity.objects.get_or_create(
            utente=persona_richiesta, community=club,
            defaults={"stato": "PENDING"},
        )
        RichiestaCommunity.objects.get_or_create(
            utente=sara, community=f1,
            defaults={"stato": "PENDING"},
        )

        ValutazioneCommunity.objects.get_or_create(
            utente=sara, community=padel,
            defaults={"voto": 5},
        )

        notifiche = (
            (sara, "MATCH", "Hai un nuovo Match con Marco!", marco, None),
            (sara, "MATCH", "Hai un nuovo Match con Alice!", alice, None),
            (sara, "LIKE_RICEVUTO", "Hai ricevuto un Like!", persona_like, None),
            (sara, "MESSAGGIO_PRIVATO", "Marco ti ha inviato un nuovo messaggio.", marco, None),
            (sara, "MESSAGGIO_PRIVATO", "Alice ti ha inviato un nuovo messaggio.", alice, None),
            (sara, "MESSAGGIO_COMMUNITY", "Nuovo messaggio nel Club del libro.", None, club),
            (sara, "RICHIESTA_COMMUNITY", "Anna ha richiesto di partecipare al Club del libro.", persona_richiesta, club),
            (f1.organizzatore, "RICHIESTA_COMMUNITY", "Sara ha richiesto di partecipare a F1 Watching.", sara, f1),
        )
        for destinatario, tipo, testo, profilo, gruppo in notifiche:
            Notifica.objects.get_or_create(
                destinatario=destinatario, tipo=tipo, testo=testo,
                profilo_collegato=profilo, community_collegata=gruppo,
                defaults={"letta": False},
            )

    stdout.write("\nSCENARIO ESAME PREPARATO: demo_04 (Sara)")
    stdout.write("2 Match, 2 chat private, 1 Like ricevuto in attesa.")
    stdout.write("2 chat Community, richiesta ricevuta e richiesta inviata.")
    stdout.write("1 valutazione e notifiche dimostrative.")
    stdout.write("Puoi rilanciare il comando senza duplicare le interazioni definite.")

# ==================================================
# MANAGEMENT COMMAND
# ==================================================

class Command(BaseCommand):

    help = "Crea 25 persone demo per FuoriRete"

    def add_arguments(self, parser):
        parser.add_argument(
            "--prepara-esame",
            action="store_true",
            help="Prepara interazioni per il profilo demo_04 senza duplicarle",
        )
        parser.add_argument(
            "--controlla",
            action="store_true",
            help="Controlla i dati senza creare account",
        )

    def handle(self, *args, **options):

        if options["prepara_esame"]:
            if options["controlla"]:
                raise CommandError("Usa --prepara-esame senza --controlla.")
            prepara_relazioni_esame(self.stdout)
            return

        cartella_foto = (
            Path(settings.BASE_DIR)
            / "dati_demo"
            / "foto_profili"
        )

        if not cartella_foto.is_dir():
            raise CommandError(
                f"Cartella fotografie non trovata: {cartella_foto}"
            )

        numeri = [dati["numero"] for dati in PERSONE]

        if sorted(numeri) != list(range(1, 26)):
            raise CommandError(
                "Devono esserci esattamente le persone da 1 a 25."
            )

        self.stdout.write(
            "Controllo delle 25 fotografie..."
        )

        fotografie = {}

        for dati in PERSONE:
            numero = dati["numero"]
            fotografie[numero] = trova_foto(
                cartella_foto, numero
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Tutte le 25 fotografie sono presenti."
            )
        )

        # ------------------------------------------
        # CONTROLLO INTERESSI
        # ------------------------------------------

        self.stdout.write(
            "\nControllo degli interessi..."
        )

        catalogo = list(Interesse.objects.all())

        if not catalogo:
            raise CommandError(
                "Il catalogo degli interessi è vuoto."
            )

        interessi_per_persona = {}
        errori = []

        for dati in PERSONE:
            numero = dati["numero"]
            risultati = []

            for categoria, sottointeresse in dati["interessi"]:
                try:
                    interesse = trova_interesse(
                        categoria,
                        sottointeresse,
                        catalogo
                    )

                    if interesse not in risultati:
                        risultati.append(interesse)

                except CommandError as errore:
                    errori.append(
                        f"{dati['nome']} (#{numero}): {errore}"
                    )

            interessi_per_persona[numero] = risultati

        if errori:
            for errore in errori:
                self.stdout.write(
                    self.style.ERROR(errore)
                )

            raise CommandError(
                "Interessi non coerenti con il catalogo. "
                "Nessun account creato."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Tutti gli interessi sono stati riconosciuti."
            )
        )

        # ------------------------------------------
        # CONTROLLO DATI PROFILI
        # ------------------------------------------

        generi_validi = {
            valore for valore, _ in Profilo.GENERI
        }

        occupazioni_valide = {
            valore for valore, _ in Profilo.OCCUPAZIONI
        }

        for dati in PERSONE:
            numero = dati["numero"]

            if dati["genere"] not in generi_validi:
                raise CommandError(
                    f"Genere non valido: persona #{numero}"
                )

            if dati["occupazione"] not in occupazioni_valide:
                raise CommandError(
                    f"Occupazione non valida: persona #{numero}"
                )

            if len(dati["descrizione"]) > 500:
                raise CommandError(
                    f"Descrizione oltre 500 caratteri: "
                    f"persona #{numero}"
                )

            if not 1 <= len(dati["lingue"]) <= 4:
                raise CommandError(
                    f"Numero lingue non valido: persona #{numero}"
                )

            if len(set(dati["lingue"])) != len(dati["lingue"]):
                raise CommandError(
                    f"Lingue duplicate: persona #{numero}"
                )

            if any(
                lingua not in Profilo.LINGUE_DISPONIBILI
                for lingua in dati["lingue"]
            ):
                raise CommandError(
                    f"Lingua non valida: persona #{numero}"
                )

            if not 1 <= len(dati["cerca"]) <= 3:
                raise CommandError(
                    f"Scelte cosa_cerca non valide: "
                    f"persona #{numero}"
                )

            if len(set(dati["cerca"])) != len(dati["cerca"]):
                raise CommandError(
                    f"Scelte cosa_cerca duplicate: "
                    f"persona #{numero}"
                )

            if any(
                scelta not in Profilo.COSA_CERCA
                for scelta in dati["cerca"]
            ):
                raise CommandError(
                    f"Valore cosa_cerca non valido: "
                    f"persona #{numero}"
                )

            if not interessi_per_persona[numero]:
                raise CommandError(
                    f"Nessun interesse: persona #{numero}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Tutti i dati dei profili sono validi."
            )
        )

        # ------------------------------------------
        # MODALITÀ CONTROLLO
        # ------------------------------------------

        if options["controlla"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nCONTROLLO COMPLETATO: "
                    "nessun account creato."
                )
            )
            return

        # ------------------------------------------
        # CREAZIONE ACCOUNT
        # ------------------------------------------

        self.stdout.write(
            "\nCreazione dei profili demo..."
        )

        creati = 0
        saltati = 0

        with transaction.atomic():

            for dati in PERSONE:
                numero = dati["numero"]
                username = f"demo_{numero:02d}"

                if User.objects.filter(
                    username=username
                ).exists():
                    self.stdout.write(
                        f"[GIÀ PRESENTE] {username}"
                    )
                    saltati += 1
                    continue

                user = User.objects.create_user(
                    username=username,
                    password=PASSWORD_DEMO,
                    first_name=dati["nome"],
                    email=f"{username}@example.com",
                )

                profilo = Profilo(
                    user=user,
                    nome=dati["nome"],
                    data_nascita=data_nascita_demo(
                        dati["eta"]
                    ),
                    genere=dati["genere"],
                    citta=dati["citta"],
                    occupazione=dati["occupazione"],
                    lingue=dati["lingue"],
                    cosa_cerca=dati["cerca"],
                    descrizione=dati["descrizione"],
                )

                percorso = fotografie[numero]

                with percorso.open("rb") as file_foto:
                    profilo.foto.save(
                        f"demo_{numero:02d}"
                        f"{percorso.suffix.lower()}",
                        File(file_foto),
                        save=False
                    )

                try:
                    profilo.full_clean()
                except ValidationError as errore:
                    raise CommandError(
                        f"Profilo {username} non valido: {errore}"
                    )

                profilo.save()

                profilo.interessi.set(
                    interessi_per_persona[numero]
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"[CREATO] {username}: "
                        f"{dati['nome']}, "
                        f"{len(interessi_per_persona[numero])} interessi"
                    )
                )

                creati += 1

        self.stdout.write(
            self.style.SUCCESS(
                "\nPOPOLAMENTO COMPLETATO!"
            )
        )

        self.stdout.write(
            f"Account creati: {creati}"
        )
        self.stdout.write(
            f"Account già presenti: {saltati}"
        )
        self.stdout.write(
            "\nUsername: demo_01 ... demo_25"
        )
        self.stdout.write(
            f"Password demo: {PASSWORD_DEMO}"
        )
