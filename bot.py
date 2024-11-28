import requests
import mplfinance as mpf
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import os
from crypto_heatmap import send_image_to_telegram  # Mengimpor fungsi dari crypto_heatmap.py
from coin_info import get_token_info  # Mengimpor fungsi dari coin_info.py


# Token bot Telegram
TELEGRAM_TOKEN = '7929212472:AAH5Nkf072mrqw0o0ToC6qAJ-JvoYvhR8ZY'

# ID admin (ganti dengan ID admin Anda)
ADMIN_ID = '6977418544'  # Ganti dengan ID Telegram admin yang valid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fungsi untuk mengonversi market cap ke format yang lebih mudah dibaca
def format_market_cap(value):
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f} T"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f} B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f} M"
    else:
        return f"${value:,.2f}"

# Fungsi untuk mendapatkan data coin dari CoinGecko dengan pengecekan limit
def get_coin_data(coin_id):
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
    response = requests.get(url)
    if response.status_code == 429:
        logger.error("API rate limit reached. Too many requests.")
        return "API limit reached. Please try again later."
    elif response.status_code != 200:
        logger.error(f"Failed to fetch data for {coin_id}. HTTP {response.status_code}")
        return None

    data = response.json()
    if 'market_data' not in data:
        logger.error(f"Missing market_data for {coin_id}")
        return None

    try:
        price = data['market_data']['current_price'].get('usd', 0)
        price_1h = data['market_data']['price_change_percentage_1h_in_currency'].get('usd', 0)
        price_24h = data['market_data']['price_change_percentage_24h_in_currency'].get('usd', 0)
        price_7d = data['market_data']['price_change_percentage_7d_in_currency'].get('usd', 0)
        price_30d = data['market_data']['price_change_percentage_30d_in_currency'].get('usd', 0)
        ath = data['market_data']['ath'].get('usd', 0)
        market_cap = data['market_data']['market_cap'].get('usd', 0)
        volume_24h = data['market_data']['total_volume'].get('usd', 0)
        high_24h = data['market_data']['high_24h'].get('usd', 0)
        low_24h = data['market_data']['low_24h'].get('usd', 0)
        market_cap_rank = data.get('market_cap_rank', 'N/A')

        ath_diff = ((price - ath) / ath) * 100 if ath != 0 else 0

        return {
            'price': price,
            'price_1h': price_1h,
            'price_24h': price_24h,
            'price_7d': price_7d,
            'price_30d': price_30d,
            'ath': ath,
            'ath_diff': ath_diff,
            'market_cap': market_cap,
            'volume_24h': volume_24h,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'market_cap_rank': market_cap_rank
        }
    except Exception as e:
        logger.error(f"Error processing data for {coin_id}: {e}")
        return None

# Fungsi untuk mencari ID koin berdasarkan nama atau ticker
def get_coin_id_by_name(coin_name):
    url = f'https://api.coingecko.com/api/v3/search?query={coin_name}'
    response = requests.get(url)
    if response.status_code == 429:
        logger.error("API rate limit reached during search.")
        return "API limit reached. Please try again later."
    elif response.status_code != 200:
        logger.error(f"Failed to fetch search data for {coin_name}. HTTP {response.status_code}")
        return None

    data = response.json()
    if 'coins' in data and len(data['coins']) > 0:
        return data['coins'][0]['id']
    else:
        logger.info(f"No coins found for {coin_name}")
        return None

