import requests
import mplfinance as mpf
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
import logging

# Token bot Telegram
TELEGRAM_TOKEN = '7929212472:AAH5Nkf072mrqw0o0ToC6qAJ-JvoYvhR8ZY'

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

# Fungsi untuk mendapatkan data coin dari CoinGecko
def get_coin_data(coin_id):
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
    response = requests.get(url)
    
    if response.status_code != 200:
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
        market_cap_rank = data.get('market_cap_rank', 'N/A')  # Ambil peringkat koin

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
            'market_cap_rank': market_cap_rank  # Menambahkan peringkat koin
        }
    except Exception as e:
        logger.error(f"Error processing data for {coin_id}: {e}")
        return None

# Fungsi untuk mencari ID koin berdasarkan nama atau ticker
def get_coin_id_by_name(coin_name):
    url = f'https://api.coingecko.com/api/v3/search?query={coin_name}'
    response = requests.get(url)

    if response.status_code != 200:
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

    if response.status_code != 200:
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

    if coin_id is None:
        await update.message.reply_text(f"Sorry, I couldn't find a coin with the name or ticker '{coin_name}'.")
        return

    data = get_coin_data(coin_id)
    if data is None:
        await update.message.reply_text(f"Sorry, I couldn't fetch data for '{coin_name}'.")
        return

    coin_display_name = coin_name.capitalize()  # Menampilkan nama koin dengan huruf kapital
    market_cap_rank = data['market_cap_rank']  # Ambil peringkat koin

    response = f"""
  {coin_display_name} [{market_cap_rank}] 
💰 Price: ${data['price']:,.6f}
⚖️ H/L: ${data['high_24h']:,.6f} | ${data['low_24h']:,.6f}
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
    message = await update.message.reply_text(response, reply_markup=reply_markup)
    context.user_data[update.effective_user.id] = {'message_id': message.message_id}

# Fungsi untuk tombol chart
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    coin_id = query.data

    chart_filename = create_coin_candlestick_chart(coin_id)
    if chart_filename is None:
        await query.message.reply_text("Sorry, I couldn't generate the chart.")
        return

    user_data = context.user_data.get(update.effective_user.id, {})
    message_id = user_data.get('message_id')
    await query.answer()

    with open(chart_filename, 'rb') as chart_file:
        await query.message.reply_photo(photo=chart_file, reply_to_message_id=message_id)

# Fungsi untuk menangani pesan dengan kata kunci dan membalas dengan fitur reply
async def handle_keyword_messages(update: Update, context: CallbackContext):
    message_text = update.message.text.lower()
    if 'moodengsol' in message_text or 'moodeng sol' in message_text or 'moodenksol' in message_text or 'moodenk sol' in message_text or 'modenksol' in message_text or 'modenk sol' in message_text:
        # Membalas pesan yang mengandung kata kunci dengan fitur reply
        await update.message.reply_text("Moodeng Sol is the biggest meme coin scam in the world!", reply_to_message_id=update.message.message_id)

# Fungsi untuk memulai bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hi! Send me a coin name (e.g., /p bitcoin) or type a keyword to get started.')

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Daftarkan handler untuk command dan pesan
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('p', coin_info))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyword_messages))
    application.add_handler(CallbackQueryHandler(button))

    # Mulai bot
    application.run_polling()

if __name__ == '__main__':
    main()
