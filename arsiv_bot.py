import os
import asyncio
import logging
import random
import json
import subprocess
from datetime import datetime
from pathlib import Path
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AYARLAR ---
BOT_TOKEN = os.environ.get("ARSIV_BOT_TOKEN", "")
ADMIN_ID = 5019918710
VIP_LINK = "https://t.me/Vip_iesrabot"

KANALLAR = [
    -1003494573579,  # Malatya Esra Bal İE' (+18)
    -1002956424495,  # MALATYA ESRA BAL (+18)
    -1003959424039,  # İ.E'sra Arşiv
]

ARSIV_DOSYASI = "video_arsiv.json"

# --- 10 CAPTION ŞABLONU ---
CAPTION_SABLONLAR = [
    "az önce çektim, size özel 🔥\ndevamı her zaman VIP'te oluyor 😏\n\n💎 {vip}\n⭐ {yildiz} yıldız ile izle",
    "bu gece biraz eğlendim 🌙\nkalanı VIP'te sizi bekliyor...\n\n→ {vip}\n⭐ {yildiz} yıldız",
    "sadece sizin için çektim 🍯\nbir kısmını gösterdim, gerisi VIP'te\n\n💎 {vip}\n⭐ {yildiz} yıldız ile devamını gör",
    "önizleme bu kadar 😈\ngerçek olan VIP kanalda\n\n🔗 {vip}\n⭐ {yildiz} yıldız",
    "iyi geceler 🔥 ya da daha iyi mi yapalım?\ndevamı için biliyorsunuz ne yapılacağını\n\n{vip}\n⭐ {yildiz} yıldız ile izle",
    "canım sıkıldı, sizi düşündüm 🌹\ngel VIP'te devamına bak 😏\n\n💎 {vip}\n⭐ {yildiz} yıldız",
    "yeni video sıcacık 🔥\ntüm içeriklere erişim VIP'te\n\n→ {vip}\n⭐ {yildiz} yıldız ile izle",
    "bu kadar mı? tabii ki hayır 😈\ngeri kalanı sana özel VIP'te\n\n🔗 {vip}\n⭐ {yildiz} yıldız",
    "bugün biraz cesurduk 🍯\ndevamını görmek isteyene kapım açık\n\n💎 {vip}\n⭐ {yildiz} yıldız ile izle",
    "sadece seçilmişler için 🌙\nVIP üyelerim her şeyi tam görüyor\n\ngel katıl: {vip}\n⭐ {yildiz} yıldız",
]

caption_index = 0

def yildiz_fiyati(sure_sn: int) -> int:
    if sure_sn <= 180:
        return 350
    elif sure_sn <= 300:
        return 650
    else:
        return 1000

def siradaki_caption(yildiz: int) -> str:
    global caption_index
    sablon = CAPTION_SABLONLAR[caption_index % len(CAPTION_SABLONLAR)]
    caption_index += 1
    return sablon.format(vip=VIP_LINK, yildiz=yildiz)

def arsiv_yukle() -> list:
    if Path(ARSIV_DOSYASI).exists():
        with open(ARSIV_DOSYASI, "r") as f:
            return json.load(f)
    return []

def arsiv_kaydet(arsiv: list):
    with open(ARSIV_DOSYASI, "w") as f:
        json.dump(arsiv, f, ensure_ascii=False, indent=2)

def video_suresi_al(dosya_yolu: str) -> int:
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', dosya_yolu],
            capture_output=True, text=True, timeout=30
        )
        return int(float(result.stdout.strip()))
    except:
        return 120

# --- BOT KOMUTLARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    arsiv = arsiv_yukle()
    await update.message.reply_text(
        f"🎬 Esra Arşiv Bot aktif!\n\n"
        f"📦 Arşivde {len(arsiv)} video var\n\n"
        f"Kullanım:\n"
        f"• Video gönder → arşive ekler\n"
        f"• /liste → arşivdeki videoları göster\n"
        f"• /paylas → hemen paylaşım yap\n"
        f"• /sil [numara] → videoyu arşivden sil\n\n"
        f"⏰ Otomatik paylaşım: Her gün 12:00 ve 21:00"
    )

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    arsiv = arsiv_yukle()
    if not arsiv:
        await update.message.reply_text("📭 Arşiv boş. Video gönder!")
        return
    metin = f"📦 Arşivde {len(arsiv)} video:\n\n"
    for i, v in enumerate(arsiv, 1):
        sure = v.get('sure_sn', 0)
        dk = sure // 60
        sn = sure % 60
        metin += f"{i}. {v.get('dosya_adi','?')} | {dk}:{sn:02d} | {v.get('yildiz',0)}⭐\n"
    await update.message.reply_text(metin)

async def paylas_komut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("📤 Paylaşım başlıyor...")
    bot = context.bot
    sonuc = await paylaşım_yap(bot)
    await update.message.reply_text(sonuc)

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        numara = int(context.args[0]) - 1
        arsiv = arsiv_yukle()
        if 0 <= numara < len(arsiv):
            silinen = arsiv.pop(numara)
            arsiv_kaydet(arsiv)
            await update.message.reply_text(f"🗑️ Silindi: {silinen.get('dosya_adi','?')}")
        else:
            await update.message.reply_text("❌ Geçersiz numara")
    except:
        await update.message.reply_text("Kullanım: /sil 1")