# Fungsi untuk membuat chart Candlestick
def create_coin_candlestick_chart(coin_id):
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30'
    response = requests.get(url)
    if response.status_code == 429:
        logger.error("API rate limit reached during chart request.")
        return "API limit reached. Please try again later."
    elif response.status_code != 200:
        logger.error(f"Failed to fetch market chart for {coin_id}. HTTP {response.status_code}")
        return None
    
    data = response.json()
    if 'prices' not in data:
        logger.error(f"Missing price data for {coin_id}")
        return None

    ohlc_data = data['prices']
    timestamps = [entry[0] for entry in ohlc_data]
    prices = [entry[1] for entry in ohlc_data]

    ohlc = []
    for i in range(0, len(prices), 24):
        open_price = prices[i]
        close_price = prices[i+23] if i+23 < len(prices) else prices[-1]
        high_price = max(prices[i:i+24])
        low_price = min(prices[i:i+24])
        ohlc.append([timestamps[i], open_price, high_price, low_price, close_price])

    ohlc_df = pd.DataFrame(ohlc, columns=["timestamp", "open", "high", "low", "close"])
    ohlc_df['timestamp'] = pd.to_datetime(ohlc_df['timestamp'], unit='ms')

    chart_filename = f'{coin_id}_candlestick_chart.png'
    mpf.plot(
        ohlc_df.set_index('timestamp'), type='candle', style='charles',
        title=f'{coin_id.capitalize()} 1-Day Candlestick Chart', ylabel='Price (USD)',
        savefig=chart_filename
    )
    return chart_filename

