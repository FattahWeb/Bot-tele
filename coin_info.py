import requests

# URL CoinMarketCap API
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/info"
CMC_API_KEY = "32aa9311-3018-464e-8f34-f56d43c70414"  # Ganti dengan API key Anda

CMC_QUOTE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY,
}

# Fungsi untuk memformat angka besar
def format_large_number(number):
    if number >= 1e9:
        return f"{number / 1e9:.2f}B"
    elif number >= 1e6:
        return f"{number / 1e6:.2f}M"
    elif number >= 1e3:
        return f"{number / 1e3:.2f}K"
    else:
        return f"{number:.2f}"

# Fungsi untuk mengambil data token
def get_token_info(contract_address):
    try:
        # Request ke API untuk mendapatkan informasi token
        params = {"address": contract_address}
        response = requests.get(CMC_API_URL, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        # Memeriksa apakah data ditemukan
        if "data" not in data or not data["data"]:
            return "Token tidak ditemukan. Pastikan alamat kontrak valid."

        token_data = next(iter(data["data"].values()))
        token_id = token_data["id"]

        # Mengambil informasi kuotasi harga
        quote_params = {"id": token_id}
        quote_response = requests.get(CMC_QUOTE_URL, headers=headers, params=quote_params)
        quote_response.raise_for_status()

        quote_data = quote_response.json()
        token_quote = quote_data["data"].get(str(token_id), {})

        # Data utama
        price = token_quote["quote"]["USD"]["price"]
        percent_change_1h = token_quote["quote"]["USD"].get("percent_change_1h", 0)
        percent_change_24h = token_quote["quote"]["USD"].get("percent_change_24h", 0)
        volume_24h = token_quote["quote"]["USD"].get("volume_24h", 0)
        market_cap = token_quote["quote"]["USD"].get("market_cap", 0)
        ath_price = token_quote.get("ath", "N/A")

        # Periksa ATH
        if isinstance(ath_price, (int, float)):
            ath_difference = ((price - ath_price) / ath_price) * 100
            ath_display = f"${ath_price:,.6f} ({ath_difference:.2f}% from ATH)"
        else:
            ath_display = "N/A"

        # Format pesan
        formatted_message = (
            f"{token_data['symbol']} [Rank {token_quote.get('cmc_rank', 'N/A')}]\n"
            f"💰 Price: ${price:,.6f}\n"
            f"📉 1h: {percent_change_1h:.2f}%\n"
            f"📈 24h: {percent_change_24h:.2f}%\n"
            f"🏆 ATH: {ath_display}\n"
            f"📊 24h Vol: ${format_large_number(volume_24h)}\n"
            f"💎 MCap: ${format_large_number(market_cap)}"
        )
        return formatted_message
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"
    except KeyError:
        return "Data token tidak lengkap atau salah format."
