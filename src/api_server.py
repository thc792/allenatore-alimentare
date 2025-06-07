import google.generativeai as genai
import os
import json

# Carica la chiave API di Gemini dalla variabile d'ambiente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_nutritional_advice_from_gemini(user_data):
    """
    Ottiene consigli nutrizionali personalizzati da Gemini, includendo fabbisogno
    calorico, macronutrienti e consigli aggiuntivi basati sui dati dell'utente.

    Args:
        user_data (dict): Un dizionario contenente i dati dell'utente:
            'age': età in anni (int)
            'weight': peso in kg (float)
            'height': altezza in cm (int)
            'gender': sesso biologico ('male' o 'female') (str)
            'activity_level': livello di attività fisica (str da una lista predefinita)
            'profession': professione (str, opzionale)
            'objectives': obiettivi (str, es. "perdere peso", "mantenimento", "aumentare massa muscolare")
            'medical_conditions': eventuali malattie o condizioni mediche (str, opzionale)
            'allergies': allergie alimentari note (str, opzionale)
            'intolerances': intolleranze alimentari note (str, opzionale)
            # Potremmo aggiungere altri campi qui in futuro (food_likes, food_dislikes, ecc.)

    Returns:
        dict: Un dizionario contenente 'calories', 'protein', 'carbs', 'fat', 
              e una nuova chiave 'personalized_advice' (lista di stringhe o stringa unica),
              oppure un dizionario con una chiave 'error' se si verifica un problema.
    """
    if not GEMINI_API_KEY:
        print("ERRORE FATALE in gemini_service: GEMINI_API_KEY non trovata nelle variabili d'ambiente.")
        return {"error": "Configurazione del servizio AI mancante (chiave API non impostata)."}

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Configurazione del modello
        generation_config = {
            "temperature": 0.7, # Un po' di creatività ma non troppa per dati numerici/consigli
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192, # Aumentato per consentire output più lunghi con i consigli
            "response_mime_type": "application/json",
        }
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest", # o un altro modello se preferisci
            safety_settings=safety_settings,
            generation_config=generation_config
        )

        # --- COSTRUZIONE DEL PROMPT MIGLIORATA ---
        prompt_parts = [
            "Sei un esperto nutrizionista e consulente del benessere. Il tuo compito è analizzare i dati di un utente e fornire una stima del suo fabbisogno calorico giornaliero e dei macronutrienti (proteine, carboidrati, grassi in grammi), insieme a 2-3 consigli personalizzati utili e pratici.",
            "Considera attentamente tutti i seguenti dati dell'utente:",
            f"- Età: {user_data.get('age', 'Non specificata')} anni",
            f"- Peso: {user_data.get('weight', 'Non specificato')} kg",
            f"- Altezza: {user_data.get('height', 'Non specificata')} cm",
            f"- Sesso Biologico: {user_data.get('gender', 'Non specificato')}",
            f"- Livello di Attività Fisica: {user_data.get('activity_level', 'Non specificato')}",
            f"- Professione: {user_data.get('profession', 'Non specificata')}",
            f"- Obiettivi Principali: {user_data.get('objectives', 'Non specificati')}",
        ]

        # Aggiungi informazioni opzionali solo se fornite
        if user_data.get('medical_conditions'):
            prompt_parts.append(f"- Condizioni Mediche Rilevanti: {user_data['medical_conditions']}")
        if user_data.get('allergies'):
            prompt_parts.append(f"- Allergie Alimentari: {user_data['allergies']}")
        if user_data.get('intolerances'):
            prompt_parts.append(f"- Intolleranze Alimentari: {user_data['intolerances']}")
        
        prompt_parts.extend([
            "\nBasandoti su questi dati:",
            "1. Fornisci una stima del fabbisogno calorico giornaliero (in kcal).",
            "2. Fornisci una stima del fabbisogno di proteine (in grammi).",
            "3. Fornisci una stima del fabbisogno di carboidrati (in grammi).",
            "4. Fornisci una stima del fabbisogno di grassi (in grammi).",
            "5. Fornisci una breve nota o disclaimer generale sulla stima (es. 'Questa è una stima generale. Consulta un professionista...').",
            "6. Offri 2-3 consigli personalizzati, brevi e pratici, basati sugli obiettivi, il livello di attività, la professione, e soprattutto tenendo conto di eventuali condizioni mediche, allergie o intolleranze menzionate. I consigli devono essere sicuri e non sostituire pareri medici specifici. Ad esempio, se l'utente ha il diabete, un consiglio potrebbe riguardare la gestione dei carboidrati; se ha un lavoro sedentario, un consiglio potrebbe essere sull'attività fisica.",
            "\nPer favore, formatta la tua risposta ESCLUSIVAMENTE come un oggetto JSON con le seguenti chiavi:",
            "- 'calories': (numero, fabbisogno calorico stimato)",
            "- 'protein': (numero, grammi di proteine stimate)",
            "- 'carbs': (numero, grammi di carboidrati stimati)",
            "- 'fat': (numero, grammi di grassi stimati)",
            "- 'notes': (stringa, la breve nota o disclaimer)",
            "- 'personalized_advice': (lista di stringhe, dove ogni stringa è un consiglio personalizzato)",
            "\nEsempio di struttura JSON attesa (i valori sono solo esempi):",
            """
            {
              "calories": 2200,
              "protein": 130,
              "carbs": 250,
              "fat": 70,
              "notes": "Questa è una stima generale del tuo fabbisogno. Per un piano personalizzato, consulta un nutrizionista o un dietologo.",
              "personalized_advice": [
                "Dato il tuo obiettivo di perdita peso e il tuo livello di attività leggero, prova ad aumentare gradualmente l'intensità o la frequenza dei tuoi allenamenti.",
                "Considerando la tua intolleranza al lattosio, esplora alternative vegetali al latte e formaggi, o usa prodotti delattosati.",
                "Per il tuo lavoro d'ufficio, cerca di fare brevi pause attive ogni ora per contrastare la sedentarietà."
              ]
            }
            """
        ])

        print(f"\n--- PROMPT INVIATO A GEMINI (per calcolo fabbisogno e consigli) ---")
        # Stampa il prompt solo se sei in un ambiente di debug e fai attenzione a dati sensibili
        # for part in prompt_parts:
        # print(part)
        # print("--------------------------------------------------------------------")

        response = model.generate_content(prompt_parts)
        
        # Debug della risposta grezza
        # print(f"RISPOSTA GREZZA DA GEMINI: {response.text}")

        # Verifica se la risposta contiene testo prima di tentare il parsing JSON
        if not response.text:
            print("ERRORE in gemini_service: Risposta vuota da Gemini.")
            return {"error": "Il servizio AI ha restituito una risposta vuota."}

        try:
            advice_data = json.loads(response.text)
            # Ulteriore validazione per assicurarsi che le chiavi attese siano presenti
            if not all(key in advice_data for key in ['calories', 'protein', 'carbs', 'fat', 'notes', 'personalized_advice']):
                print(f"ERRORE in gemini_service: Risposta JSON da Gemini non contiene tutte le chiavi attese. Ricevuto: {advice_data}")
                return {"error": "Formato della risposta AI non valido o incompleto."}
            if not isinstance(advice_data['personalized_advice'], list):
                print(f"ERRORE in gemini_service: 'personalized_advice' non è una lista. Ricevuto: {advice_data['personalized_advice']}")
                # Prova a gestirlo se è una singola stringa, o segnala errore
                if isinstance(advice_data['personalized_advice'], str):
                    advice_data['personalized_advice'] = [advice_data['personalized_advice']] # Converti in lista
                else:
                    return {"error": "Formato dei consigli personalizzati non valido."}

            return advice_data
        except json.JSONDecodeError as e:
            print(f"ERRORE in gemini_service: Impossibile fare il parsing JSON della risposta di Gemini: {e}")
            print(f"Risposta problematica: {response.text}")
            return {"error": "Errore nell'interpretazione della risposta dal servizio AI."}
        except Exception as e: # Cattura altre eccezioni generiche
            print(f"ERRORE GENERALE in gemini_service durante l'elaborazione della risposta: {e}")
            return {"error": f"Errore imprevisto nel servizio AI: {e}"}

    except AttributeError as e:
        print(f"ERRORE FATALE in gemini_service: Attributo non trovato, possibile problema con l'SDK Gemini o la configurazione del modello: {e}")
        return {"error": "Servizio AI non configurato correttamente (errore SDK)."}
    except Exception as e:
        print(f"ERRORE IMPREVISTO in gemini_service: {e}")
        # Controlla se l'errore è dovuto a una chiave API non valida
        if "API Key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
            print("ERRORE: Chiave API Gemini non valida o permessi mancanti.")
            return {"error": "Servizio Gemini non disponibile (configurazione SDK fallita o API Key mancante)."}
        return {"error": f"Si è verificato un errore con il servizio AI: {e}"}

# Esempio di utilizzo (per test locali, se necessario)
if __name__ == '__main__':
    print("Avvio test locale di gemini_service.py...")
    if not GEMINI_API_KEY:
        print("Imposta la variabile d'ambiente GEMINI_API_KEY per eseguire il test.")
    else:
        sample_user_data = {
            'age': 30,
            'weight': 70,
            'height': 175,
            'gender': 'male',
            'activity_level': 'moderate',
            'profession': 'impiegato',
            'objectives': 'mantenimento del peso e miglioramento forma fisica',
            'medical_conditions': 'leggero reflusso gastroesofageo',
            'allergies': 'polvere (non alimentare)',
            'intolerances': 'nessuna nota'
        }
        advice = get_nutritional_advice_from_gemini(sample_user_data)
        if advice:
            print("\n--- CONSIGLIO RICEVUTO DAL TEST ---")
            print(json.dumps(advice, indent=2, ensure_ascii=False))
            print("---------------------------------")
        else:
            print("Nessun consiglio ricevuto o errore durante il test.")