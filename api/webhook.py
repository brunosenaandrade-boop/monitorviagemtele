from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.parse
import hashlib
import hmac
from datetime import datetime

# Configurações
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_SECRET = os.environ.get('TELEGRAM_WEBHOOK_SECRET', '')  # Opcional
AMADEUS_KEY = os.environ.get('AMADEUS_API_KEY', '')
AMADEUS_SECRET = os.environ.get('AMADEUS_API_SECRET', '')
UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')

# Amadeus: 'test' ou 'production'
AMADEUS_ENV = os.environ.get('AMADEUS_ENV', 'test')
AMADEUS_BASE_URL = 'https://api.amadeus.com' if AMADEUS_ENV == 'production' else 'https://test.api.amadeus.com'

# Timeout padrão para requisições HTTP (10 segundos)
HTTP_TIMEOUT = 10

# Cache do token Amadeus (em memória por execução)
_amadeus_token_cache = {"token": None, "expires_at": 0}

# Base de aeroportos brasileiros (fallback para API de teste limitada)
BRAZILIAN_AIRPORTS = [
    {"code": "GRU", "name": "Aeroporto de Guarulhos", "city": "São Paulo"},
    {"code": "CGH", "name": "Aeroporto de Congonhas", "city": "São Paulo"},
    {"code": "VCP", "name": "Aeroporto de Viracopos", "city": "Campinas"},
    {"code": "GIG", "name": "Aeroporto do Galeão", "city": "Rio de Janeiro"},
    {"code": "SDU", "name": "Santos Dumont", "city": "Rio de Janeiro"},
    {"code": "BSB", "name": "Aeroporto de Brasília", "city": "Brasília"},
    {"code": "CNF", "name": "Aeroporto de Confins", "city": "Belo Horizonte"},
    {"code": "PLU", "name": "Aeroporto da Pampulha", "city": "Belo Horizonte"},
    {"code": "SSA", "name": "Aeroporto de Salvador", "city": "Salvador"},
    {"code": "REC", "name": "Aeroporto do Recife", "city": "Recife"},
    {"code": "FOR", "name": "Aeroporto de Fortaleza", "city": "Fortaleza"},
    {"code": "POA", "name": "Aeroporto Salgado Filho", "city": "Porto Alegre"},
    {"code": "CWB", "name": "Aeroporto Afonso Pena", "city": "Curitiba"},
    {"code": "FLN", "name": "Aeroporto Hercílio Luz", "city": "Florianópolis"},
    {"code": "NAT", "name": "Aeroporto de Natal", "city": "Natal"},
    {"code": "MCZ", "name": "Aeroporto de Maceió", "city": "Maceió"},
    {"code": "AJU", "name": "Aeroporto de Aracaju", "city": "Aracaju"},
    {"code": "VIX", "name": "Aeroporto de Vitória", "city": "Vitória"},
    {"code": "CGB", "name": "Aeroporto de Cuiabá", "city": "Cuiabá"},
    {"code": "CGR", "name": "Aeroporto de Campo Grande", "city": "Campo Grande"},
    {"code": "GYN", "name": "Aeroporto de Goiânia", "city": "Goiânia"},
    {"code": "MAO", "name": "Aeroporto de Manaus", "city": "Manaus"},
    {"code": "BEL", "name": "Aeroporto de Belém", "city": "Belém"},
    {"code": "SLZ", "name": "Aeroporto de São Luís", "city": "São Luís"},
    {"code": "THE", "name": "Aeroporto de Teresina", "city": "Teresina"},
    {"code": "JPA", "name": "Aeroporto de João Pessoa", "city": "João Pessoa"},
    {"code": "IGU", "name": "Aeroporto de Foz do Iguaçu", "city": "Foz do Iguaçu"},
    {"code": "NVT", "name": "Aeroporto de Navegantes", "city": "Navegantes"},
    {"code": "JOI", "name": "Aeroporto de Joinville", "city": "Joinville"},
    {"code": "LDB", "name": "Aeroporto de Londrina", "city": "Londrina"},
    {"code": "MGF", "name": "Aeroporto de Maringá", "city": "Maringá"},
    {"code": "UDI", "name": "Aeroporto de Uberlândia", "city": "Uberlândia"},
    {"code": "RAO", "name": "Aeroporto de Ribeirão Preto", "city": "Ribeirão Preto"},
    {"code": "SJP", "name": "Aeroporto de São José do Rio Preto", "city": "São José do Rio Preto"},
]

