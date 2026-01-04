import os
import logging
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from groq import Groq   # ← NUEVO IMPORT

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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")   # ← NUEVA VARIABLE

if not TELEGRAM_TOKEN:
    raise ValueError("Falta la variable de entorno TELEGRAM_TOKEN")

if not GROQ_API_KEY:
    raise ValueError("Falta la variable de entorno GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)   # ← NUEVO CLIENTE

# ==========================
# Textos multilingües
# ==========================

MENSAJES = {
    "es": {
        "start": (
            "👋 Hola, soy *PDF-Olimpus_bot*, tu asistente premium para procesar y resumir PDFs.\n\n"
            "Envíame un archivo PDF y te ayudaré con:\n"
            "• Resumen corto\n"
            "• Resumen largo\n"
            "• Puntos clave\n"
            "• Explicación simple\n"
            "• Traducción\n\n"
            "Solo envía el PDF como documento (no como foto)."
        ),
        "ayuda": (
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
        ),
        "pide_pdf": "Envíame un archivo PDF como *documento* para poder procesarlo.",
        "recibiendo_pdf": "📥 Recibiendo tu PDF, dame un momento...",
        "no_texto_pdf": "No pude extraer texto del PDF. Puede ser un PDF escaneado.",
        "idioma_detectado": "✅ PDF procesado. Idioma detectado: *{idioma}*.",
        "que_hacer": "¿Qué quieres hacer con este PDF?",
        "procesando": "🧠 Procesando tu solicitud...",
        "error_lectura": "Ocurrió un error al leer el PDF.",
        "error_ia": "Ocurrió un error al procesar el texto con IA.",
        "reenviar_pdf": "No encontré el contenido del PDF. Envíalo de nuevo.",
        "solo_pdf_doc": "Por favor envía un archivo en formato PDF.",

        "trad_que": "¿Qué deseas traducir?",
        "trad_pdf_completo": "📄 Traducir PDF completo",
        "trad_resumen": "📝 Traducir solo el resumen",
        "elige_idioma_trad": "Elige el idioma de destino:",
        "trad_pdf_procesando": "🌐 Traduciendo PDF completo, esto puede tomar un momento...",
        "trad_resumen_procesando": "🌐 Traduciendo el resumen...",
    },

    "en": {
        "start": (
            "👋 Hi, I'm *PDF-Olimpus_bot*, your premium assistant for processing and summarizing PDFs.\n\n"
            "Send me a PDF file and I will help you with:\n"
            "• Short summary\n"
            "• Long summary\n"
            "• Key points\n"
            "• Simple explanation\n"
            "• Translation\n\n"
            "Just send the PDF as a document (not as a photo)."
        ),
        "ayuda": (
            "📘 *Help*\n\n"
            "1️⃣ Send a PDF as a document.\n"
            "2️⃣ The bot will read its content.\n"
            "3️⃣ It will ask what you want to do:\n"
            "   • Short summary\n"
            "   • Long summary\n"
            "   • Key points\n"
            "   • Simple explanation\n"
            "   • Translate to Spanish\n\n"
            "If the PDF is very large, the bot will automatically split it into parts."
        ),
        "pide_pdf": "Send me a PDF file as a *document* so I can process it.",
        "recibiendo_pdf": "📥 Receiving your PDF, give me a moment...",
        "no_texto_pdf": "I couldn't extract text from this PDF. It may be a scanned document.",
        "idioma_detectado": "✅ PDF processed. Detected language: *{idioma}*.",
        "que_hacer": "What would you like to do with this PDF?",
        "procesando": "🧠 Processing your request...",
        "error_lectura": "An error occurred while reading the PDF.",
        "error_ia": "An error occurred while processing the text with AI.",
        "reenviar_pdf": "I couldn't find the PDF content. Please send it again.",
        "solo_pdf_doc": "Please send a file in PDF format.",

        "trad_que": "What would you like to translate?",
        "trad_pdf_completo": "📄 Translate full PDF",
        "trad_resumen": "📝 Translate only the summary",
        "elige_idioma_trad": "Choose the target language:",
        "trad_pdf_procesando": "🌐 Translating full PDF, this may take a moment...",
        "trad_resumen_procesando": "🌐 Translating the summary...",
    },

    "ru": {
        "start": (
            "👋 Привет, я *PDF-Olimpus_bot*, твой премиум‑ассистент для обработки и резюмирования PDF.\n\n"
            "Отправь мне PDF‑файл, и я помогу тебе с:\n"
            "• Кратким резюме\n"
            "• Подробным резюме\n"
            "• Ключевыми моментами\n"
            "• Простым объяснением\n"
            "• Переводом\n\n"
            "Отправляй PDF как документ (не как фото)."
        ),
        "ayuda": (
            "📘 *Помощь*\n\n"
            "1️⃣ Отправь PDF как документ.\n"
            "2️⃣ Бот прочитает его содержимое.\n"
            "3️⃣ Он спросит, что ты хочешь сделать:\n"
            "   • Краткое резюме\n"
            "   • Подробное резюме\n"
            "   • Ключевые моменты\n"
            "   • Простое объяснение\n"
            "   • Перевод на испанский\n\n"
            "Если PDF очень большой, бот автоматически разделит его на части."
        ),
        "pide_pdf": "Отправь мне PDF‑файл как *документ*, чтобы я мог его обработать.",
        "recibiendo_pdf": "📥 Получаю твой PDF, подожди немного...",
        "no_texto_pdf": "Мне не удалось извлечь текст из этого PDF. Возможно, это скан.",
        "idioma_detectado": "✅ PDF обработан. Обнаруженный язык: *{idioma}*.",
        "que_hacer": "Что ты хочешь сделать с этим PDF?",
        "procesando": "🧠 Обрабатываю твой запрос...",
        "error_lectura": "Произошла ошибка при чтении PDF.",
        "error_ia": "Произошла ошибка при обработке текста с помощью ИИ.",
        "reenviar_pdf": "Не удалось найти содержимое PDF. Пожалуйста, отправь его ещё раз.",
        "solo_pdf_doc": "Пожалуйста, отправь файл в формате PDF.",

        "trad_que": "Что вы хотите перевести?",
        "trad_pdf_completo": "📄 Перевести весь PDF",
        "trad_resumen": "📝 Перевести только резюме",
        "elige_idioma_trad": "Выберите язык перевода:",
        "trad_pdf_procesando": "🌐 Перевожу весь PDF, это может занять время...",
        "trad_resumen_procesando": "🌐 Перевожу резюме...",
    },
}
# ==========================
# BOTONES MULTILINGÜES
# ==========================

BOTONES = {
    "es": {
        "resumen_corto": "📄 Resumen corto",
        "resumen_largo": "📘 Resumen largo",
        "puntos_clave": "⭐ Puntos clave",
        "explicacion_simple": "👶 Explicación simple",
        "traducir": "🌎 Traducir",
    },
    "en": {
        "resumen_corto": "📄 Short summary",
        "resumen_largo": "📘 Long summary",
        "puntos_clave": "⭐ Key points",
        "explicacion_simple": "👶 Simple explanation",
        "traducir": "🌎 Translate",
    },
    "ru": {
        "resumen_corto": "📄 Краткое резюме",
        "resumen_largo": "📘 Подробное резюме",
        "puntos_clave": "⭐ Ключевые моменты",
        "explicacion_simple": "👶 Простое объяснение",
        "traducir": "🌎 Перевести",
    },
}


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
# Funciones de idioma
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


def detectar_idioma_texto(texto: str) -> str:
    try:
        muestra = texto[:4000]

        respuesta = client.chat.completions.create(
            model="llama3-8b-8192",
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
        )

        idioma = respuesta.choices[0].message.content.strip().lower()
        if "\n" in idioma:
            idioma = idioma.split("\n")[0].strip().lower()

        return idioma

    except Exception as e:
        logger.error(f"Error al detectar idioma del PDF: {e}")
        return "desconocido"


def detectar_idioma_usuario(texto: str) -> str:
    try:
        muestra = texto[:1000]

        respuesta = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Detecta el idioma del usuario y responde solo con: es, en o ru."
                    ),
                },
                {"role": "user", "content": muestra},
            ],
        )

        codigo = respuesta.choices[0].message.content.strip().lower()
        if codigo not in ["es", "en", "ru"]:
            codigo = "es"

        return codigo

    except Exception as e:
        logger.error(f"Error al detectar idioma del usuario: {e}")
        return "es"


