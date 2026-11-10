
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from gestione.models import Community, Evento, Interesse, Profilo


# ============================================================
# DATI UFFICIALI DELLE 15 COMMUNITY
# ============================================================

def community(numero, titolo, descrizione, organizzatore,
              citta, interessi, membri):
    return {
        "numero": numero,
        "titolo": titolo,
        "descrizione": descrizione,
        "organizzatore": organizzatore,
        "citta": citta,
        "interessi": interessi,
        "membri": membri,
    }


# Per gli interessi:
# ("CATEGORIA", None) = intera macrocategoria
# ("CATEGORIA", "Sottointeresse") = sottointeresse preciso

COMMUNITY_DEMO = [

    community(
        1,
        "Club del libro 📚",
        "Un libro al mese, tante opinioni diverse e possibilmente "
        "un caffè davanti! 📖☕ Un piccolo club per chi ama "
        "leggere, scoprire nuovi autori e confrontarsi sulle "
        "proprie letture. Non importa quanto leggi o quale "
        "genere preferisci: scegliamo insieme i libri e "
        "organizziamo incontri per parlarne, senza spoiler "
        "prima del tempo!",
        4, "Modena",
        [
            ("ARTE E CREATIVITÀ", "Club del libro"),
            ("SOCIALITÀ", "Caffè"),
        ],
        [4, 5, 11]
    ),

    community(
        2,
        "Padel Social Club 🎾",
        "Hai voglia di giocare a padel ma ti manca sempre "
        "qualcuno per completare il campo? 🎾 Questo è il "
        "posto giusto! Organizziamo partite amichevoli a "
        "Modena, aperte sia a chi gioca da tempo sia a chi "
        "vuole iniziare. L'obiettivo è divertirsi, conoscere "
        "nuove persone e magari fermarsi per qualcosa da "
        "bere dopo la partita!",
        6, "Modena",
        [
            ("SPORT", "Tennis e padel"),
            ("SOCIALITÀ", "Eventi in città"),
        ],
        [6, 4, 2, 5]
    ),

    community(
        3,
        "F1 Watching 🏎️",
        "Semafori spenti e via! 🏎️🏁 Una community per chi "
        "vive la Formula 1 tra strategie discutibili, team "
        "radio memorabili e domeniche davanti al Gran Premio. "
        "Organizziamo watch party, commentiamo qualifiche e "
        "gare e condividiamo le novità del paddock. "
        "Qualunque sia la tua scuderia, sei nel posto giusto!",
        17, "Modena",
        [
            ("EVENTI", None),
            ("MOTORI", "Formula 1"),
            ("SOCIALITÀ", "Eventi in città"),
        ],
        [17, 18, 24, 14]
    ),

    community(
        4,
        "Study Together ☕",
        "Studiare da soli è triste, rimandare gli esami ancora "
        "di più 🥲📚 Qui ci organizziamo per studiare insieme "
        "in biblioteca, confrontarci sugli argomenti più "
        "difficili e motivarci durante le sessioni. "
        "Facoltà diverse, stesso obiettivo: arrivare vivi "
        "alla fine degli esami. Le pause caffè sono "
        "praticamente obbligatorie!",
        5, "Modena",
        [
            ("SCIENZA E CONOSCENZA", None),
            ("SOCIALITÀ", "Caffè"),
        ],
        [5, 4, 6, 2, 11, 17]
    ),

    community(
        5,
        "Take a Hike! 🥾",
        "Scarpe comode, zaino in spalla e si parte! 🌿🥾 "
        "Una community per chi ama camminare, stare all'aria "
        "aperta e scoprire sentieri e posti nuovi nei dintorni "
        "di Roma. Organizziamo trekking di diversa difficoltà, "
        "passeggiate e gite fuori porta. Non devi essere un "
        "escursionista esperto: basta avere voglia di muoverti "
        "e conoscere nuove persone!",
        20, "Roma",
        [
            ("NATURA", "Trekking"),
            ("VIAGGI", "Weekend e gite fuori porta"),
            ("NATURA", None),
        ],
        [20, 21, 19]
    ),

    community(
        6,
        "Uni & Aperitivo 🍹",
        "Le amicizie migliori nascono fuori dall'aula! 🍹 "
        "Una community per studenti universitari che hanno "
        "voglia di conoscere nuove persone e staccare un po' "
        "tra una lezione e l'altra. Organizziamo aperitivi, "
        "serate tranquille e incontri informali nei locali "
        "di Milano. Perfetta anche se sei appena arrivato "
        "in città e non conosci ancora nessuno!",
        13, "Milano",
        [
            ("SOCIALITÀ", "Aperitivi"),
            ("SOCIALITÀ", "Eventi in città"),
        ],
        [13, 1, 10]
    ),

    community(
        7,
        "Creative Corner 🎨",
        "Uno spazio per dare libero sfogo alla creatività! "
        "🎨✂️ Disegno, collage, fotografia, piccoli progetti "
        "DIY e idee da realizzare insieme. Creative Corner "
        "nasce per condividere ispirazioni, organizzare "
        "pomeriggi creativi e conoscere persone con la stessa "
        "voglia di sperimentare. Non serve essere artisti: "
        "qui conta soprattutto divertirsi creando qualcosa!",
        23, "Bologna",
        [
            ("ARTE E CREATIVITÀ", None),
            ("ARTE E CREATIVITÀ", "Fotografia"),
            ("ARTE E CREATIVITÀ", "DIY e artigianato"),
        ],
        [23, 22]
    ),

    community(
        8,
        "Tony Boy Crew 🎤",
        "Ascolti Tony Boy in loop ma non hai nessuno con cui "
        "andare ai suoi concerti? 🎧🔥 Questo gruppo nasce "
        "per organizzarsi, trovare compagnia per i live, "
        "condividere le canzoni preferite e parlare delle "
        "nuove uscite. Che tu lo segua da sempre o abbia "
        "appena iniziato ad ascoltarlo, sei il benvenuto!",
        2, "Modena",
        [
            ("MUSICA", "Rap e hip-hop"),
            ("EVENTI", "Concerti"),
        ],
        [2, 14, 5]
    ),

    community(
        9,
        "Roomies Wanted 🏡",
        "Cerchi coinquilini ma vorresti conoscere le persone "
        "prima di condividere casa? 🏡 Questa community è "
        "pensata per chi cerca stanza, appartamento o persone "
        "con cui organizzare una convivenza a Milano. "
        "Possiamo scambiarci consigli sulla ricerca, "
        "condividere annunci e soprattutto conoscerci meglio "
        "per capire se potremmo essere compatibili!",
        10, "Milano",
        [
            ("SOCIALITÀ", None),
        ],
        [10, 1, 13, 16]
    ),

    community(
        10,
        "Let's Talk! 🌍",
        "Practice your English, improve your Italian or teach "
        "someone a new language! 🌍☕ Let's Talk è una community "
        "per conoscere persone attraverso lo scambio linguistico. "
        "Organizziamo chiacchierate informali, incontri al bar "
        "e attività per esercitarci senza la pressione di "
        "una lezione. Tutti i livelli sono benvenuti: "
        "l'importante è avere voglia di parlare e imparare!",
        1, "Milano",
        [
            ("VIAGGI", "Scambio linguistico"),
            ("SOCIALITÀ", "Caffè"),
        ],
        [1, 10, 16, 13]
    ),

    community(
        11,
        "Basic Beach 🏖️",
        "Appena esce il sole, la domanda è sempre la stessa: "
        "si va al mare? ☀️🌊 Basic Beach nasce per organizzare "
        "giornate in spiaggia, weekend al mare e piccole "
        "fughe dalla città. Ci mettiamo d'accordo su "
        "destinazioni, trasporti e programmi, così nessuno "
        "deve rinunciare a una giornata al mare perché "
        "non sa con chi partire!",
        3, "Parma",
        [
            ("VIAGGI", "Weekend e gite fuori porta"),
            ("NATURA", "Mare"),
            ("VIAGGI", None),
        ],
        [3, 15, 7, 9, 18]
    ),

    community(
        12,
        "Chimica organica survival club 🧪",
        "Chimica organica ti sta facendo perdere la voglia "
        "di vivere? 🧪📚 Non sei solo! Questo gruppo nasce "
        "per affrontare insieme esercizi, meccanismi di "
        "reazione e argomenti difficili, condividere appunti "
        "e organizzare sessioni di ripasso prima degli esami. "
        "Un posto dove fare domande senza sentirsi giudicati "
        "e aiutarsi a vicenda!",
        4, "Modena",
        [
            ("SCIENZA E CONOSCENZA", None),
            ("SCIENZA E CONOSCENZA", "Biologia e natura"),
        ],
        [4, 5, 6, 11]
    ),

    community(
        13,
        "Game Night Marathon 🎲",
        "Una partita veloce e poi andiamo? Spoiler: non succede "
        "mai 🎲😂 Organizziamo serate e maratone di giochi "
        "da tavolo, carte e videogiochi, tra sfide competitive "
        "e partite completamente assurde. Porta il tuo gioco "
        "preferito o vieni semplicemente a provarne uno nuovo. "
        "Sono benvenuti sia i veterani sia chi non conosce "
        "nemmeno le regole!",
        11, "Modena",
        [
            ("GIOCHI", "Giochi da tavolo"),
            ("GIOCHI", "Giochi di carte"),
            ("GIOCHI", "Videogiochi"),
        ],
        [11, 4, 2, 5, 6]
    ),

    community(
        14,
        "Music Talks! 🎧",
        "Hai mai ascoltato un album talmente bello da volerlo "
        "raccontare a chiunque? 🎧 Music Talks è uno spazio "
        "per parlare di musica senza giudizi: nuovi album, "
        "artisti sottovalutati, playlist da condividere e "
        "discussioni infinite su quale sia il disco migliore "
        "di sempre. Dal rock al rap, dall'indie al pop: "
        "basta avere voglia di ascoltare!",
        14, "Modena",
        [
            ("MUSICA", None),
            ("MUSICA", "Rock"),
            ("MUSICA", "Indie"),
            ("MUSICA", "Rap e hip-hop"),
        ],
        [14, 17, 2, 5, 11]
    ),

    community(
        15,
        "Vintage Hunting Milano 🧥",
        "Il sabato perfetto? Un giro per mercatini, qualche "
        "tesoro vintage trovato per caso e un caffè per "
        "commentare gli acquisti ☕🧥 Organizziamo pomeriggi "
        "tra negozi second hand, mercatini e piccoli vintage "
        "shop di Milano. Non serve essere esperti di moda, "
        "basta amare i pezzi particolari e avere voglia "
        "di girare la città in compagnia!",
        16, "Milano",
        [
            ("MODA E STILE", "Thrift shop e vintage"),
            ("MODA E STILE", "Streetwear"),
            ("SOCIALITÀ", None),
        ],
        [16, 10, 13, 1]
    ),
]


