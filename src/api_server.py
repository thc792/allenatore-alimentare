# src/api_server.py

from flask import Flask, render_template, jsonify, request 

# --- BLOCCO IMPORT PER search_products_by_name (come prima) ---
import sys
import os
PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DIR)
try:
    from src.integrations.openfoodfacts_client import search_products_by_name
    print("INFO: 'search_products_by_name' importato con successo da src.integrations.openfoodfacts_client")
except ModuleNotFoundError as e:
    print(f"ERRORE CRITICO: ModuleNotFoundError durante l'import di search_products_by_name: {e}")
    search_products_by_name = None 
except ImportError as e:
    print(f"ERRORE CRITICO: ImportError durante l'import di search_products_by_name: {e}")
    search_products_by_name = None
# --- FINE BLOCCO IMPORT ---

# --- NUOVO BLOCCO IMPORT PER gemini_service ---
try:
    from src.integrations.gemini_service import get_nutritional_advice_from_gemini
    print("INFO: 'get_nutritional_advice_from_gemini' importato con successo da src.integrations.gemini_service")
except ModuleNotFoundError as e:
    print(f"ERRORE CRITICO: ModuleNotFoundError durante l'import di get_nutritional_advice_from_gemini: {e}")
    print(f"PROJECT_ROOT_DIR aggiunto a sys.path: {PROJECT_ROOT_DIR}") # Debug aggiunto
    print(f"sys.path attuale: {sys.path}") # Debug aggiunto
    get_nutritional_advice_from_gemini = None
except ImportError as e:
    print(f"ERRORE CRITICO: ImportError durante l'import di get_nutritional_advice_from_gemini: {e}")
    print(f"PROJECT_ROOT_DIR aggiunto a sys.path: {PROJECT_ROOT_DIR}") # Debug aggiunto
    print(f"sys.path attuale: {sys.path}") # Debug aggiunto
    get_nutritional_advice_from_gemini = None
# --- FINE NUOVO BLOCCO IMPORT ---


app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index_page():
    return render_template('index.html', message="Benvenuto nel tuo Allenatore Alimentare!")

@app.route('/api/search_food', methods=['GET'])
def api_search_food():
    search_query = request.args.get('query', '') 
    if not search_query:
        return jsonify({"error": "La query di ricerca non può essere vuota"}), 400
    if search_products_by_name is None:
        return jsonify({"error": "Servizio di ricerca prodotti non disponibile (import fallito)."}), 500
    print(f"API: Ricevuta ricerca per: '{search_query}'")
    results = search_products_by_name(query=search_query, page_size=10, lang="it")
    if results is None:
        print(f"API: Errore cercando '{search_query}' con OpenFoodFacts.")
        return jsonify({"error": "Errore comunicazione database alimentare esterno"}), 500
    print(f"API: Trovati {len(results)} risultati per '{search_query}'.")
    return jsonify(results)

# --- ENDPOINT CALCOLO FABBISOGNO MODIFICATO PER USARE GEMINI ---
@app.route('/api/calculate_needs', methods=['POST'])
def api_calculate_needs():
    if not request.is_json:
        return jsonify({"error": "Richiesta deve essere JSON"}), 400

    user_data = request.get_json()
    print(f"API: Ricevuti dati utente per calcolo fabbisogno: {user_data}")

    # Controlla se la funzione di Gemini è stata importata correttamente
    if get_nutritional_advice_from_gemini is None:
        # Questo succede se l'import iniziale è fallito
        print("API ERRORE: La funzione 'get_nutritional_advice_from_gemini' non è disponibile (import fallito).")
        return jsonify({"error": "Servizio di consulenza nutrizionale non disponibile (configurazione interna)."}), 500

    # Chiama la funzione del servizio Gemini
    print("API: Chiamata a get_nutritional_advice_from_gemini in corso...")
    advice = get_nutritional_advice_from_gemini(user_data)

    if advice is None:
        # Questo potrebbe accadere se c'è un errore non gestito internamente in get_nutritional_advice_from_gemini
        # o se la funzione è stata definita per restituire None in certi casi di errore non API.
        print("API ERRORE: la funzione get_nutritional_advice_from_gemini ha restituito None inaspettatamente.")
        return jsonify({"error": "Errore imprevisto durante l'elaborazione della richiesta di consulenza nutrizionale."}), 500
    
    # Se 'advice' contiene una chiave 'error' (come definito in gemini_service.py)
    if isinstance(advice, dict) and "error" in advice:
        print(f"API: Errore ricevuto da gemini_service: {advice['error']}")
        # Restituiamo 503 Service Unavailable se l'errore proviene dal servizio Gemini
        # o se la chiave API non è configurata.
        return jsonify(advice), 503 

    print(f"API: Consiglio da Gemini ricevuto: {advice}")
    return jsonify(advice)
# --- FINE ENDPOINT MODIFICATO ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)