def obtener_idioma_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("user_lang")
    if lang in ["es", "en", "ru"]:
        return lang

    texto = None
    if update.message and update.message.text:
        texto = update.message.text

    if not texto:
        context.user_data["user_lang"] = "es"
        return "es"

    lang = detectar_idioma_usuario(texto)
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
# Funciones de IA (Groq)
# ==========================

def dividir_texto(texto, tamaño=3000):
    return [texto[i:i + tamaño] for i in range(0, len(texto), tamaño)]


def resumir_por_partes(texto, prompt):
    partes = dividir_texto(texto)

    if not partes:
        return "No se pudo extraer texto del PDF."

    resúmenes = []

    for parte in partes:
        respuesta = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en análisis y resumen de textos."},
                {"role": "user", "content": prompt + "\n\n" + parte},
            ],
        )
        resúmenes.append(respuesta.choices[0].message.content)

    combinado = "\n\n".join(resúmenes)

    respuesta_final = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en síntesis de información."},
            {"role": "user", "content": "Combina de manera clara y coherente estos resúmenes parciales:\n\n" + combinado},
        ],
    )

    return respuesta_final.choices[0].message.content


def traducir_por_partes(texto, idioma_destino):
    partes = dividir_texto(texto, tamaño=3000)
    traducciones = []

    for parte in partes:
        try:
            respuesta = client.chat.completions.create(
                model="llama3-8b-8192",
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
            )
            traducciones.append(respuesta.choices[0].message.content)

        except Exception as e:
            traducciones.append(f"[Error al traducir una parte: {e}]")

    return "\n\n".join(traducciones)

