# Gunakan Python versi 3.10-slim
FROM python:3.10-slim

# Tetapkan direktori kerja
WORKDIR /app

# Salin semua file ke dalam container
COPY . .

# Perbarui pip sebelum menginstal dependensi
RUN pip install --upgrade pip

# Instal dependensi dari requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Jalankan bot
CMD ["python", "bot.py"]
