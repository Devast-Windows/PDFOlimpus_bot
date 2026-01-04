import os
import logging
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from groq import Groq

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
# CONFIGURACIÓN BÁSICA
# ==========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("Falta la variable de entorno TELEGRAM_TOKEN")

if not GROQ_API_KEY:
    raise ValueError("Falta la variable de entorno GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)


# ==========================
# TEXTOS MULTILINGÜES
# ==========================

MENSAJES = {
    "es": {
        "start": "👋 Hola, soy *PDF‑Olimpus_bot*. Envíame un PDF para comenzar.",
        "ayuda": "📘 Envíame un PDF y te daré resúmenes, traducciones y explicaciones.",
        "solo_pdf_doc": "⚠️ Solo acepto archivos PDF.",
        "recibiendo_pdf": "📥 Recibiendo PDF...",
        "no_texto_pdf": "⚠️ No pude extraer texto del PDF.",
        "idioma_detectado": "🌎 Idioma detectado: *{idioma}*",
        "que_hacer": "¿Qué deseas hacer?",
        "reenviar_pdf": "⚠️ Por favor envía nuevamente el PDF.",
        "trad_pdf_procesando": "🌐 Traduciendo PDF completo...",
        "trad_resumen_procesando": "🌐 Traduciendo resumen...",
        "elige_idioma_trad": "🌍 Elige el idioma de destino:",
        "trad_que": "¿Qué deseas traducir?",
        "procesando": "⏳ Procesando...",
        "error_lectura": "❌ Error al leer el PDF.",
        "error_ia": "❌ Error con la IA. Intenta nuevamente.",
    },
    "en": {
        "start": "👋 Hello, I'm *PDF‑Olimpus_bot*. Send me a PDF to begin.",
        "ayuda": "📘 Send me a PDF and I will summarize or translate it.",
        "solo_pdf_doc": "⚠️ I only accept PDF files.",
        "recibiendo_pdf": "📥 Receiving PDF...",
        "no_texto_pdf": "⚠️ I couldn't extract text from the PDF.",
        "idioma_detectado": "🌎 Detected language: *{idioma}*",
        "que_hacer": "What would you like to do?",
        "reenviar_pdf": "⚠️ Please send the PDF again.",
        "trad_pdf_procesando": "🌐 Translating full PDF...",
        "trad_resumen_procesando": "🌐 Translating summary...",
        "elige_idioma_trad": "🌍 Choose target language:",
        "trad_que": "What do you want to translate?",
        "procesando": "⏳ Processing...",
        "error_lectura": "❌ Error reading PDF.",
        "error_ia": "❌ AI error. Try again.",
    },
    "ru": {
        "start": "👋 Привет, я *PDF‑Olimpus_bot*. Отправь мне PDF.",
        "ayuda": "📘 Отправь PDF, и я сделаю перевод или резюме.",
        "solo_pdf_doc": "⚠️ Я принимаю только PDF.",
        "recibiendo_pdf": "📥 Получаю PDF...",
        "no_texto_pdf": "⚠️ Не удалось извлечь текст.",
        "idioma_detectado": "🌎 Обнаруженный язык: *{idioma}*",
        "que_hacer": "Что вы хотите сделать?",
        "reenviar_pdf": "⚠️ Пожалуйста, отправьте PDF снова.",
        "trad_pdf_procesando": "🌐 Перевожу весь PDF...",
        "trad_resumen_procesando": "🌐 Перевожу резюме...",
        "elige_idioma_trad": "🌍 Выберите язык:",
        "trad_que": "Что вы хотите перевести?",
        "procesando": "⏳ Обработка...",
        "error_lectura": "❌ Ошибка чтения PDF.",
        "error_ia": "❌ Ошибка ИИ. Попробуйте снова.",
    },
}

BOTONES = {
    "es": {
        "resumen_corto": "📄 Resumen corto",
        "resumen_largo": "📘 Resumen largo",
        "puntos_clave": "⭐ Puntos clave",
        "explicacion_simple": "👶 Explicación simple",
        "traducir": "🌍 Traducir",
    },
    "en": {
        "resumen_corto": "📄 Short summary",
        "resumen_largo": "📘 Long summary",
        "puntos_clave": "⭐ Key points",
        "explicacion_simple": "👶 Simple explanation",
        "traducir": "🌍 Translate",
    },
    "ru": {
        "resumen_corto": "📄 Краткое резюме",
        "resumen_largo": "📘 Подробное резюме",
        "puntos_clave": "⭐ Ключевые моменты",
        "explicacion_simple": "👶 Простое объяснение",
        "traducir": "🌍 Перевести",
    },
}


# ==========================
# BOTONES POR IDIOMA
# ==========================

def botones_por_idioma(lang: str):
    b = BOTONES.get(lang, BOTONES["es"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(b["resumen_corto"], callback_data="resumen_corto")],
        [InlineKeyboardButton(b["resumen_largo"], callback_data="resumen_largo")],
        [InlineKeyboardButton(b["puntos_clave"], callback_data="puntos_clave")],
        [InlineKeyboardButton(b["explicacion_simple"], callback_data="explicacion_simple")],
        [InlineKeyboardButton(b["traducir"], callback_data="traducir_menu")],
    ])


