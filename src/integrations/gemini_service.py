# src/integrations/gemini_service.py

import google.generativeai as genai
import os
import json # Importa json per il parsing e per il test

# --- CONFIGURAZIONE CHIAVE API ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

gemini_sdk_configured = False
if not GEMINI_API_KEY:
    print("ATTENZIONE: La variabile d'ambiente GEMINI_API_KEY non è impostata.")
    print("Il servizio Gemini non funzionerà senza una chiave API valida.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_sdk_configured = True
        print("INFO: SDK Gemini configurato con successo.")
    except Exception as e:
        print(f"ERRORE: Configurazione SDK Gemini fallita: {e}")
        # gemini_sdk_configured rimane False

MODEL_NAME = "gemini-1.5-flash-latest"

def get_nutritional_advice_from_gemini(user_data: dict) -> dict: # Modificato per restituire sempre un dict
    """
    Invia i dati dell'utente a Gemini per ottenere consigli nutrizionali.

    Args:
        user_data (dict): Dati dell'utente.

    Returns:
        dict: Un dizionario con i consigli o un dizionario di errore.
    """
    if not gemini_sdk_configured: # Controlla se la configurazione è andata a buon fine
        error_message = "Servizio Gemini non disponibile (configurazione SDK fallita o API Key mancante)."
        print(f"ERRORE in get_nutritional_advice_from_gemini: {error_message}")
        return {"error": error_message}

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Sanificazione e preparazione dei dati utente per il prompt
        # Assicuriamoci che i valori siano presenti e abbiano un fallback 'N/D' (Non Disponibile)
        age = user_data.get('age', 'N/D')
        weight = user_data.get('weight', 'N/D')
        height = user_data.get('height', 'N/D')
        gender = user_data.get('gender', 'N/D')
        activity_level_key = user_data.get('activity_level', 'N/D')
        profession = user_data.get('profession', 'Nessuna professione specificata')
        objectives = user_data.get('objectives', 'N/D')

        # Mappatura dei livelli di attività per renderli più comprensibili a Gemini (opzionale, ma può aiutare)
        activity_level_map = {
            "sedentary": "Sedentario (poco o nessun esercizio)",
            "light": "Leggermente attivo (esercizio leggero/sport 1-3 giorni/sett.)",
            "moderate": "Moderatamente attivo (esercizio moderato/sport 3-5 giorni/sett.)",
            "active": "Molto attivo (esercizio intenso/sport 6-7 giorni/sett.)",
            "extra_active": "Estremamente attivo (esercizio molto intenso/lavoro fisico)"
        }
        activity_level_description = activity_level_map.get(activity_level_key, activity_level_key)


        prompt_parts = [
            "Sei un esperto nutrizionista virtuale. Il tuo compito è analizzare i dati di un utente e fornire una stima del suo fabbisogno calorico giornaliero e una suddivisione consigliata dei macronutrienti (proteine, carboidrati, grassi) espressi in grammi.",
            "Considera tutti i parametri forniti per una stima il più accurata possibile.",
            "Fornisci anche una breve nota o un consiglio personalizzato basato sugli obiettivi dell'utente.",
            "\nDati Utente:",
            f"- Età: {age} anni",
            f"- Peso: {weight} kg",
            f"- Altezza: {height} cm",
            f"- Sesso Biologico: {gender}",
            f"- Livello di Attività Fisica: {activity_level_description}",
            f"- Dettaglio Attività/Professione: {profession}",
            f"- Obiettivi Principali: {objectives}",
            "\nISTRUZIONI PER LA RISPOSTA:",
            "Formatta la tua risposta ESCLUSIVAMENTE come un singolo oggetto JSON valido. Non includere spiegazioni testuali prima o dopo l'oggetto JSON, e non usare markdown (come ```json).",
            "L'oggetto JSON deve contenere le seguenti chiavi:",
            "  \"calories\": (numero intero, fabbisogno calorico giornaliero stimato in kcal),",
            "  \"protein\": (numero intero, grammi di proteine consigliati al giorno),",
            "  \"carbs\": (numero intero, grammi di carboidrati consigliati al giorno),",
            "  \"fat\": (numero intero, grammi di grassi consigliati al giorno),",
            "  \"notes\": (stringa di testo, una breve nota o consiglio pertinente, massimo 2-3 frasi).",
            "\nEsempio di output JSON atteso:",
            "{\"calories\": 2200, \"protein\": 110, \"carbs\": 275, \"fat\": 73, \"notes\": \"Considerando il tuo obiettivo di mantenimento e il livello di attività moderato, questo apporto dovrebbe essere adeguato. Monitora il tuo peso e aggiusta le calorie se necessario.\"}"
        ]
        prompt = "\n".join(prompt_parts)
        
        print(f"\n--- PROMPT INVIATO A GEMINI ({MODEL_NAME}) ---")
        print(prompt)
        print("---------------------------------------\n")

        # Configurazione della generazione per richiedere output JSON (se il modello lo supporta direttamente)
        # Per gemini-1.5-flash-latest, specificare response_mime_type è il modo migliore
        generation_config = genai.types.GenerationConfig(
            # candidate_count=1, # Solitamente non necessario per JSON
            # temperature=0.7, # Puoi sperimentare con la temperatura
            response_mime_type="application/json" # Richiede esplicitamente JSON
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        response_text = response.text # Con response_mime_type="application/json", il testo dovrebbe già essere JSON valido
        
        print(f"--- RISPOSTA GREZZA (già JSON) DA GEMINI ({MODEL_NAME}) ---")
        print(response_text)
        print("----------------------------------------\n")

        try:
            advice = json.loads(response_text)
            # Validazione minima del JSON ricevuto
            required_keys = ["calories", "protein", "carbs", "fat", "notes"]
            if not all(key in advice for key in required_keys):
                print("ERRORE: Il JSON da Gemini non contiene tutte le chiavi richieste.")
                return {"error": "Formato risposta da Gemini non valido."}
            return advice
        except json.JSONDecodeError as json_e:
            print(f"ERRORE: Impossibile decodificare la risposta JSON da Gemini: {json_e}")
            print(f"Testo ricevuto che ha causato l'errore: '{response_text}'")
            return {"error": "Risposta da Gemini non è un JSON valido."}

    except Exception as e:
        print(f"ERRORE durante la comunicazione con Gemini API o nell'elaborazione: {e}")
        # Restituisci un dizionario di errore che il server API può inoltrare
        error_detail = str(e)
        # A volte gli errori di gRPC sono lunghi, potremmo volerli troncare o semplificare
        if "DEADLINE_EXCEEDED" in error_detail:
            error_detail = "Timeout durante la comunicazione con Gemini."
        elif "_InactiveRpcError" in error_detail:
             error_detail = "Problema di comunicazione con i server Gemini. Riprova più tardi."

        return {"error": f"Errore nell'interazione con il servizio di IA: {error_detail}"}


if __name__ == '__main__':
    if not GEMINI_API_KEY:
        print("Per eseguire il test di gemini_service.py, imposta la variabile d'ambiente GEMINI_API_KEY.")
    else:
        if not gemini_sdk_configured:
            print("Configurazione SDK Gemini fallita. Impossibile eseguire il test.")
        else:
            print("\n--- Test di gemini_service.py ---")
            test_user_data = {
                "age": "46",
                "weight": "70",
                "height": "170",
                "gender": "male",
                "activity_level": "light", # Chiave come inviata dal form
                "profession": "commerciante",
                "objectives": "perdere peso gradualmente"
            }
            print(f"Invio dati di test a Gemini: {test_user_data}")
            advice = get_nutritional_advice_from_gemini(test_user_data)
            
            print("\nConsiglio ricevuto da Gemini (formattato):")
            print(json.dumps(advice, indent=2, ensure_ascii=False))