# Destinos internacionais populares
INTERNATIONAL_AIRPORTS = [
    {"code": "MIA", "name": "Miami International", "city": "Miami"},
    {"code": "MCO", "name": "Orlando International", "city": "Orlando"},
    {"code": "JFK", "name": "John F. Kennedy", "city": "Nova York"},
    {"code": "EWR", "name": "Newark Liberty", "city": "Nova York"},
    {"code": "LAX", "name": "Los Angeles International", "city": "Los Angeles"},
    {"code": "LIS", "name": "Aeroporto de Lisboa", "city": "Lisboa"},
    {"code": "OPO", "name": "Aeroporto do Porto", "city": "Porto"},
    {"code": "MAD", "name": "Aeroporto de Barajas", "city": "Madrid"},
    {"code": "BCN", "name": "El Prat", "city": "Barcelona"},
    {"code": "CDG", "name": "Charles de Gaulle", "city": "Paris"},
    {"code": "ORY", "name": "Orly", "city": "Paris"},
    {"code": "FCO", "name": "Fiumicino", "city": "Roma"},
    {"code": "MXP", "name": "Malpensa", "city": "Milão"},
    {"code": "LHR", "name": "Heathrow", "city": "Londres"},
    {"code": "LGW", "name": "Gatwick", "city": "Londres"},
    {"code": "AMS", "name": "Schiphol", "city": "Amsterdam"},
    {"code": "FRA", "name": "Frankfurt Airport", "city": "Frankfurt"},
    {"code": "MUC", "name": "Munich Airport", "city": "Munique"},
    {"code": "EZE", "name": "Ezeiza", "city": "Buenos Aires"},
    {"code": "SCL", "name": "Arturo Merino", "city": "Santiago"},
    {"code": "BOG", "name": "El Dorado", "city": "Bogotá"},
    {"code": "LIM", "name": "Jorge Chávez", "city": "Lima"},
    {"code": "MEX", "name": "Benito Juárez", "city": "Cidade do México"},
    {"code": "CUN", "name": "Cancún International", "city": "Cancún"},
    {"code": "PTY", "name": "Tocumen", "city": "Cidade do Panamá"},
    {"code": "DXB", "name": "Dubai International", "city": "Dubai"},
    {"code": "NRT", "name": "Narita", "city": "Tóquio"},
    {"code": "ICN", "name": "Incheon", "city": "Seul"},
]

ALL_AIRPORTS = BRAZILIAN_AIRPORTS + INTERNATIONAL_AIRPORTS


def normalize_text(text):
    """Remove acentos e converte para minúsculas."""
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n'
    }
    text = text.lower()
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    return text


def search_local_airports(keyword):
    """Busca aeroportos na base local."""
    keyword_normalized = normalize_text(keyword)
    results = []

    for airport in ALL_AIRPORTS:
        city_normalized = normalize_text(airport["city"])
        name_normalized = normalize_text(airport["name"])
        code_lower = airport["code"].lower()

        # Match por código, cidade ou nome
        if (keyword_normalized in city_normalized or
            keyword_normalized in name_normalized or
            keyword_normalized == code_lower or
            city_normalized.startswith(keyword_normalized)):
            results.append(airport)

    return results[:5]


def redis_get(key):
    """Busca valor no Redis."""
    if not UPSTASH_URL:
        return None
    try:
        url = f"{UPSTASH_URL}/get/{key}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
            data = json.loads(response.read().decode())
            result = data.get('result')
            return json.loads(result) if result else None
    except urllib.error.URLError as e:
        print(f"Redis GET error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Redis JSON error: {e}")
        return None


def redis_set(key, value):
    """Salva valor no Redis."""
    if not UPSTASH_URL:
        return False
    try:
        encoded_value = urllib.parse.quote(json.dumps(value))
        url = f"{UPSTASH_URL}/set/{key}/{encoded_value}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
        return True
    except urllib.error.URLError as e:
        print(f"Redis SET error: {e}")
        return False


