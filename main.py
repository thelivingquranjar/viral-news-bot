#!/usr/bin/env python3
"""
Viral News Monitor - Indonesia
Tool otomatis untuk deteksi berita viral dari media besar Indonesia
dan kirim ringkasan ke Telegram.
"""
import os
import re
import time
import requests
import feedparser
from datetime import datetime
from collections import defaultdict
import pytz

# ============================================================
# CONFIGURATION
# Set these as environment variables (jangan hardcode!)
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Minimum jumlah media unik yang cover satu topik = "viral"
MIN_SOURCES = int(os.getenv('MIN_SOURCES', '3'))

# Berapa jam ke belakang yang di-scan
HOURS_LOOKBACK = int(os.getenv('HOURS_LOOKBACK', '24'))

# ============================================================
# RSS FEEDS - Media besar Indonesia (website/blog only)
# ============================================================
RSS_FEEDS = {
    'Detik': 'https://rss.detik.com/index.php/detikcom',
    'Kompas': 'https://news.kompas.com/rss',
    'CNN Indonesia': 'https://www.cnnindonesia.com/nasional/rss',
    'Tempo': 'https://rss.tempo.co/nasional',
    'Antara': 'https://www.antaranews.com/rss/terkini.xml',
    'Tribunnews': 'https://www.tribunnews.com/rss',
    'Liputan6': 'https://feed.liputan6.com/rss',
    'Republika': 'https://www.republika.co.id/rss',
    'Okezone': 'https://sindikasi.okezone.com/index.php/rss/0/RSS2.0',
    'Merdeka': 'https://www.merdeka.com/feed/',
    'JPNN': 'https://www.jpnn.com/index.php?mib=rss',
    'Suara': 'https://www.suara.com/rss/terkini',
}

# Kata-kata umum yang di-skip (stopwords Indonesia)
STOPWORDS = set('''
yang dan di ke dari untuk pada dengan atau juga akan tak tidak ini itu ada
kata sebagai jika hingga saat pun bahwa telah sudah karena tetapi tapi
lalu setelah namun para banyak lebih sangat sekali agar demi oleh dalam
menjadi masih dapat bisa harus sampai antara sekitar hanya saja belum
lain baru pertama tersebut hal apa siapa kenapa bagaimana kapan
adalah bagi ya nya kita kami mereka anda saya aku dia beliau bersama
tentang seperti setiap terhadap sesuai berdasarkan menurut selain
sedang pernah sering kadang selalu tetap bukan bukanlah
usai jadi soal ungkap ujar kepada tegas malah begitu semua sebuah
memang bila ternyata maupun adanya sesuatu
kembali mulai selesai keluar masuk turun naik pergi datang
hari senin selasa rabu kamis jumat sabtu minggu tahun bulan
sambil sementara terus lantas kemudian jelang
diri sendiri masing satu dua tiga empat lima enam tujuh
delapan sembilan sepuluh news berita foto video live update
'''.split())

# Kata-kata yang biasanya nandain berita penting (di-boost prioritasnya)
NEWS_INDICATORS = {
    'meninggal', 'wafat', 'ditangkap', 'ditahan', 'kebakaran',
    'gempa', 'banjir', 'kecelakaan', 'demo', 'unjuk',
    'menang', 'kalah', 'juara', 'putusan', 'vonis', 'korupsi',
    'presiden', 'menteri', 'gubernur', 'walikota', 'bupati',
    'viral', 'tewas', 'meledak', 'longsor', 'tsunami',
}


def log(msg):
    """Print dengan timestamp WIB"""
    wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(wib).strftime('%H:%M:%S')
    print(f"[{now}] {msg}", flush=True)


def fetch_feed(source_name, url, timeout=15):
    """Ambil satu RSS feed dengan error handling"""
    try:
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        return feed.entries
    except Exception as e:
        log(f"  x {source_name}: {str(e)[:80]}")
        return []


def fetch_all_news():
    """Ambil berita dari semua sumber RSS"""
    all_articles = []
    wib = pytz.timezone('Asia/Jakarta')

    for source, url in RSS_FEEDS.items():
        entries = fetch_feed(source, url)
        count = 0
        for entry in entries[:30]:
            published = None
            for date_field in ['published_parsed', 'updated_parsed']:
                dt = entry.get(date_field)
                if dt:
                    try:
                        published = datetime(*dt[:6], tzinfo=pytz.UTC).astimezone(wib)
                        break
                    except Exception:
                        pass

            article = {
                'title': entry.get('title', '').strip(),
                'link': entry.get('link', '').strip(),
                'source': source,
                'published': published,
            }
            if article['title'] and article['link']:
                all_articles.append(article)
                count += 1

        if count > 0:
            log(f"  v {source}: {count} artikel")

    return all_articles


def extract_keywords(title):
    """Extract kata kunci dari judul berita"""
    clean = re.sub(r'http\S+|[^\w\s-]', ' ', title.lower())
    words = re.split(r'\s+', clean)

    keywords = []
    for w in words:
        w = w.strip()
        if len(w) >= 4 and w not in STOPWORDS and not w.isdigit():
            keywords.append(w)

    bigrams = [f"{keywords[i]} {keywords[i+1]}" for i in range(len(keywords) - 1)]
    return keywords, bigrams