# Fungsi untuk command /p
async def coin_info(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text('Please specify a coin (e.g., /p bitcoin, /p btc, /p ethereum)')
        return

    coin_name = context.args[0].lower()
    coin_id = get_coin_id_by_name(coin_name)

    if coin_id == "API limit reached. Please try again later.":
        await update.message.reply_text("Kena limit API, woy jangan SPAM!")
        return

    if coin_id is None:
        await update.message.reply_text(f"Sorry, I couldn't find a coin with the name or ticker '{coin_name}'.")
        return

    data = get_coin_data(coin_id)
    if data == "API limit reached. Please try again later.":
        await update.message.reply_text("Kena limit API, woy jangan SPAM!")
        return

    if data is None:
        await update.message.reply_text(f"Sorry, I couldn't fetch data for '{coin_name}'.")
        return

    response = f"""
{coin_id.capitalize()} [Rank {data['market_cap_rank']}]
💰 Price: ${data['price']:,.6f}
📉 1h: {data['price_1h']:.2f}%
📈 24h: {data['price_24h']:.2f}%
🚀 7d: {data['price_7d']:.2f}%
🌕 30d: {data['price_30d']:.2f}%
🏆 ATH: ${data['ath']:,.6f} ({data['ath_diff']:.2f}% from ATH)
📊 24h Vol: ${data['volume_24h']:,.2f}
💎 MCap: {format_market_cap(data['market_cap'])}
"""
    keyboard = [[InlineKeyboardButton("Chart", callback_data=coin_id)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(response, reply_markup=reply_markup)

# Fungsi untuk tombol chart
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    coin_id = query.data

    # Membuat chart candlestick
    logger.info(f"Generating chart for coin: {coin_id}")
    chart_filename = create_coin_candlestick_chart(coin_id)

    # Jika chart gagal dibuat
    if chart_filename is None:
        logger.error(f"Failed to generate chart for {coin_id}.")
        await query.answer("Failed to generate chart.")
        return

    try:

         # Kirim chart sebagai gambar, sebagai balasan pesan sebelumnya
        with open(chart_filename, 'rb') as chart_file:
            await query.message.reply_photo(
                photo=chart_file,
                caption=f"Chart for {coin_id.capitalize()}",
                reply_to_message_id=query.message.message_id  # Balas ke pesan informasi coin
            )
    except Exception as e:
        logger.error(f"Failed to send chart for {coin_id}: {e}")
        await query.message.reply_text("There was an error sending the chart.")


        # Hapus file chart setelah dikirim
        os.remove(chart_filename)
        logger.info(f"Chart file {chart_filename} removed successfully.")

    except FileNotFoundError as fnf_error:
        logger.error(f"File not found: {fnf_error}")
        await query.message.reply_text("Chart file is missing. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error during chart processing: {e}")
        await query.message.reply_text("Failed to send chart due to an internal error.")
    finally:
        # Pastikan file dihapus jika masih ada
        if os.path.exists(chart_filename):
            try:
                os.remove(chart_filename)
                logger.info(f"Chart file {chart_filename} removed in finally block.")
            except Exception as e:
                logger.error(f"Failed to remove chart file in finally block: {e}")

    # Mengambil informasi coin dari pesan sebelumnya
    original_message = query.message.text

    # Pisahkan pesan menjadi bagian informasi coin dan tombol chart
    message_parts = original_message.split("\n")

    # Jika ada baris terakhir yang merupakan informasi chart, hapus tombol chart
    coin_info = "\n".join(message_parts)  # Ambil semua baris kecuali baris terakhir (tombol chart)

    # Kirim kembali pesan dengan informasi koin dan hapus tombol chart
    message_to_send = f"{coin_info}\n\nThe chart for {coin_id.capitalize()} has been sent. No more chart available."

    # Menghapus tombol chart tapi mempertahankan informasi coin
    await query.edit_message_text(
        text=message_to_send,
        reply_markup=None  # Menghapus tombol chart
    )


# Fungsi untuk menangani perintah /hmap
async def hmap(update: Update, context: CallbackContext):
    # Kirim gambar heatmap dengan reply ke pesan yang memicu perintah /hmap
    await send_image_to_telegram(update, context, reply_to_message_id=update.message.message_id)


# Fungsi untuk menangani pesan dengan kata kunci
async def handle_keyword_messages(update: Update, context: CallbackContext):
    # Simpan log jika diperlukan
    logger.info(f"Received message: {update.message.text}")

# Fungsi untuk laporan bug
async def report(update: Update, context: CallbackContext):
    if len(context.args) == 0:  # Cek jika tidak ada alasan yang diberikan
        await update.message.reply_text("Please provide a report detail after the command (e.g., /report Issue with the bot).")
        return

    report_message = ' '.join(context.args)  # Ambil alasan dari argumen
    logger.info(f"User report: {report_message}")
    
    # Kirim laporan ke admin
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"Bug Report from {update.message.from_user.username}:\n\n{report_message}")
    
    await update.message.reply_text("Thank you for your report. We will review it shortly.")


# Fungsi moodeng command
async def moodeng_command(update: Update, context: CallbackContext):
    # Membalas pesan yang memicu dengan fitur reply
    await update.message.reply_text(
        "Moodeng Sol is the biggest meme coin scam in the world!",
        reply_to_message_id=update.message.message_id  # Membalas pesan yang memicu perintah
    )

# Fungsi mog command
async def mog_command(update: Update, context: CallbackContext):
    # Membalas pesan yang memicu dengan fitur reply
    await update.message.reply_text(
        "Mogokkk",
        reply_to_message_id=update.message.message_id  # Membalas pesan yang memicu perintah
    )

# Fungsi moodengeth command
async def moodengeth_command(update: Update, context: CallbackContext):
    # Membalas pesan yang memicu dengan fitur reply
    await update.message.reply_text(
        "Moodeng eth is the best meme coin project the world has ever seen!",
        reply_to_message_id=update.message.message_id  # Membalas pesan yang memicu perintah
    )

# Fungsi untuk memulai bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hi! Send me a coin name (e.g., /p bitcoin), type a keyword to get started, or use /d for search DEX Coin by CA ,or use /report to send a report, or use /hmap to see a crypto heatmap.')

# Fungsi untuk menangani command /d
async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        contract_address = context.args[0]
        print(f"Mencari informasi untuk kontrak: {contract_address}")
        token_info = get_token_info(contract_address)
        print(f"Token Info: {token_info}")
        await update.message.reply_text(token_info)
    else:
        await update.message.reply_text("Silakan masukkan alamat kontrak token.")

# Menyeting logging untuk debug
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('p', coin_info))
    application.add_handler(CommandHandler(['moodengsol', 'moodeng_sol', 'modenksol', 'modenk_sol'], moodeng_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyword_messages))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CommandHandler("hmap", hmap))
    application.add_handler(CommandHandler("d", token_command))
    application.add_handler(CommandHandler(['mog'], mog_command))
    application.add_handler(CommandHandler(['moodengeth'], moodengeth_command))


    application.run_polling()

if __name__ == '__main__':
    main()