# ============================================================
# DATI UFFICIALI DEI 27 EVENTI
# ============================================================

def evento(comunita, titolo, descrizione, inizio, fine,
           luogo, costo="0.00", cosa_portare=""):
    return {
        "comunita": comunita,
        "titolo": titolo,
        "descrizione": descrizione,
        "inizio": inizio,
        "fine": fine,
        "luogo": luogo,
        "costo": costo,
        "cosa_portare": cosa_portare,
    }


# Le date sono nel formato:
# AAAA-MM-GG HH:MM

EVENTI_DEMO = [

    # COMMUNITY 01 - CLUB DEL LIBRO

    evento(
        1,
        "Il libro del mese: ci vediamo al caffè! 📚",
        "Primo incontro del nostro club del libro! Ci "
        "ritroviamo per parlare della lettura scelta insieme, "
        "confrontare le nostre impressioni e proporre il "
        "prossimo titolo. Non serve preparare una recensione: "
        "bastano curiosità e voglia di chiacchierare.",
        "2026-11-07 16:00",
        "2026-11-07 18:00",
        "Caffetteria in centro, Modena",
        "0.00",
        "Il libro del mese, se disponibile."
    ),

    evento(
        1,
        "Blind Date With a Book 🎁",
        "Ognuno porta un libro che ha amato, impacchettato "
        "e senza titolo visibile. Scriviamo qualche indizio "
        "sulla confezione e ci scambiamo i libri a sorpresa! "
        "Un pomeriggio per scoprire letture fuori dalla "
        "propria comfort zone.",
        "2026-11-28 15:30",
        "2026-11-28 17:30",
        "Sala comune da concordare, Modena",
        "0.00",
        "Un libro impacchettato da scambiare."
    ),

    # COMMUNITY 02 - PADEL

    evento(
        2,
        "Friday Padel Mix 🎾",
        "Partite amichevoli con coppie formate sul momento "
        "e rotazione dei giocatori. Non serve avere un "
        "partner fisso e sono benvenuti anche i principianti. "
        "L'obiettivo è giocare, divertirsi e conoscere "
        "persone nuove!",
        "2026-11-06 18:30",
        "2026-11-06 20:30",
        "Centro padel, Modena (campo da concordare)",
        "10.00",
        "Abbigliamento sportivo, scarpe adatte, acqua e "
        "racchetta, se disponibile."
    ),

    evento(
        2,
        "Padel & Spritz 🍹",
        "Un pomeriggio dedicato al padel, seguito da un "
        "aperitivo per conoscerci anche fuori dal campo. "
        "Facciamo qualche partita senza troppo agonismo "
        "e poi ci fermiamo a chiacchierare!",
        "2026-11-21 16:00",
        "2026-11-21 19:00",
        "Centro padel e bar nelle vicinanze, Modena",
        "15.00",
        "Abbigliamento sportivo e acqua."
    ),

    # COMMUNITY 03 - FORMULA 1

    evento(
        3,
        "Race Replay & Pizza Night 🏎️",
        "Riviviamo insieme una delle gare più emozionanti "
        "della Formula 1 e commentiamo sorpassi, strategie "
        "e team radio. Ognuno può proporre la propria gara "
        "preferita: preparatevi a discussioni infinite!",
        "2026-11-13 20:00",
        "2026-11-13 23:00",
        "Sala privata da concordare, Modena",
        "0.00",
        ""
    ),

    evento(
        3,
        "F1 Quiz Night 🏆",
        "Quanto ne sai davvero di Formula 1? Ci sfidiamo "
        "in un quiz a squadre su piloti, circuiti, record "
        "storici e momenti indimenticabili. Sono benvenuti "
        "anche i tifosi alle prime armi!",
        "2026-12-04 20:30",
        "2026-12-04 22:30",
        "Locale da concordare, Modena",
        "0.00",
        ""
    ),

    # COMMUNITY 04 - STUDIO

    evento(
        4,
        "Study Session: No Distractions ☕",
        "Un pomeriggio di studio condiviso per recuperare "
        "lezioni, preparare esami e ritrovare la motivazione. "
        "Studiamo individualmente, ma facciamo pause "
        "insieme per conoscerci e confrontarci.",
        "2026-11-09 14:30",
        "2026-11-09 18:00",
        "Biblioteca universitaria, Modena",
        "0.00",
        "Libri, appunti, computer e materiale di studio."
    ),

    evento(
        4,
        "Pomodoro Study Marathon 🍅",
        "Proviamo a studiare insieme utilizzando la tecnica "
        "del pomodoro: sessioni di concentrazione intervallate "
        "da pause brevi. Perfetto per chi fatica a iniziare "
        "o vuole rendere più produttiva una giornata di studio.",
        "2026-11-25 10:00",
        "2026-11-25 16:00",
        "Sala studio universitaria, Modena",
        "0.00",
        "Materiale di studio, computer se necessario "
        "e pranzo al sacco."
    ),

    # COMMUNITY 05 - TREKKING

    evento(
        5,
        "Sunday Nature Walk 🌿",
        "Una camminata di gruppo sui sentieri nei dintorni "
        "di Roma, pensata per chi vuole trascorrere una "
        "giornata nella natura e conoscere persone nuove. "
        "Sceglieremo insieme un itinerario accessibile, "
        "in base alle condizioni meteo.",
        "2026-11-15 09:00",
        "2026-11-15 15:30",
        "Area escursionistica nei dintorni di Roma, "
        "percorso da concordare",
        "0.00",
        "Scarpe da trekking, acqua, snack, pranzo al sacco "
        "e giacca impermeabile."
    ),

    evento(
        5,
        "Autumn Hiking & Picnic 🍂",
        "Una giornata tra sentieri, paesaggi autunnali "
        "e un picnic in compagnia. Camminiamo con calma, "
        "facciamo qualche pausa fotografica e ci godiamo "
        "il tempo all'aria aperta.",
        "2026-11-29 09:30",
        "2026-11-29 16:00",
        "Parco naturale nei dintorni di Roma, "
        "itinerario da concordare",
        "0.00",
        "Scarpe da trekking, acqua, pranzo al sacco "
        "e abbigliamento caldo."
    ),

    # COMMUNITY 06 - APERITIVO

    evento(
        6,
        "After Uni Aperitivo 🍹",
        "Università, esami, lezioni infinite... "
        "ci meritiamo un aperitivo! Un incontro informale "
        "per conoscere altri studenti a Milano, fare due "
        "chiacchiere e magari trovare qualcuno con cui "
        "organizzare nuove uscite.",
        "2026-11-12 18:30",
        "2026-11-12 21:00",
        "Locale per aperitivi, zona universitaria di Milano",
        "10.00",
        ""
    ),

    evento(
        6,
        "New in Milano? Meet New People! 🫶",
        "Sei arrivato da poco a Milano oppure vuoi "
        "semplicemente allargare il tuo giro di amicizie? "
        "Organizziamo un aperitivo con piccoli giochi "
        "rompighiaccio per conoscerci senza imbarazzi.",
        "2026-12-03 19:00",
        "2026-12-03 21:30",
        "Caffetteria con aperitivo, Milano",
        "8.00",
        ""
    ),

    # COMMUNITY 07 - CREATIVE CORNER

    evento(
        7,
        "Collage & Coffee 🎨",
        "Un pomeriggio creativo tra ritagli, colori e tanta "
        "ispirazione! Realizziamo collage, moodboard e "
        "piccoli progetti artistici utilizzando riviste, "
        "fotografie e materiali di recupero. Non serve "
        "avere esperienza: l'importante è sperimentare "
        "e divertirsi insieme.",
        "2026-11-14 15:00",
        "2026-11-14 18:00",
        "Spazio creativo condiviso, Bologna",
        "5.00",
        "Vecchie riviste, fotografie, forbici e qualsiasi "
        "materiale creativo da riutilizzare."
    ),

    # COMMUNITY 08 - TONY BOY

    evento(
        8,
        "Tony Boy Listening Party 🎧",
        "Una serata dedicata a Tony Boy! Ascoltiamo insieme "
        "le nostre tracce preferite, confrontiamo album "
        "e collaborazioni e condividiamo le canzoni che "
        "non riusciamo a toglierci dalla testa. Perfetta "
        "per conoscere altri fan e organizzarsi per "
        "eventuali concerti futuri.",
        "2026-11-20 20:30",
        "2026-11-20 23:00",
        "Sala privata da concordare, Modena",
        "0.00",
        "La tua top 5 delle canzoni di Tony Boy."
    ),

    # COMMUNITY 09 - ROOMIES WANTED
    # Nessun evento iniziale.

    # COMMUNITY 10 - LANGUAGE EXCHANGE

    evento(
        10,
        "Language Exchange Café 🌍",
        "Let's practice together! Un pomeriggio di "
        "conversazione informale per esercitare italiano, "
        "inglese e altre lingue. Ci dividiamo in piccoli "
        "gruppi e cambiamo lingua durante l'incontro. "
        "Non importa il livello: gli errori fanno parte "
        "dell'apprendimento!",
        "2026-11-18 17:00",
        "2026-11-18 19:00",
        "Caffetteria in centro, Milano",
        "0.00",
        ""
    ),

    # COMMUNITY 11 - BASIC BEACH

    evento(
        11,
        "Beach Plans & Coffee ☀️",
        "Ci incontriamo per conoscerci e organizzare "
        "la nostra prossima gita al mare! Scegliamo "
        "insieme destinazione, trasporti e attività, "
        "cercando una soluzione comoda per tutti. "
        "Un'occasione per creare il nostro gruppo "
        "di compagni di viaggio.",
        "2026-11-08 16:00",
        "2026-11-08 18:00",
        "Caffetteria in centro, Parma",
        "0.00",
        "Idee per destinazioni e possibili itinerari."
    ),

    evento(
        11,
        "Winter Sea Escape 🌊",
        "Chi ha detto che il mare è bello soltanto "
        "d'estate? Organizziamo una giornata sulla "
        "costa romagnola tra passeggiate in spiaggia, "
        "fotografie e una pausa pranzo vista mare. "
        "Trasporto ed eventuali acquisti personali "
        "non sono inclusi.",
        "2026-12-06 08:00",
        "2026-12-06 20:00",
        "Riviera romagnola, località e punto di "
        "ritrovo da concordare",
        "0.00",
        "Abbigliamento caldo, scarpe comode, "
        "acqua e pranzo al sacco."
    ),

    # COMMUNITY 12 - CHIMICA ORGANICA

    evento(
        12,
        "Organic Chemistry: Reaction Mechanisms 🧪",
        "Sessione di ripasso collettivo dedicata ai "
        "principali meccanismi di reazione della chimica "
        "organica. Lavoriamo sugli esercizi, confrontiamo "
        "i nostri ragionamenti e cerchiamo di chiarire "
        "insieme i passaggi più difficili. Nessuna lezione "
        "formale, soltanto studenti che si aiutano!",
        "2026-11-16 15:00",
        "2026-11-16 18:00",
        "Aula studio universitaria, Modena",
        "0.00",
        "Appunti, esercizi, tavola periodica, "
        "quaderno e calcolatrice."
    ),

    # COMMUNITY 13 - GAME NIGHT
    # Quattro eventi.

    evento(
        13,
        "Board Games Until Midnight 🎲",
        "Una lunga serata dedicata ai giochi da tavolo! "
        "Dai classici ai giochi di strategia, fino ai "
        "party game più assurdi. Organizziamo tavoli "
        "diversi in base alle preferenze, così tutti "
        "possono partecipare, anche chi non conosce "
        "le regole.",
        "2026-11-14 19:00",
        "2026-11-15 00:00",
        "Sala comune da concordare, Modena",
        "0.00",
        "Il proprio gioco da tavolo preferito, "
        "se disponibile."
    ),

    evento(
        13,
        "Mario Kart Tournament 🏎️🎮",
        "Preparati a sfide, gusci blu e amicizie messe "
        "seriamente alla prova! Organizziamo un torneo "
        "amatoriale di Mario Kart con partite a eliminazione "
        "e una finale. Non serve essere professionisti: "
        "contano soprattutto il divertimento e un "
        "pizzico di fortuna.",
        "2026-12-05 17:00",
        "2026-12-05 21:00",
        "Sala comune con postazione di gioco, Modena",
        "0.00",
        "Un controller compatibile, se disponibile."
    ),

    evento(
        13,
        "UNO Tournament 🃏",
        "Una serata di partite a UNO tra +4, cambi di "
        "colore e amicizie messe alla prova! "
        "Organizziamo piccoli tavoli e un torneo "
        "amichevole aperto anche a chi non gioca da anni.",
        "2026-11-19 20:30",
        "2026-11-19 23:00",
        "Sala comune da concordare, Modena",
        "0.00",
        "Un mazzo di UNO, se disponibile."
    ),

    evento(
        13,
        "Sunday Board Game Café ☕",
        "Un pomeriggio tranquillo dedicato ai giochi "
        "da tavolo e alle chiacchiere. Scegliamo insieme "
        "a cosa giocare, alternando giochi veloci e "
        "partite più lunghe. Perfetto anche per chi "
        "vuole conoscere il gruppo per la prima volta!",
        "2026-12-13 15:00",
        "2026-12-13 18:30",
        "Locale con tavoli da gioco, Modena "
        "(da concordare)",
        "0.00",
        "Un gioco da proporre, facoltativo."
    ),

    # COMMUNITY 14 - MUSIC TALKS
    # Tre eventi.

    evento(
        14,
        "Album Listening Session 🎧",
        "Ognuno propone un album che considera speciale "
        "e ne ascoltiamo insieme una selezione di brani. "
        "Parliamo di testi, produzioni, artisti e "
        "impressioni personali. Dall'indie al rock, "
        "dal rap all'elettronica: nessun genere è escluso!",
        "2026-11-10 20:00",
        "2026-11-10 22:30",
        "Spazio di ritrovo da concordare, Modena",
        "0.00",
        "Il titolo di un album da proporre al gruppo."
    ),

    evento(
        14,
        "Discover New Artists 🎶",
        "Hai scoperto un artista che secondo te merita "
        "più attenzione? Questa è la serata giusta "
        "per farlo conoscere! Condividiamo brani, "
        "guardiamo esibizioni e costruiamo insieme "
        "una playlist con le migliori scoperte "
        "musicali del gruppo.",
        "2026-12-01 20:30",
        "2026-12-01 22:30",
        "Spazio di ritrovo da concordare, Modena",
        "0.00",
        "Una canzone di un artista poco conosciuto "
        "da condividere."
    ),

    evento(
        14,
        "Guess the Song 🎵",
        "Una serata di quiz musicali! Ascoltiamo pochi "
        "secondi di una canzone e proviamo a indovinare "
        "titolo, artista o album. Dal rock al rap, "
        "passando per indie e pop: nessun genere escluso!",
        "2026-12-11 20:30",
        "2026-12-11 22:30",
        "Spazio di ritrovo da concordare, Modena",
        "0.00",
        ""
    ),

    # COMMUNITY 15 - VINTAGE HUNTING

    evento(
        15,
        "Saturday Vintage Hunt 🧥",
        "Un pomeriggio tra negozi second hand e "
        "mercatini vintage di Milano alla ricerca "
        "di pezzi particolari, giacche, accessori "
        "e piccoli tesori nascosti. Nessun obbligo "
        "di acquistare: possiamo anche soltanto "
        "esplorare e prendere ispirazione!",
        "2026-11-14 14:30",
        "2026-11-14 18:00",
        "Zona Navigli, Milano - ritrovo da definire",
        "0.00",
        "Una borsa riutilizzabile, facoltativa."
    ),

    evento(
        15,
        "Thrift Challenge: Under 20€ 👟",
        "Una piccola sfida di shopping vintage! "
        "Ci dividiamo in gruppi e cerchiamo il pezzo "
        "più interessante spendendo al massimo 20 euro. "
        "Alla fine ci ritroviamo per mostrare le nostre "
        "scoperte e votare l'acquisto più originale. "
        "Partecipare senza comprare nulla è possibile! "
        "Il limite di 20 euro non è una quota di iscrizione.",
        "2026-12-12 15:00",
        "2026-12-12 18:30",
        "Negozi second hand e mercatini, Milano",
        "0.00",
        ""
    ),
]


