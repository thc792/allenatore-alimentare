# src/api_server.py

from flask import Flask, render_template, jsonify, request 

# --- BLOCCO IMPORT PER search_products_by_name ---
import sys
import os

# Calcola il percorso della root del progetto in modo robusto
# __file__ è il percorso di questo file (api_server.py)
# os.path.dirname(__file__) è la cartella 'src'
# os.path.dirname(os.path.dirname(__file__)) è la root del progetto 'allenatore-alimentare'
PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Aggiungi la root del progetto a sys.path se non è già presente
# Questo aiuta Python a trovare i moduli nella cartella 'src'
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DIR)

# Ora prova a importare i moduli
try:
    from src.integrations.openfoodfacts_client import search_products_by_name
    print("INFO (api_server): 'search_products_by_name' importato con successo.")
except ModuleNotFoundError:
    print("ERRORE CRITICO (api_server): Modulo 'src.integrations.openfoodfacts_client' o 'search_products_by_name' non trovato.")
    search_products_by_name = None 
except ImportError as e:
    print(f"ERRORE CRITICO (api_server): ImportError durante l'import di search_products_by_name: {e}")
    search_products_by_name = None
# --- FINE BLOCCO IMPORT ---

# --- NUOVO BLOCCO IMPORT PER gemini_service ---
try:
    from src.integrations.gemini_service import get_nutritional_advice_from_gemini
    print("INFO (api_server): 'get_nutritional_advice_from_gemini' importato con successo.")
except ModuleNotFoundError:
    print("ERRORE CRITICO (api_server): Modulo 'src.integrations.gemini_service' o 'get_nutritional_advice_from_gemini' non trovato.")
    get_nutritional_advice_from_gemini = None
except ImportError as e:
    print(f"ERRORE CRITICO (api_server): ImportError durante l'import di get_nutritional_advice_from_gemini: {e}")
    get_nutritional_advice_from_gemini = None
# --- FINE NUOVO BLOCCO IMPORT ---


# Inizializzazione dell'app Flask
# Flask cercherà 'templates' e 'static' RELATIVAMENTE ALLA POSIZIONE DI QUESTO FILE SORGENTE
# quindi se api_server.py è in 'src/', e 'templates' e 'static' sono nella root del progetto
# (un livello sopra 'src/'), i percorsi corretti sono '../templates' e '../static'.
app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index_page():
    # Questa rotta serve la pagina HTML principale.
    # Il messaggio può essere passato al template, se necessario.
    return render_template('index.html', message="Benvenuto nel tuo Allenatore Alimentare!")

@app.route('/api/search_food', methods=['GET'])
def api_search_food():
    search_query = request.args.get('query', '') 
    if not search_query:
        return jsonify({"error": "La query di ricerca non può essere vuota"}), 400
    
    if search_products_by_name is None:
        # Questo succede se l'import iniziale di search_products_by_name è fallito
        print("API ERRORE (api_search_food): La funzione 'search_products_by_name' non è disponibile.")
        return jsonify({"error": "Servizio di ricerca prodotti non disponibile (configurazione interna)."}), 500
    
    print(f"API (api_search_food): Ricevuta ricerca per: '{search_query}'")
    # Chiama la funzione per cercare prodotti, specificando un limite di risultati e la lingua
    results = search_products_by_name(query=search_query, page_size=10, lang="it")
    
    if results is None:
        # Questo potrebbe accadere se c'è un errore di rete o un problema con l'API di Open Food Facts
        print(f"API ERRORE (api_search_food): Errore cercando '{search_query}' con OpenFoodFacts.")
        return jsonify({"error": "Errore durante la comunicazione con il database alimentare esterno"}), 503 # 503 Service Unavailable
        
    print(f"API (api_search_food): Trovati {len(results)} risultati per '{search_query}'.")
    return jsonify(results)

@app.route('/api/calculate_needs', methods=['POST'])
def api_calculate_needs():
    if not request.is_json:
        return jsonify({"error": "La richiesta deve essere in formato JSON"}), 400

    user_data = request.get_json()
    if not user_data:
        return jsonify({"error": "Corpo della richiesta JSON mancante o vuoto"}), 400
        
    print(f"API (api_calculate_needs): Ricevuti dati utente per calcolo fabbisogno: {user_data}")

    if get_nutritional_advice_from_gemini is None:
        # Questo succede se l'import iniziale di get_nutritional_advice_from_gemini è fallito
        print("API ERRORE (api_calculate_needs): La funzione 'get_nutritional_advice_from_gemini' non è disponibile.")
        return jsonify({"error": "Servizio di consulenza nutrizionale non disponibile (configurazione interna)."}), 500

    print("API (api_calculate_needs): Chiamata a get_nutritional_advice_from_gemini in corso...")
    advice = get_nutritional_advice_from_gemini(user_data)

    if advice is None:
        # Questo potrebbe accadere se c'è un errore non gestito internamente in get_nutritional_advice_from_gemini
        print("API ERRORE (api_calculate_needs): la funzione get_nutritional_advice_from_gemini ha restituito None inaspettatamente.")
        return jsonify({"error": "Errore imprevisto durante l'elaborazione della richiesta di consulenza nutrizionale."}), 500
    
    if isinstance(advice, dict) and "error" in advice:
        # Errore specifico restituito da gemini_service (es. API Key mancante, errore API Gemini)
        print(f"API (api_calculate_needs): Errore ricevuto da gemini_service: {advice['error']}")
        # Usiamo 503 Service Unavailable se il problema è con il servizio esterno (Gemini)
        # o una configurazione critica mancante come la chiave API.
        status_code = 503 if "API Key" in advice["error"] or "servizio AI" in advice["error"].lower() else 500
        return jsonify(advice), status_code

    print(f"API (api_calculate_needs): Consiglio da Gemini ricevuto: {advice}")
    return jsonify(advice)

# Questo blocco viene eseguito solo se lo script api_server.py è il file principale eseguito
# (cioè, con `python src/api_server.py`) e non quando viene importato come modulo.
if __name__ == '__main__':
    print("INFO (api_server): Avvio del server di sviluppo Flask...")
    # debug=True: Abilita il debugger di Flask e il ricaricamento automatico al salvataggio dei file.
    # host='0.0.0.0': Rende il server accessibile da qualsiasi indirizzo IP sulla macchina,
    # utile per test da altri dispositivi sulla stessa rete. Per test solo locali, '127.0.0.1' va bene.
    # port=5000: Specifica la porta su cui il server ascolterà le richieste.
    app.run(debug=True, host='0.0.0.0', port=5000)