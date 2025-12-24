import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import (
    init_db, save_monitor, get_user_monitors, get_all_active_monitors,
    update_monitor_price, deactivate_monitor, get_price_history,
    save_user_state, get_user_state, clear_user_state
)
from flight_service import FlightService

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flight_service = FlightService()

# Estados do fluxo de conversa
STATE_ORIGIN = "origin"
STATE_ORIGIN_SELECT = "origin_select"
STATE_DESTINATION = "destination"
STATE_DESTINATION_SELECT = "destination_select"
STATE_DEPARTURE_DATE = "departure_date"
STATE_RETURN_DATE = "return_date"
STATE_ADULTS = "adults"
STATE_MAX_PRICE = "max_price"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Menu principal."""
    keyboard = [
        [InlineKeyboardButton("Novo Monitoramento", callback_data="new_monitor")],
        [InlineKeyboardButton("Meus Monitoramentos", callback_data="my_monitors")],
        [InlineKeyboardButton("Buscar Voo Agora", callback_data="search_now")],
        [InlineKeyboardButton("Ajuda", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = """
*Monitor de Viagens*

Bem-vindo! Eu monitoro precos de voos e te aviso quando encontrar boas ofertas.

*O que voce quer fazer?*
"""
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa cliques nos botoes."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "new_monitor":
        await start_new_monitor(query, user_id)

    elif query.data == "search_now":
        await start_search_now(query, user_id)

    elif query.data == "my_monitors":
        await show_my_monitors(query, user_id)

    elif query.data == "help":
        await show_help(query)

    elif query.data == "main_menu":
        await clear_user_state(user_id)
        await start(update, context)

    elif query.data == "skip_return":
        await process_skip_return(query, user_id)

    elif query.data == "skip_max_price":
        await process_skip_max_price(query, user_id)

    elif query.data.startswith("origin_"):
        code = query.data.replace("origin_", "")
        await process_airport_selection(query, user_id, code, "origin")

    elif query.data.startswith("dest_"):
        code = query.data.replace("dest_", "")
        await process_airport_selection(query, user_id, code, "destination")

    elif query.data.startswith("adults_"):
        adults = int(query.data.split("_")[1])
        await process_adults_selection(query, user_id, adults)

    elif query.data.startswith("delete_"):
        monitor_id = int(query.data.split("_")[1])
        await delete_monitor(query, user_id, monitor_id)

    elif query.data.startswith("history_"):
        monitor_id = int(query.data.split("_")[1])
        await show_price_history(query, monitor_id)


async def start_new_monitor(query, user_id: int):
    """Inicia o fluxo de novo monitoramento."""
    await save_user_state(user_id, STATE_ORIGIN, {})

    keyboard = [[InlineKeyboardButton("Cancelar", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "*Novo Monitoramento*\n\n"
        "Digite o nome da *cidade de origem*:\n\n"
        "_Exemplo: Sao Paulo, Rio de Janeiro, Miami_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def start_search_now(query, user_id: int):
    """Inicia busca imediata."""
    await save_user_state(user_id, f"search_{STATE_ORIGIN}", {"mode": "search"})

    keyboard = [[InlineKeyboardButton("Cancelar", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "*Buscar Voo*\n\n"
        "Digite o nome da *cidade de origem*:\n\n"
        "_Exemplo: Sao Paulo, Rio de Janeiro, Miami_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def process_airport_selection(query, user_id: int, code: str, field: str):
    """Processa a selecao de aeroporto."""
    state = await get_user_state(user_id)
    if not state:
        return

    data = state["data"]
    current_state = state["state"]
    is_search = current_state.startswith("search_")

    if field == "origin":
        data["origin"] = code
        data["origin_name"] = data.get("airports", {}).get(code, code)
        next_state = f"search_{STATE_DESTINATION}" if is_search else STATE_DESTINATION

        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="main_menu")]]

        await save_user_state(user_id, next_state, data)
        await query.edit_message_text(
            f"Origem: *{data['origin_name']}* ({code})\n\n"
            "Agora digite o nome da *cidade de destino*:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif field == "destination":
        data["destination"] = code
        data["destination_name"] = data.get("airports", {}).get(code, code)
        next_state = f"search_{STATE_DEPARTURE_DATE}" if is_search else STATE_DEPARTURE_DATE

        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="main_menu")]]

        await save_user_state(user_id, next_state, data)
        await query.edit_message_text(
            f"Origem: *{data.get('origin_name', data['origin'])}* ({data['origin']})\n"
            f"Destino: *{data['destination_name']}* ({code})\n\n"
            "Digite a *data de ida* (formato: DD/MM/AAAA):\n\n"
            "_Exemplo: 15/01/2025_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


async def show_my_monitors(query, user_id: int):
    """Mostra os monitoramentos do usuario."""
    monitors = await get_user_monitors(user_id)

    if not monitors:
        keyboard = [
            [InlineKeyboardButton("Criar Monitoramento", callback_data="new_monitor")],
            [InlineKeyboardButton("Menu Principal", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "*Meus Monitoramentos*\n\n"
            "Voce ainda nao tem monitoramentos ativos.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    text = "*Meus Monitoramentos*\n\n"
    keyboard = []

    for m in monitors:
        price_info = f"R$ {m['last_price']:,.2f}" if m['last_price'] else "Aguardando..."
        text += f"*{m['origin']} -> {m['destination']}*\n"
        text += f"  Data: {m['departure_date']}"
        if m['return_date']:
            text += f" - {m['return_date']}"
        text += f"\n  Ultimo: {price_info}\n\n"

        keyboard.append([
            InlineKeyboardButton(f"Historico #{m['id']}", callback_data=f"history_{m['id']}"),
            InlineKeyboardButton(f"Excluir", callback_data=f"delete_{m['id']}")
        ])

    keyboard.append([InlineKeyboardButton("Menu Principal", callback_data="main_menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_help(query):
    """Mostra ajuda."""
    help_text = """
