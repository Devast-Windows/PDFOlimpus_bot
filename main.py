import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from pypdf import PdfReader
from openai import OpenAI

# Cargar variables del .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- Función para resumir texto con OpenAI ---
def resumir_texto(texto):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Resume el siguiente texto de forma clara y concisa."},
            {"role": "user", "content": texto}
        ]
    )
    return response.choices[0].message.content

# --- Comando /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola, soy tu bot para resumir PDFs.\n\n"
        "Envíame un PDF y te daré un resumen automático."
    )

# --- Manejar PDFs ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "temp.pdf"
    await file.download_to_drive(file_path)

    # Extraer texto del PDF
    reader = PdfReader(file_path)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()

    # Resumir con IA
    resumen = resumir_texto(texto)

    await update.message.reply_text("📄 *Resumen del PDF:*\n\n" + resumen, parse_mode="Markdown")

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    print("Bot corriendo...")

    app.run_polling()
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "temp.pdf"
    await file.download_to_drive(file_path)

    reader = PdfReader(file_path)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()

    context.user_data["pdf_text"] = texto

    keyboard = [
        [InlineKeyboardButton("📄 Resumen corto", callback_data="resumen_corto")],
        [InlineKeyboardButton("📘 Resumen largo", callback_data="resumen_largo")],
        [InlineKeyboardButton("⭐ Puntos clave", callback_data="puntos_clave")],
        [InlineKeyboardButton("👶 Explicación simple", callback_data="explicacion_simple")],
        [InlineKeyboardButton("🌎 Traducir", callback_data="traducir")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿Qué quieres hacer con este PDF?", reply_markup=reply_markup)
    from telegram.ext import CallbackQueryHandler

app.add_handler(CallbackQueryHandler(botones_pdf))
async def botones_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    texto = context.user_data.get("pdf_text", "")

    if not texto:
        await query.edit_message_text("No pude encontrar el texto del PDF.")
        return

    accion = query.data

    if accion == "resumen_corto":
        prompt = "Resume este texto en 5 líneas:"
    elif accion == "resumen_largo":
        prompt = "Haz un resumen detallado de este texto:"
    elif accion == "puntos_clave":
        prompt = "Extrae los puntos clave del texto en viñetas:"
    elif accion == "explicacion_simple":
        prompt = "Explica este texto como si fuera para un niño de 10 años:"
    elif accion == "traducir":
        prompt = "Traduce este texto al español de forma clara y natural:"
    else:
        prompt = "Resume este texto:"

    respuesta = resumir_texto(prompt + "\n\n" + texto)

    await query.edit_message_text(respuesta)
    
