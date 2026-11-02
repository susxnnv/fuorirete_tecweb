from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import json
from functools import lru_cache
from pathlib import Path
from django.conf import settings

from .models import Profilo, Interesse, Community, Evento

# AUTENTICAZIONE / PROFILO / PERMESSI

# Form per la registrazione dello User
class RegistrazioneForm(UserCreationForm):

    # aggiungiamo il campo email perchè lo avevo previsto 
    email = forms.EmailField(
        required=True,
        label='Email'
    )

    # class Meta configura il form
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    # controllo di unicità della mail 
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'Esiste già un account con questa email.'
            )

        return email

# Utile per CreazioneProfiloForm
# LETTURA DELLE CITTÀ ITALIANE --> validazione delle città tramite JSON
@lru_cache(maxsize=1)
def carica_citta():
    percorso = Path(settings.BASE_DIR) / 'gestione' / 'data' / 'citta_italiane.json'

    with open(percorso, encoding='utf-8') as file:
        citta = json.load(file)

    return {
        nome.casefold(): nome for nome in citta
    }


# Form per la creazione del profilo
class CreazioneProfiloForm(forms.ModelForm):

    # abbiamo definito a mano 2 campi perchè sono scelti fra diversi valori
    lingue = forms.MultipleChoiceField(
        label='Lingue parlate',
        choices=[
            (lingua, lingua)
            for lingua in Profilo.LINGUE_DISPONIBILI
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    cosa_cerca = forms.MultipleChoiceField(
        label='Cosa cerchi?',
        choices=[
            ('AMICIZIE', 'Amicizie'),
            ('COMPAGNO_STUDIO', 'Compagno di studio'),
            ('COINQUILINO', 'Coinquilino'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Profilo

        fields = [
            'nome',
            'foto',
            'data_nascita',
            'genere',
            'citta',
            'occupazione',
            'lingue',
            'descrizione',
            'cosa_cerca',
        ]

        labels = {
            'nome': 'Nome',
            'foto': 'Foto del profilo',
            'data_nascita': 'Data di nascita',
            'genere': 'Genere',
            'citta': 'Città',
            'occupazione': 'Occupazione',
            'descrizione': 'Descrizione',
        }

        widgets = {
            'data_nascita': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'descrizione': forms.Textarea(
                attrs={'rows': 4}
            ),
            'citta': forms.TextInput(
                attrs={'placeholder': 'Es. Modena'}
            ),
        }

    # verifica che la città inserita sia presente nell'elenco JSON
    def clean_citta(self):
        citta = self.cleaned_data['citta'].strip()

        try:
            citta_disponibili = carica_citta()
        except (OSError, ValueError, TypeError):
            raise forms.ValidationError(
                'Elenco delle città non disponibile.'
            )

        citta_ufficiale = citta_disponibili.get(citta.casefold())

        if citta_ufficiale is None:
            raise forms.ValidationError(
                'Inserisci una città valida tra quelle disponibili.'
            )

        return citta_ufficiale

    # verifica che abbiamo selezionato da 1 - 4 lingue e che non inviamo valori duplicati
    def clean_lingue(self):
        lingue = self.cleaned_data['lingue']

        if not 1 <= len(lingue) <= 4:
            raise forms.ValidationError(
                'Devi selezionare da 1 a 4 lingue.'
            )

        if len(lingue) != len(set(lingue)):
            raise forms.ValidationError(
                'Non puoi selezionare lingue duplicate.'
            )

        return lingue

    # verifica che abbiamo selezionato da 1 - 3 cose e che non inviamo valori duplicati
    def clean_cosa_cerca(self):
        scelte = self.cleaned_data['cosa_cerca']

        if not 1 <= len(scelte) <= 3:
            raise forms.ValidationError(
                'Devi selezionare da 1 a 3 opzioni.'
            )

        if len(scelte) != len(set(scelte)):
            raise forms.ValidationError(
                'Non puoi selezionare opzioni duplicate.'
            )

        return scelte


# Form per la selezione degli interessi
class SelezioneInteressiForm(forms.Form):

    interessi = forms.ModelMultipleChoiceField(
        queryset=Interesse.objects.all(),
        required=True,
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            'required': 'Seleziona almeno un interesse.',
            'invalid_choice': 'Uno degli interessi selezionati non è valido.',
        }
    )

    # verifica dei vincoli per gli interessi
    def clean_interessi(self):

        interessi = self.cleaned_data['interessi']

        # Minimo 1, massimo 6 interessi
        if not 1 <= interessi.count() <= 6:
            raise forms.ValidationError(
                'Devi selezionare da 1 a 6 interessi.'
            )

        # Evitiamo la selezione contemporanea di una categoria e di un suo sottointeresse
        interessi_selezionati = list(interessi)
        ids_selezionati = {
            interesse.pk
            for interesse in interessi_selezionati
        }

        for interesse in interessi_selezionati:

            if interesse.padre_id in ids_selezionati:
                raise forms.ValidationError(
                    'Non puoi selezionare una categoria '
                    'e una sua sottocategoria contemporaneamente.'
                )

        return interessi


# ==========================================
# CREAZIONE E MODIFICA COMMUNITY
# ==========================================

class CreazioneCommunityForm(forms.ModelForm):

    class Meta:

        model = Community

        fields = [
            'titolo',
            'descrizione',
            'immagine',
            'citta',
        ]

        labels = {
            'titolo': 'Nome della community',
            'descrizione': 'Descrizione',
            'immagine': 'Immagine della community',
            'citta': 'Città',
        }

        widgets = {
            'titolo': forms.TextInput(
                attrs={
                    'placeholder': 'Es. Trekking nel weekend'
                }
            ),
            'descrizione': forms.Textarea(
                attrs={
                    'rows': 5,
                    'placeholder': (
                        'Racconta di cosa si occupa '
                        'la tua community...'
                    ),
                }
            ),
            'citta': forms.TextInput(
                attrs={
                    'placeholder': 'Es. Modena'
                }
            ),
        }

    def clean_titolo(self):

        titolo = self.cleaned_data['titolo'].strip()

        if not titolo:
            raise forms.ValidationError(
                'Inserisci il nome della community.'
            )

        return titolo

    def clean_descrizione(self):

        descrizione = self.cleaned_data['descrizione'].strip()

        if not descrizione:
            raise forms.ValidationError(
                'Inserisci una descrizione.'
            )

        return descrizione

    def clean_citta(self):

        citta = self.cleaned_data['citta'].strip()

        try:
            citta_disponibili = carica_citta()
        except (OSError, ValueError, TypeError):
            raise forms.ValidationError(
                'Elenco delle città non disponibile.'
            )

        citta_ufficiale = citta_disponibili.get(
            citta.casefold()
        )

        if citta_ufficiale is None:
            raise forms.ValidationError(
                'Inserisci una città valida '
                'tra quelle disponibili.'
            )

        return citta_ufficiale


# ==========================================
# FORM CREAZIONE E MODIFICA EVENTO
# ==========================================

class EventoForm(forms.ModelForm):

    class Meta:

        model = Evento

        fields = [
            'titolo',
            'descrizione',
            'inizio',
            'fine',
            'luogo',
            'costo',
            'cosa_portare',
        ]

        labels = {
            'titolo': 'Titolo',
            'descrizione': 'Descrizione',
            'inizio': 'Data e ora di inizio',
            'fine': 'Data e ora di fine',
            'luogo': 'Luogo',
            'costo': 'Costo (€)',
            'cosa_portare': 'Cosa portare',
        }

        widgets = {

            'titolo': forms.TextInput(attrs={
                'placeholder': 'Es. Aperitivo in centro'
            }),

            'descrizione': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': (
                    'Descrivi brevemente '
                    'l’attività organizzata...'
                )
            }),

            'inizio': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'fine': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'luogo': forms.TextInput(attrs={
                'placeholder': 'Es. Piazza Grande, Modena'
            }),

            'costo': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
                'placeholder': '0.00'
            }),

            'cosa_portare': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': (
                    'Es. Scarpe comode, acqua...'
                )
            }),
        }

    def clean_titolo(self):

        titolo = self.cleaned_data['titolo'].strip()

        if not titolo:
            raise forms.ValidationError(
                'Inserisci il titolo dell’evento.'
            )

        return titolo

    def clean_luogo(self):

        luogo = self.cleaned_data['luogo'].strip()

        if not luogo:
            raise forms.ValidationError(
                'Inserisci il luogo dell’evento.'
            )

        return luogo