*Como usar o Monitor de Viagens*

*Comandos:*
/start - Menu principal

*Como funciona:*
1. Crie um monitoramento com origem, destino e datas
2. Defina um preco maximo (opcional)
3. Receba alertas quando o preco cair!

*Dicas:*
- Digite o nome da cidade (ex: Sao Paulo, Miami)
- O bot vai mostrar os aeroportos disponiveis
- Escolha o aeroporto clicando no botao

*Cidades populares:*
- Sao Paulo, Rio de Janeiro, Brasilia
- Miami, Orlando, New York
- Lisboa, Paris, Londres
"""
    keyboard = [[InlineKeyboardButton("Menu Principal", callback_data="main_menu")]]
    await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def process_skip_return(query, user_id: int):
    """Processa quando o usuario pula a data de volta."""
    state = await get_user_state(user_id)
    if state:
        data = state["data"]
        data["return_date"] = None
        await save_user_state(user_id, STATE_ADULTS, data)
        await ask_adults(query)


async def process_skip_max_price(query, user_id: int):
    """Processa quando o usuario pula o preco maximo."""
    state = await get_user_state(user_id)
    if state:
        await finish_monitor_creation(query, user_id, state["data"])


async def process_adults_selection(query, user_id: int, adults: int):
    """Processa selecao de quantidade de adultos."""
    state = await get_user_state(user_id)
    if state:
        data = state["data"]
        data["adults"] = adults

        # Se for busca imediata, executa agora
        if data.get("mode") == "search":
            await execute_search(query, data)
            await clear_user_state(user_id)
        else:
            await save_user_state(user_id, STATE_MAX_PRICE, data)
            await ask_max_price(query)


async def ask_adults(query):
    """Pergunta a quantidade de adultos."""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="adults_1"),
            InlineKeyboardButton("2", callback_data="adults_2"),
            InlineKeyboardButton("3", callback_data="adults_3"),
            InlineKeyboardButton("4", callback_data="adults_4"),
        ],
        [InlineKeyboardButton("Cancelar", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        "*Quantos adultos?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def ask_max_price(query):
    """Pergunta o preco maximo."""
    keyboard = [
        [InlineKeyboardButton("Pular (sem limite)", callback_data="skip_max_price")],
        [InlineKeyboardButton("Cancelar", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        "*Preco maximo desejado?*\n\n"
        "Digite o valor maximo em reais (ex: 1500) ou pule para monitorar qualquer preco.\n\n"
        "_Voce sera notificado quando o preco ficar abaixo deste valor._",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def execute_search(query, data: dict):
    """Executa a busca de voos."""
    await query.edit_message_text("*Buscando voos...*", parse_mode="Markdown")

    offers = flight_service.search_flights(
        origin=data["origin"],
        destination=data["destination"],
        departure_date=data["departure_date"],
        return_date=data.get("return_date"),
        adults=data.get("adults", 1)
    )

    if not offers:
        keyboard = [[InlineKeyboardButton("Menu Principal", callback_data="main_menu")]]
        await query.edit_message_text(
            "*Nenhum voo encontrado*\n\n"
            "Tente outras datas ou destinos.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    origin_name = data.get('origin_name', data['origin'])
    dest_name = data.get('destination_name', data['destination'])

    text = f"*Voos: {origin_name} -> {dest_name}*\n"
    text += f"Data: {data['departure_date']}"
    if data.get('return_date'):
        text += f" - {data['return_date']}"
    text += "\n\n"

    for i, offer in enumerate(offers[:5], 1):
        text += f"*{i}. R$ {offer.price:,.2f}*\n"
        text += f"   {offer.airline} | "
        text += f"{'Direto' if offer.stops == 0 else f'{offer.stops} parada(s)'}\n\n"

    keyboard = [[InlineKeyboardButton("Menu Principal", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def finish_monitor_creation(query, user_id: int, data: dict):
    """Finaliza a criacao do monitoramento."""
    chat_id = query.message.chat_id

    monitor_id = await save_monitor(
        user_id=user_id,
        chat_id=chat_id,
        origin=data["origin"],
        destination=data["destination"],
        departure_date=data["departure_date"],
        return_date=data.get("return_date"),
        adults=data.get("adults", 1),
        max_price=data.get("max_price")
    )

    await clear_user_state(user_id)

    origin_name = data.get('origin_name', data['origin'])
    dest_name = data.get('destination_name', data['destination'])

    text = f"""