# ==========================
# FUNCIONES DE IDIOMA
# ==========================

def normalizar_idioma_nombre(nombre: str) -> str:
    nombre = (nombre or "").strip().lower()

    if any(x in nombre for x in ["español", "castellano", "spanish"]):
        return "es"
    if any(x in nombre for x in ["inglés", "english"]):
        return "en"
    if any(x in nombre for x in ["ruso", "russian", "русский"]):
        return "ru"

    return "es"


async def detectar_idioma_texto(texto: str) -> str:
    try:
        muestra = texto[:4000]

        respuesta = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un detector de idioma. "
                        "Responde solo con el nombre del idioma en español."
                    ),
                },
                {"role": "user", "content": muestra},
            ],
            temperature=0.0,
        )

        idioma = respuesta.choices[0].message.content.strip().lower()
        idioma = idioma.split("\n")[0].strip()

        return idioma

    except Exception as e:
        logger.error(f"Error al detectar idioma del PDF: {e}")
        return "desconocido"


async def detectar_idioma_usuario(texto: str) -> str:
    try:
        muestra = texto[:1000]

        respuesta = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Detecta el idioma del usuario y responde solo con: es, en o ru."
                },
                {"role": "user", "content": muestra},
            ],
            temperature=0.0,
        )

        codigo = respuesta.choices[0].message.content.strip().lower()
        if codigo not in ["es", "en", "ru"]:
            codigo = "es"

        return codigo

    except Exception as e:
        logger.error(f"Error al detectar idioma del usuario: {e}")
        return "es"


async def obtener_idioma_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("user_lang")
    if lang in ["es", "en", "ru"]:
        return lang

    texto = update.message.text if update.message and update.message.text else None

    if not texto:
        context.user_data["user_lang"] = "es"
        return "es"

    lang = await detectar_idioma_usuario(texto)
    context.user_data["user_lang"] = lang
    return lang


def t(lang: str, clave: str, **kwargs) -> str:
    if lang not in MENSAJES:
        lang = "es"
    texto = MENSAJES[lang].get(clave, "")
    if kwargs:
        try:
            texto = texto.format(**kwargs)
        except:
            pass
    return texto


# ==========================
# IA — RESUMEN Y TRADUCCIÓN
# ==========================

def dividir_texto(texto, tamaño=3000):
    return [texto[i:i + tamaño] for i in range(0, len(texto), tamaño)]


async def resumir_por_partes(texto, prompt):
    partes = dividir_texto(texto)

    if not partes:
        return "No se pudo extraer texto del PDF."

    resúmenes = []

    for parte in partes:
        respuesta = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en análisis y resumen de textos."},
                {"role": "user", "content": f"{prompt}\n\n{parte}"},
            ],
            temperature=0.2,
        )
        resúmenes.append(respuesta.choices[0].message.content)

    combinado = "\n\n".join(resúmenes)

    respuesta_final = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en síntesis de información."},
            {"role": "user", "content": f"Combina de manera clara y coherente estos resúmenes parciales:\n\n{combinado}"},
        ],
        temperature=0.2,
    )

    return respuesta_final.choices[0].message.content


async def traducir_por_partes(texto, idioma_destino):
    partes = dividir_texto(texto, tamaño=3000)
    traducciones = []

    for parte in partes:
        try:
            respuesta = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Eres un traductor profesional. Traduce el texto al idioma '{idioma_destino}' "
                            "manteniendo el significado, tono y claridad."
                        ),
                    },
                    {"role": "user", "content": parte},
                ],
                temperature=0.2,
            )
            traducciones.append(respuesta.choices[0].message.content)

        except Exception as e:
            traducciones.append(f"[Error al traducir una parte: {e}]")

    return "\n\n".join(traducciones)


