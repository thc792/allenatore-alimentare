# src/integrations/openfoodfacts_client.py

import requests
import json

USER_AGENT = "AllenatoreAlimentareApp/1.0 (Python; +tuo@dominio.com o link progetto)"
BASE_URL_PRODUCT_V2 = "https://world.openfoodfacts.org/api/v2/product/"
BASE_URL_SEARCH_CGI = "https://world.openfoodfacts.org/cgi/search.pl"

print("Il file openfoodfacts_client.py è stato caricato!")

def get_product_by_barcode(barcode: str) -> dict | None:
    headers = {'User-Agent': USER_AGENT}
    url = f"{BASE_URL_PRODUCT_V2}{barcode}"
    params = {
        "fields": "product_name_it,product_name,nutriments,brands,code,image_url,status,status_verbose"
    }

    print(f"\nINFO: Sto cercando il prodotto con barcode: {barcode}")
    print(f"INFO: URL completo della richiesta: {url}")
    # print(f"INFO: Parametri (campi richiesti): {params}") # Meno verboso

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        api_status = data.get("status")
        api_status_verbose = data.get("status_verbose")

        if api_status == 1 and "product" in data and data.get("product"):
            product_info = data["product"]
            if not product_info or not product_info.get("product_name_it", product_info.get("product_name")):
                print(f"WARN: Prodotto con barcode {barcode} trovato con status=1 ma i dati del prodotto sono mancanti o incompleti.")
                return None

            print(f"INFO: Prodotto '{product_info.get('product_name_it', product_info.get('product_name'))}' trovato!")
            nutriments = product_info.get("nutriments", {})
            return {
                "barcode": product_info.get("code"),
                "name": product_info.get("product_name_it", product_info.get("product_name")),
                "brands": product_info.get("brands"),
                "image_url": product_info.get("image_url"),
                "calories_100g": nutriments.get("energy-kcal_100g"),
                "protein_100g": nutriments.get("proteins_100g"),
                "carbs_100g": nutriments.get("carbohydrates_100g"),
                "fat_100g": nutriments.get("fat_100g"),
                "api_source": "OpenFoodFacts_v2_product"
            }
        elif api_status == 0 and api_status_verbose == "product not found":
            print(f"INFO: Prodotto con barcode {barcode} non trovato (status 0, product not found).")
            return None
        else:
            print(f"WARN: Prodotto con barcode {barcode} non trovato o risposta inattesa. Status API: {api_status}, Status Verbose: '{api_status_verbose}'")
            # print(f"DEBUG: Dati completi ricevuti: {json.dumps(data, indent=2, ensure_ascii=False)}") # Per debug futuro se necessario
            return None

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404: # HTTP 404 significa Not Found
            print(f"INFO: Prodotto con barcode {barcode} non trovato (HTTP 404).")
            return None
        else:
            print(f"ERRORE HTTP: {http_err} - Status Code: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError as conn_err:
        print(f"ERRORE DI CONNESSIONE: Impossibile connettersi a Open Food Facts. {conn_err}")
        return None
    except requests.exceptions.Timeout as timeout_err:
        print(f"ERRORE DI TIMEOUT: La richiesta a Open Food Facts ha impiegato troppo tempo. {timeout_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"ERRORE RICHIESTA GENERICA: {req_err}")
        return None
    except json.JSONDecodeError:
        print(f"ERRORE: Impossibile decodificare la risposta JSON da Open Food Facts per barcode {barcode}. Risposta: {response.text[:200]}...")
        return None
def search_products_by_name(query: str, page_size: int = 5, lang: str = "it") -> list[dict] | None:
    """
    Cerca prodotti per nome su Open Food Facts usando l'endpoint CGI search.pl.

    Args:
        query (str): Il termine di ricerca per i prodotti (es. "pasta Barilla").
        page_size (int, optional): Quanti prodotti restituire al massimo. Default a 5.
        lang (str, optional): Codice lingua per la ricerca (es. "it", "en"). Default a "it".

    Returns:
        list[dict] | None: Una lista di dizionari, ognuno rappresentante un prodotto trovato.
                           Restituisce una lista vuota se nessun prodotto è trovato.
                           Restituisce None se si verifica un errore durante la richiesta.
    """
    headers = {'User-Agent': USER_AGENT}
    
    # Parametri per l'API di ricerca
    # Documentazione: https://wiki.openfoodfacts.org/API/Search
    params = {
        "search_terms": query,
        "search_simple": 1,      # Per una ricerca "semplice" sui termini
        "action": "process",     # Azione richiesta all'API
        "json": 1,               # Richiediamo l'output in formato JSON
        "page_size": page_size,  # Numero di risultati per pagina
        "lc": lang,              # Codice lingua per i risultati (se disponibile)
        # Specifichiamo i campi che ci interessano per alleggerire la risposta
        "fields": "product_name_it,product_name,nutriments,brands,code,image_url"
    }
    
    url = BASE_URL_SEARCH_CGI # Usiamo l'URL per la ricerca CGI

    print(f"\nINFO: Sto cercando prodotti con query: '{query}' (lingua: {lang}, max {page_size} risultati)")
    print(f"INFO: URL della richiesta: {url}")
    # print(f"INFO: Parametri della ricerca: {params}") # Meno verboso

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15) # Timeout un po' più lungo per la ricerca
        response.raise_for_status() # Controlla errori HTTP
        data = response.json()

        # La risposta JSON per la ricerca ha una chiave "products" che è una lista
        if "products" in data and data["products"]: # Controlla se la lista esiste e non è vuota
            products_found = []
            for product_data_api in data["products"]:
                # Simile a get_product_by_barcode, estraiamo i dati che ci servono
                # Potrebbe mancare product_name_it, quindi usiamo product_name come fallback
                product_name = product_data_api.get("product_name_it", product_data_api.get("product_name"))
                
                # Ignoriamo prodotti senza nome, potrebbero essere dati spuri
                if not product_name:
                    continue

                nutriments = product_data_api.get("nutriments", {})
                
                simplified_product = {
                    "barcode": product_data_api.get("code"),
                    "name": product_name,
                    "brands": product_data_api.get("brands"),
                    "image_url": product_data_api.get("image_url"),
                    "calories_100g": nutriments.get("energy-kcal_100g"),
                    "protein_100g": nutriments.get("proteins_100g"),
                    "carbs_100g": nutriments.get("carbohydrates_100g"),
                    "fat_100g": nutriments.get("fat_100g"),
                    "api_source": "OpenFoodFacts_cgi_search"
                }
                products_found.append(simplified_product)
            
            print(f"INFO: Trovati {len(products_found)} prodotti per la query '{query}'.")
            return products_found
        else:
            # Nessun prodotto trovato o la chiave "products" manca/è vuota
            print(f"INFO: Nessun prodotto trovato per la query '{query}'.")
            return [] # Restituisce una lista vuota se non ci sono prodotti

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404: # Anche se raro per la ricerca, gestiamolo
            print(f"INFO: Ricerca per '{query}' ha restituito HTTP 404.")
            return [] # Trattiamo come nessun risultato
        else:
            print(f"ERRORE HTTP durante la ricerca: {http_err} - Status Code: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError as conn_err:
        print(f"ERRORE DI CONNESSIONE durante la ricerca: Impossibile connettersi. {conn_err}")
        return None
    except requests.exceptions.Timeout as timeout_err:
        print(f"ERRORE DI TIMEOUT durante la ricerca: {timeout_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"ERRORE RICHIESTA GENERICA durante la ricerca: {req_err}")
        return None
    except json.JSONDecodeError:
        print(f"ERRORE: Impossibile decodificare la risposta JSON dalla ricerca per '{query}'. Risposta: {response.text[:200]}...")
        return None

# FINE DELLA FUNZIONE search_products_by_name


if __name__ == '__main__':
    print("\n--- INIZIO TEST get_product_by_barcode ---")
    # ... (codice di test per get_product_by_barcode che avevamo già) ...
    barcode_esempio_cocacola = "5449000000996"
    print(f"\nSto testando con il barcode: {barcode_esempio_cocacola}")
    prodotto_trovato = get_product_by_barcode(barcode_esempio_cocacola)

    if prodotto_trovato:
        print("\nProdotto TROVATO! Ecco i dati:")
        print(json.dumps(prodotto_trovato, indent=2, ensure_ascii=False))
    else:
        print(f"\nProdotto con barcode {barcode_esempio_cocacola} NON TROVATO o si è verificato un errore.")

    print("\n--- TEST con un barcode 'particolare' (1234567890123) ---")
    barcode_anomalo = "1234567890123"
    print(f"Sto testando con il barcode anomalo: {barcode_anomalo}")
    prodotto_anomalo = get_product_by_barcode(barcode_anomalo)

    if prodotto_anomalo:
        print(f"\nProdotto per barcode '{barcode_anomalo}' TROVATO (come da API OpenFoodFacts). Dati:")
        print(json.dumps(prodotto_anomalo, indent=2, ensure_ascii=False))
    else:
        print(f"\nProdotto con barcode '{barcode_anomalo}' NON TROVATO (inaspettato per questo barcode).")
        
    print("\n--- FINE TEST get_product_by_barcode ---")


    # --- NUOVI TEST PER search_products_by_name ---
    print("\n\n--- INIZIO TEST search_products_by_name ---")

    query_ricerca_1 = "pasta Barilla spaghetti"
    print(f"\nSto cercando prodotti per: '{query_ricerca_1}'")
    risultati_ricerca_1 = search_products_by_name(query_ricerca_1, page_size=3, lang="it")

    if risultati_ricerca_1 is not None: # Controlla se c'è stato un errore (None) o una lista (anche vuota)
        if risultati_ricerca_1: # Se la lista non è vuota
            print(f"\nRisultati trovati per '{query_ricerca_1}':")
            for prodotto in risultati_ricerca_1:
                print(json.dumps(prodotto, indent=2, ensure_ascii=False))
                print("---") # Separatore tra prodotti
        else:
            print(f"\nNessun prodotto trovato per '{query_ricerca_1}'.")
    else:
        print(f"\nErrore durante la ricerca per '{query_ricerca_1}'.")

    query_ricerca_2 = "cioccolato fondente extra"
    print(f"\nSto cercando prodotti per: '{query_ricerca_2}' (max 2 risultati)")
    risultati_ricerca_2 = search_products_by_name(query_ricerca_2, page_size=2, lang="it")

    if risultati_ricerca_2 is not None:
        if risultati_ricerca_2:
            print(f"\nRisultati trovati per '{query_ricerca_2}':")
            for prodotto in risultati_ricerca_2:
                print(json.dumps(prodotto, indent=2, ensure_ascii=False))
                print("---")
        else:
            print(f"\nNessun prodotto trovato per '{query_ricerca_2}'.")
    else:
        print(f"\nErrore durante la ricerca per '{query_ricerca_2}'.")

    query_ricerca_inesistente = "prodottoinventatochecertononesiste123gnurbleplick"
    print(f"\nSto cercando prodotti per: '{query_ricerca_inesistente}' (dovrebbe dare 0 risultati)")
    risultati_ricerca_inesistente = search_products_by_name(query_ricerca_inesistente, page_size=2, lang="it")

    if risultati_ricerca_inesistente is not None:
        if not risultati_ricerca_inesistente: # Ci aspettiamo una lista vuota
            print(f"\nCorretto: Nessun prodotto trovato per '{query_ricerca_inesistente}' (come atteso).")
        else: # Se trova qualcosa, è un errore nel test
            print(f"\nERRORE NEL TEST: Trovati prodotti per una query inesistente '{query_ricerca_inesistente}'?!")
            for prodotto in risultati_ricerca_inesistente:
                print(json.dumps(prodotto, indent=2, ensure_ascii=False))
                print("---")
    else:
        print(f"\nErrore durante la ricerca per '{query_ricerca_inesistente}'.")

    print("\n--- FINE TEST search_products_by_name ---")