async def video_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin'den gelen videoyu arşive ekle"""
    if update.effective_user.id != ADMIN_ID:
        return

    msg = update.message
    video = msg.video or msg.document

    if not video:
        return

    await msg.reply_text("⏳ Video arşive ekleniyor...")

    try:
        # File ID'yi al (Telegram'da saklar, indirmez)
        file_id = video.file_id
        dosya_adi = getattr(video, 'file_name', None) or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        sure_sn = getattr(video, 'duration', 120) or 120
        yildiz = yildiz_fiyati(sure_sn)

        arsiv = arsiv_yukle()
        arsiv.append({
            "file_id": file_id,
            "dosya_adi": dosya_adi,
            "sure_sn": sure_sn,
            "yildiz": yildiz,
            "eklenme": datetime.now().isoformat(),
            "kullanildi": 0
        })
        arsiv_kaydet(arsiv)

        dk = sure_sn // 60
        sn = sure_sn % 60
        await msg.reply_text(
            f"✅ Arşive eklendi!\n\n"
            f"📹 {dosya_adi}\n"
            f"⏱️ Süre: {dk}:{sn:02d}\n"
            f"⭐ Yıldız: {yildiz}\n"
            f"📦 Toplam arşiv: {len(arsiv)} video"
        )

    except Exception as e:
        logger.error(f"Video ekleme hatası: {e}")
        await msg.reply_text(f"❌ Hata: {e}")

# --- PAYLAŞIM FONKSİYONU ---

async def paylaşım_yap(bot: Bot) -> str:
    arsiv = arsiv_yukle()

    if not arsiv:
        logger.warning("Arşiv boş, paylaşım yapılamıyor")
        await bot.send_message(ADMIN_ID, "⚠️ Arşiv boş! Video ekle: @esra_arsiv_bot")
        return "❌ Arşiv boş"

    # En az kullanılan videoyu seç
    video = min(arsiv, key=lambda x: x.get('kullanildi', 0))
    file_id = video['file_id']
    yildiz = video.get('yildiz', 350)
    caption = siradaki_caption(yildiz)

    basari = 0
    hatalar = []

    for kanal_id in KANALLAR:
        try:
            try:
                from telegram import InputPaidMediaVideo
                await bot.send_paid_media(
                    chat_id=kanal_id,
                    star_count=yildiz,
                    media=[InputPaidMediaVideo(media=file_id, supports_streaming=True)],
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                # Yıldızlı çalışmazsa normal gönder
                await bot.send_video(
                    chat_id=kanal_id,
                    video=file_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    supports_streaming=True,
                )
            basari += 1
            logger.info(f"✅ Kanal {kanal_id} → gönderildi ({yildiz}⭐)")
            await asyncio.sleep(3)

        except Exception as e:
            hatalar.append(f"Kanal {kanal_id}: {e}")
            logger.error(f"❌ Kanal {kanal_id} hatası: {e}")

    # Kullanım sayısını güncelle
    for v in arsiv:
        if v['file_id'] == file_id:
            v['kullanildi'] = v.get('kullanildi', 0) + 1
    arsiv_kaydet(arsiv)

    saat = datetime.now().strftime('%H:%M')
    if basari > 0:
        sonuc = f"✅ {saat} paylaşımı tamamlandı\n{basari}/{len(KANALLAR)} kanala gönderildi\n⭐ {yildiz} yıldız"
    else:
        sonuc = f"❌ Paylaşım başarısız\n{chr(10).join(hatalar)}"

    # Admin'e bildir
    await bot.send_message(ADMIN_ID, sonuc)
    return sonuc

# --- ZAMANLAYICI ---

async def zamanlayici(bot: Bot):
    """Her 30 saniyede kontrol et, 12:00 ve 21:00'de paylaş"""
    son_paylasim = {"saat": -1}

    while True:
        now = datetime.utcnow()
        tr_saat = (now.hour + 3) % 24

        if tr_saat in [12, 21] and son_paylasim["saat"] != tr_saat:
            logger.info(f"🕐 Otomatik paylaşım: {tr_saat}:00 TR")
            son_paylasim["saat"] = tr_saat
            await paylaşım_yap(bot)

        # Gece yarısı sıfırla
        if tr_saat == 0:
            son_paylasim["saat"] = -1

        await asyncio.sleep(30)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("liste", liste))
    app.add_handler(CommandHandler("paylas", paylas_komut))
    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_al))

    logger.info("🎬 Esra Arşiv Bot başlıyor...")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        # Zamanlayıcıyı arka planda başlat
        asyncio.create_task(zamanlayici(app.bot))

        logger.info("✅ Bot aktif — 12:00 ve 21:00 TR otomatik paylaşım")
        await asyncio.Event().wait()  # Sonsuza kadar çalış

if __name__ == "__main__":
    asyncio.run(main())


# Render free plan için health check server
import threading
import http.server

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def health_server():
    port = int(os.environ.get("PORT", 10000))
    server = http.server.HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# Health server'ı arka planda başlat
t = threading.Thread(target=health_server, daemon=True)
t.start()
