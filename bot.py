import sqlite3
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==========================
# CONFIG
# ==========================
TOKEN = "6344483879:AAFfWIZTQvokTbfOFTiCrjTcMi9hNgzV3hY"
CHANNEL_STORAGE = "@savefenix"
CHANNEL_CATALOG = "@gamespcfenix"
BOT_USERNAME = "FortuneRPG_bot"

# ==========================
# BASE DE DATOS
# ==========================
db = sqlite3.connect("games.db", check_same_thread=False)
cur = db.cursor()

def init_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS games(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
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
# START
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        game_id = context.args[0]
        cur.execute("SELECT name FROM games WHERE id=?", (game_id,))
        game = cur.fetchone()
        if not game:
            await update.message.reply_text("❌ Juego no encontrado")
            return

        # Obtener archivos y ordenarlos alfabéticamente
        cur.execute("SELECT file_id FROM files WHERE game_id=?", (game_id,))
        files = cur.fetchall()
        files_sorted = sorted(files, key=lambda x: x[0])  # ordenar por file_id (puedes cambiar a nombre si lo guardas)

        await update.message.reply_text(f"📦 Enviando {game[0]} ({len(files_sorted)} archivos)...")
        for f in files_sorted:
            try:
                await context.bot.send_document(update.message.chat_id, f[0])
                await asyncio.sleep(1.2)
            except Exception as e:
                await update.message.reply_text(f"Error al enviar archivo: {e}")
    else:
        await update.message.reply_text("👋 Usa /subir para agregar un juego")

# ==========================
# SUBIR
# ==========================
async def subir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    upload_state[chat_id] = {
        "step": "nombre",
        "files": [],
    }
    await update.message.reply_text("✏️ Escribe el nombre del juego:")

# ==========================
# MENSAJES
# ==========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in upload_state:
        return

    state = upload_state[chat_id]

    if state["step"] == "nombre":
        state["name"] = update.message.text.strip()
        state["step"] = "imagen"
        await update.message.reply_text("📷 Envía la imagen principal del juego:")
        return

    if state["step"] == "imagen":
        if update.message.photo:
            state["image_file_id"] = update.message.photo[-1].file_id
            state["step"] = "archivos"
            await update.message.reply_text("📦 Envía los archivos del juego:")
        else:
            await update.message.reply_text("❌ Envía una foto válida")
        return

    if state["step"] == "archivos":
        if update.message.document:
            state["files"].append(update.message.document.file_id)
            await update.message.reply_text(f"✅ Archivo agregado ({len(state['files'])})")
        else:
            await update.message.reply_text("❌ Envía un archivo o usa /ok para finalizar")
        return

# ==========================
# FINALIZAR SUBIDA
# ==========================
async def ok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in upload_state:
        await update.message.reply_text("❌ No hay subida activa")
        return

    state = upload_state[chat_id]
    name = state["name"]
    image = state["image_file_id"]
    files = state["files"]

    # Guardar juego en DB
    cur.execute(
        "INSERT OR IGNORE INTO games(name,image_file_id) VALUES(?,?)",
        (name, image)
    )
    db.commit()
    cur.execute("SELECT id FROM games WHERE name=?", (name,))
    game_id = cur.fetchone()[0]

    for f in files:
        cur.execute("INSERT INTO files(game_id,file_id) VALUES(?,?)", (game_id, f))
    db.commit()

    # Ordenar archivos alfabéticamente antes de enviarlos al canal
    ordered_files = sorted(files)
    await update.message.reply_text("⬆️ Subiendo archivos al canal de storage...")
    for f in ordered_files:
        try:
            await context.bot.send_document(CHANNEL_STORAGE, f)
            await asyncio.sleep(1.2)
        except Exception as e:
            await update.message.reply_text(f"Error al enviar archivo: {e}")

    # Publicar en catálogo con botón START
    keyboard = [[InlineKeyboardButton("▶ START", url=f"https://t.me/{BOT_USERNAME}?start={game_id}")]]
    await context.bot.send_photo(
        CHANNEL_CATALOG,
        image,
        caption=f"🎮 {name}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("✅ Juego publicado correctamente")
    del upload_state[chat_id]

# ==========================
# COMANDO /DB
# ==========================
async def db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        await update.message.reply_text("❌ Este comando solo funciona en privado.")
        return

    await update.message.reply_text("⏳ Escaneando canal de storage y agregando a la base de datos...")

    try:
        chat = await context.bot.get_chat(CHANNEL_STORAGE)
        async for message in chat.iter_history(limit=500):
            if message.document:
                file_id = message.document.file_id
                game_name = message.caption or f"Juego {file_id[:8]}"
                cur.execute("INSERT OR IGNORE INTO games(name,image_file_id) VALUES(?,?)", (game_name, None))
                db.commit()
                cur.execute("SELECT id FROM games WHERE name=?", (game_name,))
                game_id = cur.fetchone()[0]
                cur.execute("INSERT INTO files(game_id,file_id) VALUES(?,?)", (game_id, file_id))
                db.commit()
        await update.message.reply_text("✅ Todos los archivos del canal se agregaron a la base de datos.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ==========================
# MAIN
# ==========================
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).connect_timeout(30).read_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subir", subir))
    app.add_handler(CommandHandler("ok", ok))
    app.add_handler(CommandHandler("db", db_command))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("BOT RUNNING 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