def find_viral_topics(articles):
    """Deteksi topik yang di-cover multi-source"""
    bigram_articles = defaultdict(list)
    keyword_articles = defaultdict(list)

    for article in articles:
        keywords, bigrams = extract_keywords(article['title'])
        for bg in bigrams:
            bigram_articles[bg].append(article)
        for kw in keywords:
            keyword_articles[kw].append(article)

    viral_candidates = []

    # Prioritas 1: bigrams (2 kata) - lebih spesifik
    for bigram, arts in bigram_articles.items():
        sources = set(a['source'] for a in arts)
        if len(sources) >= MIN_SOURCES:
            viral_candidates.append({
                'topic': bigram,
                'type': 'phrase',
                'sources': sources,
                'source_count': len(sources),
                'articles': arts,
                'boost': 2,
            })

    # Prioritas 2: single keyword - butuh threshold lebih tinggi
    for keyword, arts in keyword_articles.items():
        sources = set(a['source'] for a in arts)
        min_needed = MIN_SOURCES if keyword in NEWS_INDICATORS else MIN_SOURCES + 1
        if len(sources) >= min_needed:
            viral_candidates.append({
                'topic': keyword,
                'type': 'keyword',
                'sources': sources,
                'source_count': len(sources),
                'articles': arts,
                'boost': 2 if keyword in NEWS_INDICATORS else 1,
            })

    viral_candidates.sort(key=lambda x: x['source_count'] * x['boost'], reverse=True)

    # Dedup: topik yang share banyak artikel, keep yang lebih spesifik
    final = []
    used_articles = set()

    for topic in viral_candidates:
        unique_arts = [a for a in topic['articles'] if a['link'] not in used_articles]
        unique_sources = set(a['source'] for a in unique_arts)
        if len(unique_sources) >= MIN_SOURCES and len(unique_arts) >= MIN_SOURCES:
            topic['articles'] = unique_arts[:5]
            topic['sources'] = unique_sources
            topic['source_count'] = len(unique_sources)
            final.append(topic)
            for a in unique_arts:
                used_articles.add(a['link'])

        if len(final) >= 10:
            break

    return final


def send_telegram(text):
    """Kirim pesan ke Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️  TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum di-set!")
        log("    Preview pesan:")
        print("\n" + text + "\n")
        return False

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            log(f"  x Telegram error {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        log(f"  x Telegram exception: {e}")
        return False


def build_message(viral_topics, now, total_articles):
    """Build pesan Telegram"""
    header = (
        f"🔥 <b>BERITA VIRAL INDONESIA</b>\n"
        f"🕐 {now.strftime('%A, %d %B %Y')}\n"
        f"⏰ {now.strftime('%H:%M WIB')}\n"
        f"📊 Total artikel di-scan: {total_articles}\n"
    )

    if not viral_topics:
        return header + (
            f"\n━━━━━━━━━━━━━━━\n\n"
            f"✅ Belum ada topik yang mencapai batas viral "
            f"({MIN_SOURCES}+ media besar) dalam {HOURS_LOOKBACK} jam terakhir.\n\n"
            f"<i>Selamat pagi! ☕</i>"
        )

    body = f"\n\n🎯 <b>{len(viral_topics)} topik terdeteksi viral</b>\n"
    body += f"<i>(dibahas di {MIN_SOURCES}+ media besar)</i>\n\n"
    body += "━━━━━━━━━━━━━━━\n\n"

    for i, topic in enumerate(viral_topics[:7], 1):
        body += f"<b>#{i} — {topic['topic'].upper()}</b>\n"
        body += f"📰 {topic['source_count']} media meliput:\n"
        body += f"<i>{', '.join(sorted(topic['sources']))}</i>\n\n"

        for art in topic['articles'][:3]:
            title = art['title']
            if len(title) > 130:
                title = title[:127] + '...'
            body += f"▸ <a href=\"{art['link']}\">{title}</a>\n"
            body += f"   <i>{art['source']}</i>\n"
        body += "\n━━━━━━━━━━━━━━━\n\n"

    return header + body


def main():
    wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(wib)

    log("=" * 50)
    log("VIRAL NEWS MONITOR - INDONESIA")
    log(f"Waktu: {now.strftime('%Y-%m-%d %H:%M WIB')}")
    log("=" * 50)

    log("\n📥 Ambil berita dari semua sumber...")
    articles = fetch_all_news()
    log(f"\n📊 Total artikel: {len(articles)}")

    if not articles:
        log("⚠️  Tidak ada artikel yang berhasil di-fetch!")
        send_telegram(
            f"⚠️ <b>Viral News Monitor</b>\n"
            f"🕐 {now.strftime('%H:%M WIB')}\n\n"
            f"Gagal fetch berita. Cek koneksi atau RSS feed."
        )
        return

    log("\n🔍 Analisa topik viral...")
    viral = find_viral_topics(articles)
    log(f"🔥 Ditemukan {len(viral)} topik viral")
    for i, t in enumerate(viral[:5], 1):
        log(f"  {i}. {t['topic']} — {t['source_count']} media")

    log("\n📤 Kirim ke Telegram...")
    message = build_message(viral, now, len(articles))

    # Split kalau kepanjangan (Telegram max 4096 chars)
    if len(message) > 4000:
        parts = []
        current = ""
        for chunk in message.split("━━━━━━━━━━━━━━━"):
            if len(current) + len(chunk) > 3500:
                if current:
                    parts.append(current)
                current = chunk
            else:
                current += ("━━━━━━━━━━━━━━━" + chunk) if current else chunk
        if current:
            parts.append(current)

        for i, part in enumerate(parts, 1):
            prefix = f"<b>[Bagian {i}/{len(parts)}]</b>\n\n" if len(parts) > 1 else ""
            send_telegram(prefix + part)
            time.sleep(1)
    else:
        send_telegram(message)

    log("\n✅ Selesai!")


if __name__ == '__main__':
    main()