# ============================================================
# FUNZIONI DI SUPPORTO
# ============================================================

def username_demo(numero):
    return f"demo_{numero:02d}"


def trova_fotografia(cartella, numero):
    estensioni = {".jpg", ".jpeg", ".png", ".webp"}

    immagini = [
        percorso
        for percorso in cartella.iterdir()
        if percorso.is_file()
        and percorso.suffix.lower() in estensioni
        and re.match(
            rf"^{numero:02d}[_\-.]",
            percorso.name
        )
    ]

    if len(immagini) != 1:
        raise CommandError(
            f"Community #{numero:02d}: trovate "
            f"{len(immagini)} immagini. "
            "Deve essercene esattamente una, "
            f"con prefisso '{numero:02d}_'."
        )

    return immagini[0]


def trova_interesse(categoria, sottointeresse):
    """
    Cerca esclusivamente nella gerarchia ufficiale.
    Non crea interessi nuovi e non usa nomi simili.
    """

    padri = Interesse.objects.filter(
        nome=categoria,
        padre__isnull=True,
    )

    if padri.count() != 1:
        raise CommandError(
            f"Macrocategoria non univoca o assente: "
            f"'{categoria}' (trovate {padri.count()})."
        )

    padre = padri.get()

    if sottointeresse is None:
        return padre

    figli = Interesse.objects.filter(
        nome=sottointeresse,
        padre=padre,
    )

    if figli.count() != 1:
        raise CommandError(
            f"Interesse assente o duplicato: "
            f"{categoria} > {sottointeresse} "
            f"(trovati {figli.count()})."
        )

    return figli.get()


