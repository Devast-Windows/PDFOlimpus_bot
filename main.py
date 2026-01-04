import os
import logging
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from openai import OpenAI

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# ==========================
# Configuración básica
# ==========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("Falta la variable de entorno TELEGRAM_TOKEN")

if not OPENAI_API_KEY:
    raise ValueError("Falta la variable de entorno OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================
# Funciones de OpenAI
# ==========================

def dividir_texto(texto, tamaño=8000):
    return [texto[i:i + tamaño] for i in range(0, len(texto), tamaño)]


def detectar_idioma_texto(texto: str) -> str:
    """
    Detecta el idioma principal de un texto usando OpenAI.
    Devuelve solo el nombre del idioma, por ejemplo: 'español', 'inglés', 'ruso'.
    """
    try:
        # Tomamos solo un fragmento si el texto es muy largo, para no gastar tokens de más
        muestra = texto[:4000]

        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un detector de idioma. "
                        "Tu trabajo es identificar en qué idioma está escrito el siguiente texto. "
                        "Responde únicamente con el nombre del idioma en español, por ejemplo: "
                        "'español', 'inglés', 'ruso', 'portugués', 'francés', 'alemán', 'italiano', "
                        "'chino', 'árabe', etc. Sin explicaciones adicionales."
                    ),
                },
                {
                    "role": "user",
                    "content": muestra,
                },
            ],
        )

        idioma = respuesta.choices[0].message.content.strip().lower()
        # Normalizamos un poco por si devuelve algo raro
        if "\n" in idioma:
            idioma = idioma.split("\n")[0].strip().lower()

        logger.info(f"Idioma detectado para el PDF: {idioma}")
        return idioma

    except Exception as e:
        logger.error(f"Error al detectar idioma: {e}")
        return "desconocido"


def resumir_por_partes(texto, prompt):
    partes = dividir_texto(texto)

    if not partes:
        return "No se pudo extraer texto del PDF."

    resúmenes = []

    for parte in partes:
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en análisis y resumen de textos."},
                {"role": "user", "content": prompt + "\n\n" + parte},
            ],
        )
        resúmenes.append(respuesta.choices[0].message.content)

    combinado = "\n\n".join(resúmenes)

    respuesta_final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en síntesis de información."},
            {"role": "user", "content": "Combina de manera clara y coherente estos resúmenes parciales:\n\n" + combinado},
        ],
    )

    return respuesta_final.choices[0].message.content


# ==========================
# Handlers de Telegram
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "👋 Hola, soy *PDF-Olimpus_bot*, tu asistente premium para procesar y resumir PDFs.\n\n"
        "Envíame un archivo PDF y te ayudaré con:\n"
        "• Resumen corto\n"
        "• Resumen largo\n"
        "• Puntos clave\n"
        "• Explicación simple\n"
        "• Traducción\n\n"
        "Solo envía el PDF como documento (no como foto)."
    )
    await update.message.reply_markdown(mensaje)


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "📘 *Ayuda*\n\n"
        "1️⃣ Envía un PDF como documento.\n"
        "2️⃣ El bot leerá el contenido.\n"
        "3️⃣ Te preguntará qué quieres hacer:\n"
        "   • Resumen corto\n"
        "   • Resumen largo\n"
        "   • Puntos clave\n"
        "   • Explicación simple\n"
        "   • Traducir al español\n\n"
        "Si el PDF es muy grande, el bot lo divide en partes automáticamente."
    )
    await update.message.reply_markdown(mensaje)


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.mime_type or "pdf" not in document.mime_type:
        await update.message.reply_text("Por favor envía un archivo en formato PDF.")
        return

    await update.message.reply_text("📥 Recibiendo tu PDF, dame un momento...")

    file = await document.get_file()
    file_path = "temp.pdf"
    await file.download_to_drive(file_path)

    try:
        reader = PdfReader(file_path)
        texto = ""

        for page in reader.pages:
            extraido = page.extract_text()
            if extraido:
                texto += extraido + "\n"

        if not texto.strip():
            await update.message.reply_text("No pude extraer texto del PDF. Puede ser un PDF escaneado.")
            return

        # Guardamos el texto del PDF
        context.user_data["pdf_text"] = texto

        # 🔍 NUEVO: detectar idioma del PDF y guardarlo
        idioma_pdf = detectar_idioma_texto(texto)
        context.user_data["pdf_lang"] = idioma_pdf

        logger.info(f"Idioma del PDF guardado en user_data: {idioma_pdf}")

        # Te avisamos (por ahora en español, luego lo haremos dinámico)
        await update.message.reply_text(f"✅ PDF procesado. Idioma detectado: *{idioma_pdf}*.", parse_mode="Markdown")

        keyboard = [
            [InlineKeyboardButton("📄 Resumen corto", callback_data="resumen_corto")],
            [InlineKeyboardButton("📘 Resumen largo", callback_data="resumen_largo")],
            [InlineKeyboardButton("⭐ Puntos clave", callback_data="puntos_clave")],
            [InlineKeyboardButton("👶 Explicación simple", callback_data="explicacion_simple")],
            [InlineKeyboardButton("🌎 Traducir al español", callback_data="traducir")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "¿Qué quieres hacer con este PDF?",
            reply_markup=reply_markup,
        )

    except Exception as e:
        logger.error(f"Error al procesar el PDF: {e}")
        await update.message.reply_text("Ocurrió un error al leer el PDF.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def botones_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    texto = context.user_data.get("pdf_text", "")
    idioma_pdf = context.user_data.get("pdf_lang", "desconocido")

    if not texto:
        await query.edit_message_text("No encontré el contenido del PDF. Envíalo de nuevo.")
        return

    accion = query.data

    if accion == "resumen_corto":
        prompt = "Haz un resumen breve y conciso (máximo 5 líneas) de este texto:"
        titulo = "📄 Resumen corto"
    elif accion == "resumen_largo":
        prompt = "Haz un resumen detallado y bien estructurado de este texto:"
        titulo = "📘 Resumen largo"
    elif accion == "puntos_clave":
        prompt = "Extrae los puntos clave en viñetas:"
        titulo = "⭐ Puntos clave"
    elif accion == "explicacion_simple":
        prompt = "Explica este texto como si fuera para un niño de 10 años:"
        titulo = "👶 Explicación simple"
    elif accion == "traducir":
        prompt = "Traduce este texto al español:"
        titulo = "🌎 Traducción al español"
    else:
        prompt = "Haz un resumen de este texto:"
        titulo = "📄 Resumen"

    # Por ahora solo mostramos el idioma detectado en logs,
    # en los siguientes pasos lo usaremos para cambiar idioma de salida.
    logger.info(f"Acción '{accion}' solicitada. Idioma del PDF: {idioma_pdf}")

    await query.edit_message_text("🧠 Procesando tu solicitud...")

    try:
        resultado = resumir_por_partes(texto, prompt)

        if len(resultado) > 4000:
            resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"

        await query.edit_message_text(f"{titulo}:\n\n{resultado}")

    except Exception as e:
        logger.error(f"Error con OpenAI: {e}")
        await query.edit_message_text("Ocurrió un error al procesar el texto con IA.")


async def texto_no_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envíame un archivo PDF como *documento* para poder procesarlo.",
        parse_mode="Markdown",
    )


# ==========================
# Función principal
# ==========================

def main():
    request = HTTPXRequest(read_timeout=30.0)

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))

    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    application.add_handler(CallbackQueryHandler(botones_pdf))

    application.add_handler(MessageHandler(filters.ALL & ~filters.Document.PDF, texto_no_pdf))

    logger.info("Bot iniciando...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
