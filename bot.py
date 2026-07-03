from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime
import pandas as pd

TOKEN = "ISI_TOKEN_KAMU"

# koneksi database
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tiket (
    user_id TEXT,
    tanggal TEXT,
    tiket TEXT,
    kategori TEXT,
    bobot REAL
)
""")
conn.commit()

# kategori
BOBOT = {
    "REGULER_HSI": 2,
    "REGULER_OLO": 4,
    "REGULER_WMS": 4,
    "REGULER_NODEB": 4,
    "PSB": 4.3,
    "INFRACARE": 2,
    "GAMAS_DISTRIBUSI": 4,
    "GAMAS_FEEDER": 10,
    "GAMAS_ODP": 3,
    "GAMAS_ODC": 18,
    "DATIN": 2.4,
    "VALIN": 0.5
}

def menu():
    return ReplyKeyboardMarkup([
        ["➕ Tambah Tiket"],
        ["📊 Harian", "📅 Mingguan", "📆 Bulanan"],
        ["📥 Export Excel"]
    ], resize_keyboard=True)

def kategori_menu():
    return ReplyKeyboardMarkup([
        ["REGULER_HSI", "REGULER_OLO"],
        ["REGULER_WMS", "REGULER_NODEB"],
        ["PSB", "INFRACARE"],
        ["GAMAS_DISTRIBUSI", "GAMAS_FEEDER"],
        ["GAMAS_ODP", "GAMAS_ODC"],
        ["DATIN", "VALIN"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Tiket PRO Aktif!", reply_markup=menu())

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.message.from_user.id)

    if text == "➕ Tambah Tiket":
        context.user_data["step"] = "tiket"
        await update.message.reply_text("Masukkan ID Tiket:")
        return

    if context.user_data.get("step") == "tiket":
        context.user_data["tiket"] = text
        context.user_data["step"] = "kategori"
        await update.message.reply_text("Pilih kategori:", reply_markup=kategori_menu())
        return

    if context.user_data.get("step") == "kategori":
        if text not in BOBOT:
            await update.message.reply_text("Kategori tidak valid!")
            return

        tiket = context.user_data["tiket"]
        kategori = text
        bobot = BOBOT[kategori]
        tanggal = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("INSERT INTO tiket VALUES (?, ?, ?, ?, ?)",
                       (user_id, tanggal, tiket, kategori, bobot))
        conn.commit()

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ {tiket}\n{kategori}\nBobot: {bobot}",
            reply_markup=menu()
        )
        return

    if text == "📊 Harian":
        await laporan(update, user_id, "harian")
    elif text == "📅 Mingguan":
        await laporan(update, user_id, "mingguan")
    elif text == "📆 Bulanan":
        await laporan(update, user_id, "bulanan")
    elif text == "📥 Export Excel":
        await export_excel(update, user_id)

async def laporan(update, user_id, tipe):
    df = pd.read_sql_query("SELECT * FROM tiket WHERE user_id=?", conn, params=(user_id,))
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    now = datetime.now()

    if tipe == "harian":
        df = df[df["tanggal"].dt.date == now.date()]
    elif tipe == "mingguan":
        df = df[df["tanggal"] >= now - pd.Timedelta(days=7)]
    elif tipe == "bulanan":
        df = df[df["tanggal"].dt.strftime("%Y-%m") == now.strftime("%Y-%m")]

    if df.empty:
        await update.message.reply_text("Belum ada data", reply_markup=menu())
        return

    text = f"📊 {tipe.upper()}\n\n"
    text += f"Tiket: {len(df)}\n"
    text += f"Nilai: {df['bobot'].sum()}\n\n"

    for k, v in df["kategori"].value_counts().items():
        text += f"{k}: {v}\n"

    await update.message.reply_text(text, reply_markup=menu())

async def export_excel(update, user_id):
    df = pd.read_sql_query("SELECT * FROM tiket WHERE user_id=?", conn, params=(user_id,))

    if df.empty:
        await update.message.reply_text("Tidak ada data")
        return

    file_name = f"laporan_{user_id}.xlsx"
    df.to_excel(file_name, index=False)

    await update.message.reply_document(open(file_name, "rb"))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

import os

if __name__ == "__main__":
    app.run_polling()