# ==========================
# Handlers
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = obtener_idioma_usuario(update, context)
    await update.message.reply_markdown(t(lang, "start"))


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = obtener_idioma_usuario(update, context)
    await update.message.reply_markdown(t(lang, "ayuda"))


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = obtener_idioma_usuario(update, context)
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

        idioma_nombre = detectar_idioma_texto(texto)
        context.user_data["pdf_lang_name"] = idioma_nombre
        context.user_data["pdf_lang"] = normalizar_idioma_nombre(idioma_nombre)

        await update.message.reply_text(
            t(lang, "idioma_detectado", idioma=idioma_nombre),
            parse_mode="Markdown",
        )

        # 🔥 BOTONES MULTILINGÜES
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

    # 🌎 Submenú principal de traducción
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

    # 🌐 Menú de idiomas para TRADUCIR PDF COMPLETO
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

    # 🌐 Menú de idiomas para TRADUCIR SOLO EL RESUMEN
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

    # 🔥 Traducción del PDF completo
    if accion.startswith("trad_pdf_"):
        idioma_destino = accion.replace("trad_pdf_", "")
        texto = context.user_data.get("pdf_text", "")

        if not texto:
            await query.edit_message_text(t(lang, "reenviar_pdf"))
            return

        await query.edit_message_text(t(lang, "trad_pdf_procesando"))

        try:
            resultado = traducir_por_partes(texto, idioma_destino)
            if len(resultado) > 4000:
                resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"
            await query.edit_message_text(resultado)

        except Exception as e:
            logger.error(f"Error al traducir PDF: {e}")
            await query.edit_message_text(t(lang, "error_ia"))
        return

    # 🔥 Traducción del resumen
    if accion.startswith("trad_resumen_"):
        idioma_destino = accion.replace("trad_resumen_", "")
        resumen = context.user_data.get("last_summary", "")

        if not resumen:
            await query.edit_message_text(t(lang, "reenviar_pdf"))
            return

        await query.edit_message_text(t(lang, "trad_resumen_procesando"))

        try:
            resultado = traducir_por_partes(resumen, idioma_destino)
            if len(resultado) > 4000:
                resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"
            await query.edit_message_text(resultado)

        except Exception as e:
            logger.error(f"Error al traducir resumen: {e}")
            await query.edit_message_text(t(lang, "error_ia"))
        return

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
        resultado = resumir_por_partes(texto, prompt)
        context.user_data["last_summary"] = resultado

        if len(resultado) > 4000:
            resultado = resultado[:3990] + "\n\n[Texto recortado por longitud]"

        await query.edit_message_text(f"{titulo}:\n\n{resultado}")

    except Exception as e:
        logger.error(f"Error con IA: {e}")   # ← CORREGIDO
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