def send_message(chat_id, text, reply_markup=None):
    """Envia mensagem via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
        return True
    except urllib.error.URLError as e:
        print(f"Telegram send error: {e}")
        return False


def answer_callback(callback_id):
    """Responde callback query."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_id}
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
    except urllib.error.URLError:
        pass  # Não crítico


def get_amadeus_token():
    """Obtém token da API Amadeus com cache."""
    global _amadeus_token_cache

    # Verificar cache
    now = datetime.now().timestamp()
    if _amadeus_token_cache["token"] and _amadeus_token_cache["expires_at"] > now:
        return _amadeus_token_cache["token"]

    url = f"{AMADEUS_BASE_URL}/v1/security/oauth2/token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": AMADEUS_KEY,
        "client_secret": AMADEUS_SECRET
    }).encode()
    req = urllib.request.Request(url, data=data)

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
            result = json.loads(response.read().decode())
            token = result.get("access_token")
            expires_in = result.get("expires_in", 1800)  # Padrão 30 min

            # Cachear com margem de 60 segundos
            _amadeus_token_cache = {
                "token": token,
                "expires_at": now + expires_in - 60
            }
            return token
    except urllib.error.URLError as e:
        print(f"Amadeus token error: {e}")
        return None


def search_airports(keyword):
    """Busca aeroportos - primeiro na base local, depois na API."""
    # Primeiro tenta a base local (mais rápida e completa para BR)
    local_results = search_local_airports(keyword)
    if local_results:
        return local_results

    # Se não encontrou localmente, tenta a API Amadeus
    token = get_amadeus_token()
    if not token:
        return []

    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations?keyword={urllib.parse.quote(keyword)}&subType=AIRPORT,CITY"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
            data = json.loads(response.read().decode())
            results = [
                {
                    "code": loc["iataCode"],
                    "name": loc.get("name", ""),
                    "city": loc.get("address", {}).get("cityName", "")
                }
                for loc in data.get("data", [])[:5]
            ]
            return results if results else []
    except urllib.error.URLError as e:
        print(f"Airport search error: {e}")
        return []


def search_flights(origin, destination, departure_date, return_date=None, adults=1):
    """Busca voos."""
    token = get_amadeus_token()
    if not token:
        return []

    params = f"originLocationCode={origin}&destinationLocationCode={destination}&departureDate={departure_date}&adults={adults}&currencyCode=BRL&max=5"
    if return_date:
        params += f"&returnDate={return_date}"

    url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(req, timeout=30) as response:  # Timeout maior para busca
            data = json.loads(response.read().decode())
            offers = []
            for offer in data.get("data", [])[:5]:
                price = float(offer["price"]["total"])
                segment = offer["itineraries"][0]["segments"][0]
                offers.append({
                    "price": price,
                    "airline": segment["carrierCode"],
                    "stops": len(offer["itineraries"][0]["segments"]) - 1
                })
            return sorted(offers, key=lambda x: x["price"])
    except urllib.error.URLError as e:
        print(f"Flight search error: {e}")
        return []


def format_brl(value):
    """Formata valor em Real brasileiro (R$ 1.234,56)."""
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def main_menu(chat_id):
    """Mostra menu principal."""
    keyboard = {
        "inline_keyboard": [
            [{"text": "Novo Monitoramento", "callback_data": "new_monitor"}],
            [{"text": "Meus Monitoramentos", "callback_data": "my_monitors"}],
            [{"text": "Buscar Voo Agora", "callback_data": "search_now"}],
            [{"text": "Ajuda", "callback_data": "help"}]
        ]
    }
    send_message(chat_id, "*Monitor de Viagens*\n\nEscolha uma opção:", keyboard)


