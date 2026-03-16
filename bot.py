import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==========================
# CONFIGURACIÓN
# ==========================
TOKEN = "6344483879:AAFfWIZTQvokTbfOFTiCrjTcMi9hNgzV3hY"
CHANNEL_STORAGE = "@savefenix"
CHANNEL_CATALOG = "@gamespcfenix"

# ==========================
# BASE DE DATOS
# ==========================
db = sqlite3.connect("games.db", check_same_thread=False)
cur = db.cursor()

def init_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS games(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        image_file_id TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS files(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        file_id TEXT
    )
    """)
    db.commit()

# ==========================
# ESTADO DE SUBIDA
# ==========================
upload_state = {}

# ==========================
# HANDLERS
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Detecta si hay payload (START del botón)
    if context.args:
        game_id = context.args[0]
        cur.execute("SELECT name FROM games WHERE id=?", (game_id,))
        game = cur.fetchone()
        if not game:
            await update.message.reply_text("❌ Juego no encontrado")
            return
        cur.execute("SELECT file_id FROM files WHERE game_id=?", (game_id,))
        files = cur.fetchall()
        await update.message.reply_text(f"📦 Enviando {game[0]}...")
        for f in files:
            await context.bot.send_document(update.message.chat_id, f[0])
    else:
        await update.message.reply_text("")

async def subir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    upload_state[chat_id] = {"step": "nombre", "files": []}
    await update.message.reply_text("✏️ Escribe el nombre del juego:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in upload_state:
        return

    state = upload_state[chat_id]

    if state["step"] == "nombre":
        state["name"] = update.message.text
        state["step"] = "imagen"
        await update.message.reply_text("📷 Envía la imagen del juego:")
        return

    if state["step"] == "imagen":
        if update.message.photo:
            photo = update.message.photo[-1]
            state["image_file_id"] = photo.file_id
            state["step"] = "archivos"
            await update.message.reply_text("📦 Envía los archivos del juego (puedes enviar varios):")
        else:
            await update.message.reply_text("❌ Por favor envía una foto")
        return

    if state["step"] == "archivos":
        if update.message.document:
            state["files"].append(update.message.document.file_id)
            await update.message.reply_text("Archivo agregado. Envía /ok cuando termines.")
        else:
            await update.message.reply_text("❌ Envía un archivo o /ok para terminar")
        return

async def ok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in upload_state:
        await update.message.reply_text("No hay juego en subida.")
        return

    state = upload_state[chat_id]
    name = state["name"]
    image_file_id = state["image_file_id"]
    files = state["files"]

    # Guardar juego en DB
    cur.execute("INSERT INTO games(name,image_file_id) VALUES(?,?)", (name,image_file_id))
    db.commit()
    game_id = cur.lastrowid

    for f in files:
        cur.execute("INSERT INTO files(game_id,file_id) VALUES(?,?)", (game_id,f))
    db.commit()

    # Enviar archivos al canal de almacenamiento
    for f in files:
        await context.bot.send_document(CHANNEL_STORAGE, f)

    # Publicar en canal catálogo con botón START
    keyboard = [[InlineKeyboardButton("▶ START", url=f"https://t.me/{context.bot.username}?start={game_id}")]]
    await context.bot.send_photo(CHANNEL_CATALOG, image_file_id, caption=f"🎮 {name}", reply_markup=InlineKeyboardMarkup(keyboard))

    await update.message.reply_text("✅ Juego subido y publicado!")
    del upload_state[chat_id]

# ==========================
# MAIN
# ==========================
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).connect_timeout(30).read_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subir", subir))
    app.add_handler(CommandHandler("ok", ok))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()