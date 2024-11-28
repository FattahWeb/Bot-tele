import os
import requests
import matplotlib.pyplot as plt
import pandas as pd

# Fungsi untuk mengambil data crypto dari API CoinGecko
def fetch_crypto_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',  # Mengambil harga dalam USD
        'order': 'market_cap_desc',  # Urutkan berdasarkan kapitalisasi pasar
        'per_page': 100,  # Ambil 100 coin pertama
        'page': 1  # Halaman pertama
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"Data terbaru: {data[:5]}")  # Cek 5 data pertama yang diterima
        return data
    else:
        print("Error dalam mengambil data")
        return []

# Fungsi untuk membuat heatmap crypto
def create_crypto_heatmap(df):
    print("Data yang digunakan untuk heatmap:", df.head())  # Menampilkan data yang diproses
    plt.figure(figsize=(15, 10))

    # Menyiapkan grid untuk heatmap
    ax = plt.gca()
    ax.set_xticks([])
    ax.set_yticks([])

    rows, cols = 10, 10  # Grid 10x10
    for i in range(rows):
        for j in range(cols):
            index = i * cols + j
            if index < len(df):
                coin = df.iloc[index]
                ticker = coin['symbol']
                price = coin['current_price']
                percent_change = coin['price_change_percentage_24h']

                color = 'green' if percent_change > 0 else 'red'
                change_str = f"{percent_change:+.2f}%"

                # Buat kotak dan tuliskan data coin di dalamnya
                ax.add_patch(plt.Rectangle((j, rows-i-1), 1, 1, facecolor=color, edgecolor='black', lw=2))

                # Tulis ticker coin dengan ukuran font lebih besar
                ax.text(j + 0.5, rows-i-0.25, f"{ticker}",
                        ha='center', va='center', fontsize=16, color='white', fontweight='bold')

                # Tulis harga dan perubahan persen dengan ukuran font lebih kecil
                ax.text(j + 0.5, rows-i-0.65, f"${price:,.2f}\n{change_str}",
                        ha='center', va='center', fontsize=10, color='white')

    # Simpan gambar heatmap sebagai file tanpa ruang putih
    image_path = 'crypto_heatmap.png'
    plt.xlim(0, cols)
    plt.ylim(0, rows)
    plt.axis('off')
    plt.savefig(image_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close()

    return image_path

# Fungsi untuk mengirim gambar ke Telegram dengan reply
async def send_image_to_telegram(update, context, reply_to_message_id=None):
    data = fetch_crypto_data()
    df = pd.DataFrame(data)
    df = df[['symbol', 'current_price', 'price_change_percentage_24h']]  # Pilih kolom yang relevan
    image_path = create_crypto_heatmap(df)

    # Kirim gambar ke pengguna yang mengirimkan perintah /hmap dengan reply
    with open(image_path, 'rb') as image_file:
        await update.message.reply_photo(
            photo=image_file,
            caption="Here's the heatmap!",
            reply_to_message_id=reply_to_message_id  # Membalas pesan yang memicu /hmap
        )

    # Hapus file setelah pengiriman
    os.remove(image_path)
    print(f"File {image_path} berhasil dihapus setelah dikirim.")
