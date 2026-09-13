# Viral News Monitor Indonesia — Setup Guide

Tool otomatis untuk deteksi berita viral Indonesia, kirim ke Telegram setiap jam 6 pagi WIB.

## Cara Kerja
- Scan RSS dari 12 media besar Indonesia (Detik, Kompas, CNN Indonesia, Tempo, dll)
- Deteksi topik yang di-cover 3+ media dalam 24 jam terakhir = viral
- Kirim ringkasan ke Telegram lo

---

## Akun yang Dibutuhkan

| Tool | Link | Fungsi | Biaya |
|------|------|--------|-------|
| Telegram | https://telegram.org | Terima notifikasi | Gratis |
| GitHub | https://github.com/signup | Simpan code | Gratis |
| Railway | https://railway.com | Jalankan bot 24/7 | Gratis $5 kredit awal, cukup untuk 1 tahun+ |

---

## STEP 1 — Buat Telegram Bot (5 menit)

1. Buka Telegram (HP atau desktop)
2. Search: `@BotFather` (yang official, ada centang biru)
3. Klik **START**
4. Ketik: `/newbot`
5. BotFather tanya nama bot → ketik apa aja, misal: `Viral News Rofina`
6. BotFather tanya username → harus unik, harus diakhiri `bot`. Misal: `viralnews_rofina_bot`
7. **BotFather kasih TOKEN** kayak gini:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   👉 **COPY dan simpan** di Notes. Ini `TELEGRAM_BOT_TOKEN`

### Ambil Chat ID (biar bot tau kirim ke siapa)

1. Di Telegram, search nama bot yang barusan lo buat, klik **START**
2. Kirim pesan apa aja ke bot lo (misal: "halo")
3. Buka browser, akses URL ini (ganti `TOKEN_LO` dengan token dari BotFather):
   ```
   https://api.telegram.org/bot<TOKEN_LO>/getUpdates
   ```
   Contoh: `https://api.telegram.org/bot7123456789:AAHxxxx.../getUpdates`
4. Bakal muncul JSON. Cari bagian:
   ```json
   "chat":{"id":123456789,"first_name":"Rofina"...}
   ```
5. Angka `123456789` itu **CHAT ID** lo. Simpan sebagai `TELEGRAM_CHAT_ID`

---

## STEP 2 — Upload Code ke GitHub (10 menit)

1. Daftar GitHub di https://github.com/signup (gratis)
2. Verify email
3. Login, klik ikon **+** di kanan atas → **New repository**
4. Isi:
   - Repository name: `viral-news-bot`
   - Description: (kosongin aja)
   - **Public** atau **Private** — pilih Private supaya orang lain ga bisa liat
   - **JANGAN centang** "Initialize with README"
   - Klik **Create repository**
5. Di halaman repo yang baru dibuat, klik **"uploading an existing file"** (link biru di tengah)
6. **Drag & drop** ke 4 file ini:
   - `main.py`
   - `requirements.txt`
   - `railway.json`
   - `SETUP.md` (optional, buat dokumentasi)
7. Scroll ke bawah, klik **Commit changes**

---

## STEP 3 — Deploy ke Railway (15 menit)

### Setup Railway account
1. Buka https://railway.com
2. Klik **Login** → **Login with GitHub** (paling gampang)
3. Authorize Railway akses ke GitHub lo

### Deploy dari GitHub
1. Klik **New Project** → **Deploy from GitHub repo**
2. Pilih repo `viral-news-bot`
3. Railway otomatis detect Python, mulai build. Tunggu 2-3 menit.

### Set Environment Variables (CREDENTIAL LO)
1. Klik service yang baru dibuat
2. Klik tab **Variables**
3. Klik **New Variable**, tambahin satu-satu:

| Nama | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | Token dari BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID dari step 1 |
| `MIN_SOURCES` | `3` (default, boleh diubah ke 4 kalau mau lebih strict) |

### Set Cron Schedule (jadwal jalan)
1. Masih di service, klik tab **Settings**
2. Scroll cari section **"Cron Schedule"** atau **"Deploy"**
3. Isi Cron Schedule:
   ```
   0 23 * * *
   ```
   ⚠️ Ini artinya jam 23:00 UTC = **jam 6 pagi WIB** (UTC+7)
4. Save

### Trigger manual test pertama kali
1. Di tab **Deployments**, klik deployment terakhir
2. Klik **Redeploy** — supaya jalan sekali sekarang buat test
3. Cek tab **Logs** — harusnya muncul log kayak:
   ```
   [06:00:01] ==================================================
   [06:00:01] VIRAL NEWS MONITOR - INDONESIA
   [06:00:03]   v Detik: 30 artikel
   ...
   [06:00:15] ✅ Selesai!
   ```
4. **Cek Telegram lo** — harusnya udah masuk pesan berita viral

---

## STEP 4 — Verify Semuanya Jalan

### Checklist
- [ ] Telegram bot udah reply pas dikirim `/start`
- [ ] Environment variables di Railway udah lengkap (3 items)
- [ ] Cron schedule di Railway udah di-set `0 23 * * *`
- [ ] Manual test deploy berhasil, log ga ada error merah besar
- [ ] Pesan pertama udah masuk Telegram

### Cek Log Nanti
- Buka Railway → project lo → **Deployments** → **View Logs**
- Setiap hari harusnya ada deployment baru jam 6 pagi WIB
- Kalau ada error, log-nya di sini

---

## Troubleshooting

**Bot Telegram ga nerima pesan?**
- Pastikan lo udah kirim pesan ke bot dulu (klik START di chat bot)
- Chat ID harus angka lo, bukan angka bot
- Test manual: buka `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test`

**Log Railway error "Module not found"?**
- Pastiin `requirements.txt` udah ke-upload ke GitHub
- Redeploy dari Railway

**RSS feed ada yang gagal (tanda `x`)?**
- Normal, kadang media ganti URL RSS
- Selama 8+ media masih jalan, deteksi masih akurat

**Ga ada topik viral yang muncul?**
- Normal juga, ga tiap hari ada berita yang cover 3+ media besar
- Coba turunin `MIN_SOURCES` jadi `2` di Railway Variables

**Railway kredit habis?**
- Kredit awal $5 cukup buat ~10+ bulan pemakaian bot yang jalan cuma 1 menit sehari
- Kalau habis, upgrade ke Hobby plan ($5/bulan) atau pindah ke GitHub Actions (gratis selamanya)

---

## Alternatif: GitHub Actions (Kalau Ga Mau Railway)

GitHub Actions gratis selamanya untuk public repo. Ganti approach-nya kalau Railway ribet:
- Tambah file `.github/workflows/schedule.yml`
- Cron di GitHub Actions pakai UTC juga
- Set secrets di GitHub repo settings (bukan Railway)

Tanya lagi kalau mau opsi ini.