def handle_message(message):
    """Processa mensagens de texto."""
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
        redis_set(f"state:{user_id}", None)
        main_menu(chat_id)
        return

    state_data = redis_get(f"state:{user_id}")
    if not state_data:
        send_message(chat_id, "Use /start para começar!")
        return

    state = state_data.get("state", "")
    data = state_data.get("data", {})

    cancel_keyboard = {"inline_keyboard": [[{"text": "Cancelar", "callback_data": "main_menu"}]]}

    # Origem - buscar aeroportos
    if state in ["origin", "search_origin"]:
        airports = search_airports(text)
        if not airports:
            send_message(chat_id, f"Nenhum aeroporto encontrado para '{text}'.", cancel_keyboard)
            return

        data["airports"] = {a["code"]: f"{a['city']} - {a['name']}" for a in airports}
        prefix = "origin_" if state == "origin" else "sorigin_"

        keyboard = {"inline_keyboard": [
            [{"text": f"{a['code']} - {a['name'] or a['city']}", "callback_data": f"{prefix}{a['code']}"}]
            for a in airports
        ] + [[{"text": "Cancelar", "callback_data": "main_menu"}]]}

        redis_set(f"state:{user_id}", {"state": state + "_select", "data": data})
        send_message(chat_id, f"*Aeroportos para '{text}':*\n\nEscolha:", keyboard)

    # Destino - buscar aeroportos
    elif state in ["destination", "search_destination"]:
        airports = search_airports(text)
        if not airports:
            send_message(chat_id, f"Nenhum aeroporto encontrado para '{text}'.", cancel_keyboard)
            return

        data["airports"] = {a["code"]: f"{a['city']} - {a['name']}" for a in airports}
        prefix = "dest_" if state == "destination" else "sdest_"

        keyboard = {"inline_keyboard": [
            [{"text": f"{a['code']} - {a['name'] or a['city']}", "callback_data": f"{prefix}{a['code']}"}]
            for a in airports
        ] + [[{"text": "Cancelar", "callback_data": "main_menu"}]]}

        redis_set(f"state:{user_id}", {"state": state + "_select", "data": data})
        send_message(chat_id, "*Escolha o aeroporto de destino:*", keyboard)

    # Data de ida
    elif state in ["departure_date", "search_departure_date"]:
        try:
            date = datetime.strptime(text, "%d/%m/%Y")
            if date.date() < datetime.now().date():
                send_message(chat_id, "A data não pode ser no passado!", cancel_keyboard)
                return

            data["departure_date"] = date.strftime("%Y-%m-%d")
            next_state = "return_date" if state == "departure_date" else "search_return_date"

            keyboard = {"inline_keyboard": [
                [{"text": "Só ida (sem volta)", "callback_data": "skip_return"}],
                [{"text": "Cancelar", "callback_data": "main_menu"}]
            ]}

            redis_set(f"state:{user_id}", {"state": next_state, "data": data})
            send_message(chat_id, f"Data de ida: *{text}*\n\nDigite a data de volta (DD/MM/AAAA):", keyboard)
        except ValueError:
            send_message(chat_id, "Formato inválido. Use DD/MM/AAAA", cancel_keyboard)

    # Data de volta
    elif state in ["return_date", "search_return_date"]:
        try:
            date = datetime.strptime(text, "%d/%m/%Y")
            departure = datetime.strptime(data["departure_date"], "%Y-%m-%d")
            if date.date() < departure.date():
                send_message(chat_id, "A volta deve ser após a ida!", cancel_keyboard)
                return

            data["return_date"] = date.strftime("%Y-%m-%d")
            next_state = "adults" if state == "return_date" else "search_adults"

            keyboard = {"inline_keyboard": [
                [{"text": "1", "callback_data": "adults_1"}, {"text": "2", "callback_data": "adults_2"},
                 {"text": "3", "callback_data": "adults_3"}, {"text": "4", "callback_data": "adults_4"}],
                [{"text": "Cancelar", "callback_data": "main_menu"}]
            ]}

            redis_set(f"state:{user_id}", {"state": next_state, "data": data})
            send_message(chat_id, "*Quantos adultos?*", keyboard)
        except ValueError:
            send_message(chat_id, "Formato inválido. Use DD/MM/AAAA", cancel_keyboard)

    # Preço máximo
    elif state == "max_price":
        try:
            max_price = float(text.replace(",", ".").replace("R$", "").strip())
            if max_price <= 0:
                raise ValueError("Preço deve ser positivo")
            data["max_price"] = max_price
            finish_monitor(chat_id, user_id, data)
        except ValueError:
            send_message(chat_id, "Valor inválido. Digite apenas números (ex: 1500)", cancel_keyboard)


