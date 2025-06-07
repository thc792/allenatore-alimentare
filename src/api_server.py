# src/api_server.py

import os
import traceback # Per debugging più dettagliato degli errori
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS # Necessario se il frontend e backend sono su porte/domini diversi in sviluppo

# Importa i tuoi moduli personalizzati
from integrations import openfoodfacts_client
from integrations import gemini_service # Assumendo che le modifiche siano qui

# Inizializzazione dell'applicazione Flask
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configurazione CORS - Utile per lo sviluppo locale se frontend e backend sono su porte diverse.
# Per Vercel, potrebbe non essere strettamente necessario se tutto è servito dallo stesso dominio,
# ma è una buona pratica averlo per flessibilità.
CORS(app, resources={r"/api/*": {"origins": "*"}}) # Permette richieste da qualsiasi origine per gli endpoint API

# ----- Configurazione per servire i file statici e l'index.html -----

@app.route('/')
def index():
    """Serve la pagina principale index.html."""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serve file statici (CSS, JS, immagini) dalla cartella static."""
    return send_from_directory(app.static_folder, path)

# ----- API Endpoints -----

@app.route('/api/search_food', methods=['GET'])
def search_food_api():
    """
    Endpoint per cercare alimenti tramite Open Food Facts.
    Accetta 'query' o 'barcode' come parametri GET.
    """
    query = request.args.get('query')
    barcode = request.args.get('barcode')

    if not query and not barcode:
        return jsonify({"error": "Parametro 'query' o 'barcode' mancante."}), 400

    try:
        if barcode:
            # print(f"DEBUG: Ricerca per barcode: {barcode}")
            results = openfoodfacts_client.search_product_by_barcode(barcode)
        else:
            # print(f"DEBUG: Ricerca per query: {query}")
            results = openfoodfacts_client.search_products_by_name(query)
        
        # print(f"DEBUG: Risultati da OpenFoodFacts: {results}")
        if "error" in results:
            return jsonify(results), 500 # Se il client restituisce un errore interno
        return jsonify(results)
    except Exception as e:
        # print(f"ERRORE in /api/search_food: {str(e)}")
        # traceback.print_exc()
        return jsonify({"error": "Errore durante la ricerca dell'alimento.", "details": str(e)}), 500

@app.route('/api/calculate_needs', methods=['POST'])
def calculate_needs_api():
    """
    Endpoint per calcolare il fabbisogno nutrizionale utilizzando Gemini.
    Riceve i dati dell'utente in formato JSON.
    """
    try:
        user_data = request.json
        # print(f"DEBUG: Dati ricevuti dal frontend per calcolo fabbisogno: {user_data}")

        # Estrazione dei dati obbligatori
        age = user_data.get('age')
        weight = user_data.get('weight')
        height = user_data.get('height')
        gender = user_data.get('gender')
        activity_level = user_data.get('activity_level')
        goals = user_data.get('goals')

        # Estrazione dei dati opzionali (con default a stringa vuota se non forniti)
        profession = user_data.get('profession', '')
        medical_conditions = user_data.get('medical_conditions', '').strip()
        food_allergies = user_data.get('food_allergies', '').strip()
        food_intolerances = user_data.get('food_intolerances', '').strip()

        # Validazione base dei dati obbligatori
        required_fields = {
            "età (age)": age, "peso (weight)": weight, "altezza (height)": height,
            "sesso (gender)": gender, "livello di attività (activity_level)": activity_level,
            "obiettivi (goals)": goals
        }
        missing_fields = [name for name, value in required_fields.items() if not value]
        if missing_fields:
            return jsonify({"error": f"Dati utente incompleti. Campi mancanti: {', '.join(missing_fields)}"}), 400

        # Chiamata al servizio Gemini con tutti i dati, inclusi quelli opzionali
        advice = gemini_service.get_nutritional_advice_from_gemini(
            age=age,
            weight=weight,
            height=height,
            gender=gender,
            activity_level=activity_level,
            profession=profession,
            goals=goals,
            medical_conditions=medical_conditions,
            food_allergies=food_allergies,
            food_intolerances=food_intolerances
        )
        
        # print(f"DEBUG: Risposta da gemini_service.get_nutritional_advice_from_gemini: {advice}")
        
        if "error" in advice:
            # Se gemini_service restituisce un errore, propagalo con uno status code appropriato
            # (assumendo che il servizio possa impostare 'status_code' nel dizionario di errore)
            status_code = advice.get("status_code", 500) # Default a 500 se non specificato
            return jsonify(advice), status_code
            
        return jsonify(advice)

    except TypeError as e: # Potrebbe accadere se request.json è None (es. Content-Type non corretto)
        # print(f"ERRORE in /api/calculate_needs (TypeError): {str(e)}")
        # traceback.print_exc()
        return jsonify({"error": "Dati non validi o mancanti nella richiesta. Assicurati che Content-Type sia application/json.", "details": str(e)}), 400
    except Exception as e:
        # print(f"ERRORE in /api/calculate_needs (Exception generica): {str(e)}")
        # traceback.print_exc()
        return jsonify({"error": "Errore interno del server durante il calcolo del fabbisogno.", "details": str(e)}), 500

# ----- Per l'esecuzione locale -----

if __name__ == '__main__':
    # Caricamento della API Key di Gemini dalle variabili d'ambiente
    # (gemini_service.py dovrebbe già gestire la configurazione di genai)
    if not os.environ.get("GEMINI_API_KEY"):
        print("ATTENZIONE: La variabile d'ambiente GEMINI_API_KEY non è impostata.")
        print("Il servizio Gemini potrebbe non funzionare correttamente.")

    # Esegui l'app Flask in modalità debug per lo sviluppo locale
    # Host '0.0.0.0' la rende accessibile da altre macchine nella stessa rete
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)