# ==========================
# HANDLERS
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await obtener_idioma_usuario(update, context)
    await update.message.reply_text(t(lang, "start"), parse_mode="Markdown")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await obtener_idioma_usuario(update, context)
    await update.message.reply_text(t(lang, "ayuda"), parse_mode="Markdown")


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await obtener_idioma_usuario(update, context)
    document = update.message.document

    if not document.mime_type or "pdf" not in document.mime_type:
        await update.message.reply_text(t(lang, "solo_pdf_doc"))
        return

    await update.message.reply_text(t(lang, "recibiendo_pdf"))

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
            await update.message.reply_text(t(lang, "no_texto_pdf"))
            return

        context.user_data["pdf_text"] = texto

        idioma_nombre = await detectar_idioma_texto(texto)
        context.user_data["pdf_lang_name"] = idioma_nombre
        context.user_data["pdf_lang"] = normalizar_idioma_nombre(idioma_nombre)

        await update.message.reply_text(
            t(lang, "idioma_detectado", idioma=idioma_nombre),
            parse_mode="Markdown",
        )

        reply_markup = botones_por_idioma(lang)

        await update.message.reply_text(
            t(lang, "que_hacer"),
            reply_markup=reply_markup,
        )

    except Exception as e:
        logger.error(f"Error al procesar el PDF: {e}")
        await update.message.reply_text(t(lang, "error_lectura"))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def botones_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = context.user_data.get("user_lang", "es")
    texto = context.user_data.get("pdf_text", "")

    if not texto:
        await query.edit_message_text(t(lang, "reenviar_pdf"))
        return

    accion = query.data

    # Submenú principal
    if accion == "traducir_menu":
        keyboard = [
            [InlineKeyboardButton(t(lang, "trad_pdf_completo"), callback_data="trad_pdf_menu")],
            [InlineKeyboardButton(t(lang, "trad_resumen"), callback_data="trad_resumen_menu")],
        ]
        await query.edit_message_text(
            t(lang, "trad_que"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Menú de idiomas PDF completo
    if accion == "trad_pdf_menu":
        keyboard = [
            [
                InlineKeyboardButton("🇪🇸 Español", callback_data="trad_pdf_es"),
                InlineKeyboardButton("🇬🇧 English", callback_data="trad_pdf_en"),
            ],
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="trad_pdf_ru"),
                InlineKeyboardButton("🇵🇹 Português", callback_data="trad_pdf_pt"),
            ],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data="trad_pdf_fr"),
                InlineKeyboardButton("🇩🇪 Deutsch", callback_data="trad_pdf_de"),
            ],
        ]
        await query.edit_message_text(
            t(lang, "elige_idioma_trad"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Menú de idiomas resumen
    if accion == "trad_resumen_menu":
        keyboard = [
            [
                InlineKeyboardButton("🇪🇸 Español", callback_data="trad_resumen_es"),
                InlineKeyboardButton("🇬🇧 English", callback_data="trad_resumen_en"),
            ],
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="trad_resumen_ru"),
                InlineKeyboardButton("🇵🇹 Português", callback_data="trad_resumen_pt"),
            ],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data="trad_resumen_fr"),
                InlineKeyboardButton("🇩🇪 Deutsch", callback_data="trad_resumen_de"),
            ],
        ]
        await query.edit_message_text(
            t(lang, "elige_idioma_trad"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Traducción PDF completo
    if accion.startswith("trad_pdf_"):
        idioma_destino = accion.replace("trad_pdf_", "")

        await query.edit_message_text(t(lang, "trad_pdf_procesando"))

        try:
            resultado = await traducir_por_partes(texto, idioma_destino)

            if len(resultado) > 4000:
                resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"

            await query.edit_message_text(resultado)

        except Exception as e:
            logger.error(f"Error al traducir PDF: {e}")
            await query.edit_message_text(t(lang, "error_ia"))
        return

    # Traducción resumen
    if accion.startswith("trad_resumen_"):
        idioma_destino = accion.replace("trad_resumen_", "")
        resumen = context.user_data.get("last_summary", "")

        if not resumen:
            await query.edit_message_text(t(lang, "reenviar_pdf"))
            return

        await query.edit_message_text(t(lang, "trad_resumen_procesando"))

        try:
            resultado = await traducir_por_partes(resumen, idioma_destino)

            if len(resultado) > 4000:
                resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"

            await query.edit_message_text(resultado)

        except Exception as e:
            logger.error(f"Error al traducir resumen:
    # 🔥 Resúmenes y explicaciones
    prompts = {
        "resumen_corto": ("📄 Resumen corto", "Haz un resumen breve y conciso (máximo 5 líneas) de este texto:"),
        "resumen_largo": ("📘 Resumen largo", "Haz un resumen detallado y bien estructurado de este texto:"),
        "puntos_clave": ("⭐ Puntos clave", "Extrae los puntos clave en viñetas:"),
        "explicacion_simple": ("👶 Explicación simple", "Explica este texto como si fuera para un niño de 10 años:"),
    }

    titulo, prompt = prompts.get(accion, ("📄 Resumen", "Haz un resumen de este texto:"))

    await query.edit_message_text(t(lang, "procesando"))

    try:
        resultado = await resumir_por_partes(texto, prompt)
        context.user_data["last_summary"] = resultado

        if len(resultado) > 4000:
            resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"

        await query.edit_message_text(f"{titulo}:\n\n{resultado}")

    except Exception as e:
        logger.error(f"Error con IA: {e}")
        await query.edit_message_text(t(lang, "error_ia"))


async def texto_no_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = obtener_idioma_usuario(update, context)
    await update.message.reply_text(t(lang, "solo_pdf_doc"))
# ==========================
# Función principal
# ==========================

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).request(HTTPXRequest()).build()

    # * Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))

    # * PDF recibido como documento
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    # * Texto que no es PDF
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_no_pdf))

    # * Botones de resumen / traducción
    application.add_handler(CallbackQueryHandler(botones_pdf))

    # * Iniciar el bot
    application.run_polling()

if __name__ == "__main__":
    main()