*Monitoramento Criado!*

Rota: *{origin_name} -> {dest_name}*
Ida: {data['departure_date']}
"""
    if data.get("return_date"):
        text += f"Volta: {data['return_date']}\n"

    text += f"Adultos: {data.get('adults', 1)}\n"

    if data.get("max_price"):
        text += f"Alerta quando < R$ {data['max_price']:,.2f}\n"

    text += "\n_Voce recebera notificacoes quando encontrarmos bons precos!_"

    keyboard = [[InlineKeyboardButton("Menu Principal", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def delete_monitor(query, user_id: int, monitor_id: int):
    """Exclui um monitoramento."""
    success = await deactivate_monitor(monitor_id, user_id)

    if success:
        await query.answer("Monitoramento excluido!")
        await show_my_monitors(query, user_id)
    else:
        await query.answer("Erro ao excluir", show_alert=True)


async def show_price_history(query, monitor_id: int):
    """Mostra historico de precos."""
    history = await get_price_history(monitor_id)

    if not history:
        await query.answer("Ainda nao ha historico de precos.", show_alert=True)
        return

    text = "*Historico de Precos*\n\n"

    for h in history:
        dt = datetime.fromisoformat(h["checked_at"])
        text += f"- {dt.strftime('%d/%m %H:%M')} - R$ {h['price']:,.2f}\n"

    keyboard = [[InlineKeyboardButton("Voltar", callback_data="my_monitors")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de texto do usuario."""
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    state = await get_user_state(user_id)

    if not state:
        await update.message.reply_text(
            "Use /start para comecar!",
            parse_mode="Markdown"
        )
        return

    current_state = state["state"]
    data = state["data"]

    keyboard = [[InlineKeyboardButton("Cancelar", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Processar origem - buscar aeroportos
    if current_state in [STATE_ORIGIN, f"search_{STATE_ORIGIN}"]:
        await update.message.reply_text("Buscando aeroportos...")

        airports = flight_service.search_airports(text)

        if not airports:
            await update.message.reply_text(
                f"Nenhum aeroporto encontrado para '{text}'.\n\n"
                "Tente outro nome de cidade.",
                reply_markup=reply_markup
            )
            return

        # Salvar aeroportos encontrados
        data["airports"] = {a["code"]: f"{a['city']} - {a['name']}" for a in airports}
        await save_user_state(user_id, STATE_ORIGIN_SELECT, data)

        # Criar botoes com aeroportos
        keyboard = []
        for airport in airports:
            label = f"{airport['code']} - {airport['city']}"
            if airport['name']:
                label = f"{airport['code']} - {airport['name']}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"origin_{airport['code']}")])

        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="main_menu")])

        await update.message.reply_text(
            f"*Aeroportos encontrados para '{text}':*\n\n"
            "Escolha o aeroporto de origem:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # Processar destino - buscar aeroportos
    elif current_state in [STATE_DESTINATION, f"search_{STATE_DESTINATION}"]:
        await update.message.reply_text("Buscando aeroportos...")

        airports = flight_service.search_airports(text)

        if not airports:
            await update.message.reply_text(
                f"Nenhum aeroporto encontrado para '{text}'.\n\n"
                "Tente outro nome de cidade.",
                reply_markup=reply_markup
            )
            return

        # Salvar aeroportos encontrados
        data["airports"] = {a["code"]: f"{a['city']} - {a['name']}" for a in airports}
        await save_user_state(user_id, STATE_DESTINATION_SELECT, data)

        # Criar botoes com aeroportos
        keyboard = []
        for airport in airports:
            label = f"{airport['code']} - {airport['city']}"
            if airport['name']:
                label = f"{airport['code']} - {airport['name']}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"dest_{airport['code']}")])

        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="main_menu")])

        await update.message.reply_text(
            f"*Aeroportos encontrados para '{text}':*\n\n"
            "Escolha o aeroporto de destino:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # Processar data de ida
    elif current_state in [STATE_DEPARTURE_DATE, f"search_{STATE_DEPARTURE_DATE}"]:
        try:
            date = datetime.strptime(text, "%d/%m/%Y")
            if date.date() < datetime.now().date():
                await update.message.reply_text(
                    "A data nao pode ser no passado!",
                    reply_markup=reply_markup
                )
                return

            data["departure_date"] = date.strftime("%Y-%m-%d")
            is_search = current_state.startswith("search_")
            next_state = f"search_{STATE_RETURN_DATE}" if is_search else STATE_RETURN_DATE
            await save_user_state(user_id, next_state, data)

            keyboard = [
                [InlineKeyboardButton("So ida (sem volta)", callback_data="skip_return")],
                [InlineKeyboardButton("Cancelar", callback_data="main_menu")]
            ]

            await update.message.reply_text(
                f"Data de ida: *{text}*\n\n"
                "Digite a *data de volta* (DD/MM/AAAA) ou pule para so ida:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        except ValueError:
            await update.message.reply_text(
                "Formato invalido. Use DD/MM/AAAA (ex: 25/01/2025)",
                reply_markup=reply_markup
            )

    # Processar data de volta
    elif current_state in [STATE_RETURN_DATE, f"search_{STATE_RETURN_DATE}"]:
        try:
            date = datetime.strptime(text, "%d/%m/%Y")
            departure = datetime.strptime(data["departure_date"], "%Y-%m-%d")

            if date.date() < departure.date():
                await update.message.reply_text(
                    "A volta deve ser apos a ida!",
                    reply_markup=reply_markup
                )
                return

            data["return_date"] = date.strftime("%Y-%m-%d")
            is_search = current_state.startswith("search_")
            next_state = f"search_{STATE_ADULTS}" if is_search else STATE_ADULTS
            await save_user_state(user_id, next_state, data)

            # Perguntar quantidade de adultos
            keyboard = [
                [
                    InlineKeyboardButton("1", callback_data="adults_1"),
                    InlineKeyboardButton("2", callback_data="adults_2"),
                    InlineKeyboardButton("3", callback_data="adults_3"),
                    InlineKeyboardButton("4", callback_data="adults_4"),
                ],
                [InlineKeyboardButton("Cancelar", callback_data="main_menu")]
            ]

            await update.message.reply_text(
                f"Data de volta: *{text}*\n\n"
                "*Quantos adultos?*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        except ValueError:
            await update.message.reply_text(
                "Formato invalido. Use DD/MM/AAAA (ex: 30/01/2025)",
                reply_markup=reply_markup
            )

    # Processar preco maximo
    elif current_state == STATE_MAX_PRICE:
        try:
            max_price = float(text.replace(",", ".").replace("R$", "").strip())
            if max_price <= 0:
                raise ValueError()

            data["max_price"] = max_price

            # Criar mensagem fake para reutilizar a funcao
            class FakeQuery:
                message = update.message
                async def edit_message_text(self, *args, **kwargs):
                    await update.message.reply_text(*args, **kwargs)

            await finish_monitor_creation(FakeQuery(), user_id, data)

        except ValueError:
            await update.message.reply_text(
                "Valor invalido. Digite apenas numeros (ex: 1500)",
                reply_markup=reply_markup
            )


async def check_prices(app: Application):
    """Verifica precos de todos os monitoramentos ativos."""
    logger.info("Verificando precos...")

    monitors = await get_all_active_monitors()

    for monitor in monitors:
        try:
            offer = flight_service.get_cheapest_price(
                origin=monitor["origin"],
                destination=monitor["destination"],
                departure_date=monitor["departure_date"],
                return_date=monitor.get("return_date"),
                adults=monitor.get("adults", 1)
            )

            if not offer:
                continue

            # Atualizar preco no banco
            await update_monitor_price(
                monitor["id"],
                offer.price,
                flight_service.format_flight_message(offer)
            )

            # Verificar se deve notificar
            should_notify = False
            notification_reason = ""

            # Notificar se preco caiu
            if monitor["last_price"] and offer.price < monitor["last_price"]:
                diff = monitor["last_price"] - offer.price
                should_notify = True
                notification_reason = f"Preco caiu R$ {diff:,.2f}!"

            # Notificar se atingiu preco maximo desejado
            if monitor["max_price"] and offer.price <= monitor["max_price"]:
                should_notify = True
                notification_reason = f"Preco atingiu sua meta de R$ {monitor['max_price']:,.2f}!"

            if should_notify:
                message = f"""
*ALERTA DE PRECO!*

{notification_reason}

{flight_service.format_flight_message(offer)}
"""
                await app.bot.send_message(
                    chat_id=monitor["chat_id"],
                    text=message,
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Erro ao verificar monitor {monitor['id']}: {e}")

    logger.info(f"Verificacao concluida. {len(monitors)} monitoramentos checados.")


def main():
    """Funcao principal."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[ERRO] TELEGRAM_BOT_TOKEN nao configurado!")
        return

    # Criar aplicacao
    app = Application.builder().token(token).build()

    # Adicionar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Configurar scheduler para verificar precos
    scheduler = AsyncIOScheduler()
    interval = int(os.getenv("CHECK_INTERVAL_MINUTES", 60))
    scheduler.add_job(
        check_prices,
        "interval",
        minutes=interval,
        args=[app]
    )

    async def on_startup(app: Application):
        await init_db()
        scheduler.start()
        logger.info("Bot iniciado!")

    app.post_init = on_startup

    # Rodar bot
    print("[BOT] Iniciando...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