def handle_callback(callback_query):
    """Processa cliques em botões."""
    chat_id = callback_query["message"]["chat"]["id"]
    user_id = callback_query["from"]["id"]
    callback_id = callback_query["id"]
    action = callback_query.get("data", "")

    answer_callback(callback_id)

    state_data = redis_get(f"state:{user_id}") or {"state": "", "data": {}}
    data = state_data.get("data", {})

    cancel_keyboard = {"inline_keyboard": [[{"text": "Cancelar", "callback_data": "main_menu"}]]}

    if action == "main_menu":
        redis_set(f"state:{user_id}", None)
        main_menu(chat_id)

    elif action == "new_monitor":
        redis_set(f"state:{user_id}", {"state": "origin", "data": {}})
        send_message(chat_id, "*Novo Monitoramento*\n\nDigite o nome da cidade de origem:", cancel_keyboard)

    elif action == "search_now":
        redis_set(f"state:{user_id}", {"state": "search_origin", "data": {"mode": "search"}})
        send_message(chat_id, "*Buscar Voo*\n\nDigite o nome da cidade de origem:", cancel_keyboard)

    elif action == "my_monitors":
        monitors = redis_get(f"monitors:{user_id}") or []
        if not monitors:
            keyboard = {"inline_keyboard": [
                [{"text": "Criar Monitoramento", "callback_data": "new_monitor"}],
                [{"text": "Menu Principal", "callback_data": "main_menu"}]
            ]}
            send_message(chat_id, "*Meus Monitoramentos*\n\nVocê não tem monitoramentos ativos.", keyboard)
            return

        text = "*Meus Monitoramentos*\n\n"
        keyboard_buttons = []
        for i, m in enumerate(monitors):
            text += f"*{m['origin']} → {m['destination']}*\n"
            text += f"  Data: {m['departure_date']}\n\n"
            keyboard_buttons.append([{"text": f"Excluir #{i+1}", "callback_data": f"delete_{i}"}])

        keyboard_buttons.append([{"text": "Menu Principal", "callback_data": "main_menu"}])
        send_message(chat_id, text, {"inline_keyboard": keyboard_buttons})

    elif action == "help":
        help_text = """*Como usar:*

1. Clique em Novo Monitoramento
2. Digite a cidade de origem
3. Digite a cidade de destino
4. Informe as datas
5. Receba alertas!

*Dicas:*
- Digite o nome da cidade (ex: São Paulo)
- O bot mostra os aeroportos disponíveis"""
        keyboard = {"inline_keyboard": [[{"text": "Menu Principal", "callback_data": "main_menu"}]]}
        send_message(chat_id, help_text, keyboard)

    elif action.startswith("origin_") or action.startswith("sorigin_"):
        code = action.replace("origin_", "").replace("sorigin_", "")
        data["origin"] = code
        data["origin_name"] = data.get("airports", {}).get(code, code)

        is_search = action.startswith("s")
        next_state = "search_destination" if is_search else "destination"

        redis_set(f"state:{user_id}", {"state": next_state, "data": data})
        send_message(chat_id, f"Origem: *{data['origin_name']}* ({code})\n\nDigite a cidade de destino:", cancel_keyboard)

    elif action.startswith("dest_") or action.startswith("sdest_"):
        code = action.replace("dest_", "").replace("sdest_", "")
        data["destination"] = code
        data["destination_name"] = data.get("airports", {}).get(code, code)

        is_search = action.startswith("s")
        next_state = "search_departure_date" if is_search else "departure_date"

        redis_set(f"state:{user_id}", {"state": next_state, "data": data})
        send_message(chat_id, f"Origem: *{data.get('origin_name')}*\nDestino: *{data['destination_name']}*\n\nDigite a data de ida (DD/MM/AAAA):", cancel_keyboard)

    elif action == "skip_return":
        data["return_date"] = None
        is_search = state_data.get("state", "").startswith("search")
        next_state = "search_adults" if is_search else "adults"

        keyboard = {"inline_keyboard": [
            [{"text": "1", "callback_data": "adults_1"}, {"text": "2", "callback_data": "adults_2"},
             {"text": "3", "callback_data": "adults_3"}, {"text": "4", "callback_data": "adults_4"}],
            [{"text": "Cancelar", "callback_data": "main_menu"}]
        ]}
        redis_set(f"state:{user_id}", {"state": next_state, "data": data})
        send_message(chat_id, "*Quantos adultos?*", keyboard)

    elif action.startswith("adults_"):
        adults = int(action.split("_")[1])
        data["adults"] = adults

        is_search = state_data.get("state", "").startswith("search")

        if is_search:
            # Executar busca
            send_message(chat_id, "*Buscando voos...*")
            offers = search_flights(data["origin"], data["destination"], data["departure_date"], data.get("return_date"), adults)

            if not offers:
                keyboard = {"inline_keyboard": [[{"text": "Menu Principal", "callback_data": "main_menu"}]]}
                send_message(chat_id, "*Nenhum voo encontrado*\n\nTente outras datas.", keyboard)
            else:
                text = f"*Voos: {data.get('origin_name', data['origin'])} → {data.get('destination_name', data['destination'])}*\n\n"
                for i, o in enumerate(offers, 1):
                    stops = "Direto" if o["stops"] == 0 else f"{o['stops']} parada(s)"
                    text += f"*{i}. {format_brl(o['price'])}*\n   {o['airline']} | {stops}\n\n"

                keyboard = {"inline_keyboard": [[{"text": "Menu Principal", "callback_data": "main_menu"}]]}
                send_message(chat_id, text, keyboard)

            redis_set(f"state:{user_id}", None)
        else:
            # Perguntar preço máximo
            keyboard = {"inline_keyboard": [
                [{"text": "Pular (sem limite)", "callback_data": "skip_max_price"}],
                [{"text": "Cancelar", "callback_data": "main_menu"}]
            ]}
            redis_set(f"state:{user_id}", {"state": "max_price", "data": data})
            send_message(chat_id, "*Preço máximo?*\n\nDigite o valor em reais ou pule:", keyboard)

    elif action == "skip_max_price":
        data["max_price"] = None
        finish_monitor(chat_id, user_id, data)

    elif action.startswith("delete_"):
        idx = int(action.split("_")[1])
        monitors = redis_get(f"monitors:{user_id}") or []
        if 0 <= idx < len(monitors):
            monitors.pop(idx)
            redis_set(f"monitors:{user_id}", monitors)

        keyboard = {"inline_keyboard": [[{"text": "Menu Principal", "callback_data": "main_menu"}]]}
        send_message(chat_id, "Monitoramento excluído!", keyboard)


