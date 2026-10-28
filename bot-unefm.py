import os
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Configurar logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()

# Credenciales de Telegram y Trello
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_ID_LIST = os.getenv("TRELLO_ID_LIST")

async def crear_tarjeta_en_trello(nombre_usuario, username, categoria, mensaje):
    url = "https://api.trello.com/1/cards"
    
    # Datos de la tarjeta
    query = {
        'key': TRELLO_API_KEY,
        'token': TRELLO_TOKEN,
        'idList': TRELLO_ID_LIST,
        'name': f"[{categoria}] - {nombre_usuario}",
        'desc': f"**Usuario de Telegram:** @{username or 'Sin alias'}\n"
                f"**Nombre:** {nombre_usuario}\n"
                f"**Categoría:** {categoria}\n\n"
                f"**Descripción del problema:**\n{mensaje}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, params=query)
        if response.status_code == 200:
            return response.json() # Retorna los datos de la tarjeta creada (incluye URL)
        else:
            logging.error(f"Error al crear tarjeta en Trello: {response.text}")
            return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    keyboard = [
        [InlineKeyboardButton("🛠️ Problema Técnico", callback_data="Técnico")],
        [InlineKeyboardButton("💳 Recuperar accesso", callback_data="Acceso")],
        [InlineKeyboardButton("👤 Hablar con Soporte", callback_data="General")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"¡Hola, {user_name}! Bienvenido al **Centro de Soporte**. Selecciona una categoría:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Guardamos la categoría seleccionada en la memoria del chat del usuario
    categoria = query.data
    context.user_data['categoria'] = categoria
    
    await query.edit_message_text(
        text=f"Has seleccionado: **{categoria}**.\n\n"
             "Por favor, envíanos a continuación el mensaje detallando tu consulta o inconveniente. Generaremos un ticket automáticamente.",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mensaje_texto = update.message.text
    
    # Obtenemos la categoría que eligió antes (si no eligió, por defecto es "General")
    categoria = context.user_data.get('categoria', 'General')
    
    # Indicamos al usuario que estamos procesando
    wait_msg = await update.message.reply_text("🔄 Registrando tu caso en nuestro sistema...")
    
    # Creamos la tarjeta en Trello
    tarjeta = await crear_tarjeta_en_trello(
        nombre_usuario=user.first_name,
        username=user.username,
        categoria=categoria,
        mensaje=mensaje_texto
    )
    
    if tarjeta:
        await wait_msg.edit_text(
            "✅ **¡Ticket creado con éxito!**\n\n"
            "Nuestro equipo técnico ha recibido tu reporte y le dará seguimiento pronto.",
            parse_mode="Markdown"
        )
    else:
        await wait_msg.edit_text(
            "⚠️ Hubo un pequeño error al registrar tu solicitud en el sistema de tickets. Por favor, intenta de nuevo más tarde."
        )

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("El bot de soporte con integración a Trello está corriendo...")
    application.run_polling()

if __name__ == '__main__':
    main()