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