def finish_monitor(chat_id, user_id, data):
    """Finaliza criação do monitoramento."""
    monitors = redis_get(f"monitors:{user_id}") or []
    monitors.append({
        "origin": data["origin"],
        "origin_name": data.get("origin_name", data["origin"]),
        "destination": data["destination"],
        "destination_name": data.get("destination_name", data["destination"]),
        "departure_date": data["departure_date"],
        "return_date": data.get("return_date"),
        "adults": data.get("adults", 1),
        "max_price": data.get("max_price"),
        "chat_id": chat_id,
        "created_at": datetime.now().isoformat()
    })
    redis_set(f"monitors:{user_id}", monitors)
    redis_set(f"state:{user_id}", None)

    text = f"""*Monitoramento Criado!*

Rota: *{data.get('origin_name', data['origin'])} → {data.get('destination_name', data['destination'])}*
Ida: {data['departure_date']}"""

    if data.get("return_date"):
        text += f"\nVolta: {data['return_date']}"
    if data.get("max_price"):
        text += f"\nAlerta quando < {format_brl(data['max_price'])}"

    text += "\n\n_Você receberá alertas quando o preço baixar!_"

    keyboard = {"inline_keyboard": [[{"text": "Menu Principal", "callback_data": "main_menu"}]]}
    send_message(chat_id, text, keyboard)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Limitar tamanho do request (máx 64KB)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 65536:
            self.send_response(413)
            self.end_headers()
            return

        body = self.rfile.read(content_length)

        try:
            update = json.loads(body.decode('utf-8'))

            if "message" in update:
                handle_message(update["message"])
            elif "callback_query" in update:
                handle_callback(update["callback_query"])

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except KeyError as e:
            print(f"Missing key error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "Bot is running!",
            "timestamp": datetime.now().isoformat()
        }).encode())