def data_ora_locale(testo):
    """
    Trasforma la data testuale in un datetime
    con il fuso orario configurato in Django.
    """
    valore = datetime.strptime(
        testo,
        "%Y-%m-%d %H:%M",
    )

    return timezone.make_aware(
        valore,
        timezone.get_current_timezone(),
    )


# ============================================================
# MANAGEMENT COMMAND
# ============================================================

class Command(BaseCommand):

    help = (
        "Crea le 15 community e i 27 eventi demo "
        "senza modificare gli account esistenti."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--controlla",
            action="store_true",
            help="Verifica tutti i dati senza creare nulla.",
        )

    def handle(self, *args, **options):

        controlla = options["controlla"]

        cartella_foto = (
            Path(settings.BASE_DIR)
            / "dati_demo"
            / "foto_community"
        )

        self.stdout.write(
            "\n=== CONTROLLO DATASET COMMUNITY ==="
        )

        # ----------------------------------------
        # 1. CONTROLLO FOTOGRAFIE
        # ----------------------------------------

        if not cartella_foto.is_dir():
            raise CommandError(
                "Cartella foto_community non trovata: "
                f"{cartella_foto}"
            )

        fotografie = {}

        for dati in COMMUNITY_DEMO:
            numero = dati["numero"]
            fotografie[numero] = trova_fotografia(
                cartella_foto,
                numero,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "OK: tutte le 15 fotografie sono presenti."
            )
        )

        # ----------------------------------------
        # 2. CONTROLLO PROFILI
        # ----------------------------------------

        numeri_profili = set()

        for dati in COMMUNITY_DEMO:
            numeri_profili.add(dati["organizzatore"])
            numeri_profili.update(dati["membri"])

        profili = {}

        for numero in sorted(numeri_profili):
            username = username_demo(numero)

            try:
                profilo = Profilo.objects.select_related(
                    "user"
                ).get(user__username=username)
            except Profilo.DoesNotExist:
                raise CommandError(
                    f"Profilo richiesto non trovato: "
                    f"{username}"
                )

            profili[numero] = profilo

        self.stdout.write(
            self.style.SUCCESS(
                "OK: tutti i profili necessari esistono."
            )
        )

        # ----------------------------------------
        # 3. CONTROLLO DATI COMMUNITY
        # ----------------------------------------

        numeri_community = [
            dati["numero"] for dati in COMMUNITY_DEMO
        ]

        if sorted(numeri_community) != list(range(1, 16)):
            raise CommandError(
                "Le community devono essere 15, "
                "numerate da 1 a 15 senza duplicati."
            )

        interessi_community = {}

        for dati in COMMUNITY_DEMO:
            numero = dati["numero"]

            if len(dati["titolo"]) > 100:
                raise CommandError(
                    f"Titolo troppo lungo: community #{numero}"
                )

            if not dati["descrizione"] or len(
                dati["descrizione"]
            ) > 1000:
                raise CommandError(
                    f"Descrizione non valida: community #{numero}"
                )

            if len(dati["citta"]) > 100:
                raise CommandError(
                    f"Città troppo lunga: community #{numero}"
                )

            organizzatore = dati["organizzatore"]

            if organizzatore not in dati["membri"]:
                raise CommandError(
                    f"L'organizzatore della community "
                    f"#{numero} deve essere anche membro."
                )

            if len(set(dati["membri"])) != len(
                dati["membri"]
            ):
                raise CommandError(
                    f"Membri duplicati: community #{numero}"
                )

            if (
                profili[organizzatore].citta.casefold()
                != dati["citta"].casefold()
            ):
                raise CommandError(
                    f"La città della community #{numero} "
                    "non coincide con quella "
                    "dell'organizzatore."
                )

            interessi = []

            for categoria, sottointeresse in dati["interessi"]:
                interesse = trova_interesse(
                    categoria,
                    sottointeresse,
                )

                if interesse not in interessi:
                    interessi.append(interesse)

            interessi_community[numero] = interessi

        self.stdout.write(
            self.style.SUCCESS(
                "OK: organizzatori, città, membri "
                "e interessi sono coerenti."
            )
        )

        # ----------------------------------------
        # 4. CONTROLLO EVENTI
        # ----------------------------------------

        eventi_preparati = []
        chiavi_eventi = set()

        for dati in EVENTI_DEMO:

            numero = dati["comunita"]

            if numero not in numeri_community:
                raise CommandError(
                    f"Evento associato a community "
                    f"inesistente: #{numero}"
                )

            chiave = (
                numero,
                dati["titolo"],
            )

            if chiave in chiavi_eventi:
                raise CommandError(
                    f"Evento duplicato nel dataset: "
                    f"{dati['titolo']}"
                )

            chiavi_eventi.add(chiave)

            if len(dati["titolo"]) > 100:
                raise CommandError(
                    f"Titolo evento troppo lungo: "
                    f"{dati['titolo']}"
                )

            if len(dati["descrizione"]) > 1000:
                raise CommandError(
                    f"Descrizione evento troppo lunga: "
                    f"{dati['titolo']}"
                )

            if not dati["luogo"] or len(
                dati["luogo"]
            ) > 200:
                raise CommandError(
                    f"Luogo non valido: {dati['titolo']}"
                )

            if len(dati["cosa_portare"]) > 500:
                raise CommandError(
                    f"Cosa portare troppo lungo: "
                    f"{dati['titolo']}"
                )

            inizio = data_ora_locale(dati["inizio"])
            fine = data_ora_locale(dati["fine"])
            costo = Decimal(dati["costo"])

            if fine <= inizio:
                raise CommandError(
                    f"Date non valide: {dati['titolo']}"
                )

            if costo < Decimal("0.00"):
                raise CommandError(
                    f"Costo negativo: {dati['titolo']}"
                )

            if inizio < timezone.now():
                raise CommandError(
                    f"Evento già nel passato: "
                    f"{dati['titolo']}. "
                    "Aggiorna le date nel dataset "
                    "prima di creare nuovi eventi."
                )

            eventi_preparati.append({
                **dati,
                "inizio_dt": inizio,
                "fine_dt": fine,
                "costo_decimal": costo,
            })

        if len(eventi_preparati) != 27:
            raise CommandError(
                "Il dataset deve contenere 27 eventi."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "OK: tutti i 27 eventi sono validi."
            )
        )

        # ----------------------------------------
        # 5. CONTROLLO DATI GIÀ ESISTENTI
        # ----------------------------------------

        community_esistenti = {}

        for dati in COMMUNITY_DEMO:

            numero = dati["numero"]

            trovate = list(
                Community.objects.filter(
                    titolo=dati["titolo"],
                )
            )

            if len(trovate) > 1:
                raise CommandError(
                    f"Esistono più community con titolo "
                    f"'{dati['titolo']}'. "
                    "Controlla il database."
                )

            if trovate:
                esistente = trovate[0]

                if (
                    esistente.organizzatore_id
                    != profili[dati["organizzatore"]].pk
                ):
                    raise CommandError(
                        f"La community '{dati['titolo']}' "
                        "esiste già ma ha un organizzatore "
                        "diverso. Nessun dato modificato."
                    )

                community_esistenti[numero] = esistente

        self.stdout.write(
            self.style.SUCCESS(
                "OK: nessun conflitto con community esistenti."
            )
        )

        # ----------------------------------------
        # 6. SOLO CONTROLLO
        # ----------------------------------------

        if controlla:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nCONTROLLO COMPLETATO CON SUCCESSO!"
                    "\nNessun record è stato creato."
                )
            )
            return

        # ----------------------------------------
        # 7. CREAZIONE COMMUNITY ED EVENTI
        # ----------------------------------------

        create_community = 0
        community_gia_presenti = 0
        creati_eventi = 0
        eventi_gia_presenti = 0

        with transaction.atomic():

            community_salvate = {}

            for dati in COMMUNITY_DEMO:

                numero = dati["numero"]

                if numero in community_esistenti:

                    obj = community_esistenti[numero]
                    community_gia_presenti += 1

                    self.stdout.write(
                        f"[GIÀ PRESENTE] Community: "
                        f"{dati['titolo']}"
                    )

                else:

                    obj = Community(
                        titolo=dati["titolo"],
                        descrizione=dati["descrizione"],
                        organizzatore=profili[
                            dati["organizzatore"]
                        ],
                        citta=dati["citta"],
                    )

                    percorso = fotografie[numero]

                    with percorso.open("rb") as file_foto:
                        obj.immagine.save(
                            f"demo_community_{numero:02d}"
                            f"{percorso.suffix.lower()}",
                            File(file_foto),
                            save=False,
                        )

                    try:
                        obj.full_clean()
                    except ValidationError as errore:
                        raise CommandError(
                            f"Community #{numero} "
                            f"non valida: {errore}"
                        )

                    obj.save()
                    create_community += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[CREATA] Community: "
                            f"{dati['titolo']}"
                        )
                    )

                # Associa gli interessi e i membri
                # definiti nel dataset ufficiale.
                obj.interessi.set(
                    interessi_community[numero]
                )

                obj.membri.set([
                    profili[n] for n in dati["membri"]
                ])

                community_salvate[numero] = obj

            # ------------------------------------
            # CREAZIONE EVENTI
            # ------------------------------------

            for dati in eventi_preparati:

                obj_community = community_salvate[
                    dati["comunita"]
                ]

                esistente = Evento.objects.filter(
                    community=obj_community,
                    titolo=dati["titolo"],
                ).first()

                if esistente:
                    eventi_gia_presenti += 1

                    self.stdout.write(
                        f"[GIÀ PRESENTE] Evento: "
                        f"{dati['titolo']}"
                    )

                    continue

                nuovo_evento = Evento(
                    community=obj_community,
                    titolo=dati["titolo"],
                    descrizione=dati["descrizione"],
                    inizio=dati["inizio_dt"],
                    fine=dati["fine_dt"],
                    luogo=dati["luogo"],
                    costo=dati["costo_decimal"],
                    cosa_portare=dati["cosa_portare"],
                )

                try:
                    nuovo_evento.full_clean()
                except ValidationError as errore:
                    raise CommandError(
                        f"Evento '{dati['titolo']}' "
                        f"non valido: {errore}"
                    )

                nuovo_evento.save()
                creati_eventi += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"[CREATO] Evento: "
                        f"{dati['titolo']}"
                    )
                )

        # ----------------------------------------
        # RIEPILOGO
        # ----------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== POPOLAMENTO COMPLETATO ==="
            )
        )

        self.stdout.write(
            f"Community create: {create_community}"
        )

        self.stdout.write(
            f"Community già presenti: "
            f"{community_gia_presenti}"
        )

        self.stdout.write(
            f"Eventi creati: {creati_eventi}"
        )

        self.stdout.write(
            f"Eventi già presenti: {eventi_gia_presenti}"
        )

        self.stdout.write(
            "\nI 25 profili demo sono stati conservati."
        )
