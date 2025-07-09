import os
import time
import random
import datetime
import socket
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Fix für Pillow ≥ 10.0 (ANTIALIAS entfernt)
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
import cloudinary
import cloudinary.uploader
import requests
import threading
from http.server import SimpleHTTPRequestHandler
import socketserver

# === ENV-VARIABLEN ===
CLOUD_NAME = os.environ["CLOUD_NAME"]
API_KEY = os.environ["API_KEY"]
API_SECRET = os.environ["API_SECRET"]
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]

OUTPUT_FOLDER = "daily_tiktoks"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === PORT-CHECK ===
def check_port(port=8080):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            s.listen(1)
            print(f"Port {port} ist frei.")
            return True
        except OSError:
            print(f"Port {port} ist bereits belegt.")
            return False

# === GLEICHUNGSGENERATOR ===
def generate_equation_variant():
    variant = random.choice([1, 2, 3, 4, 5, 6, 7, 8])
    
    if variant == 1:
        m = random.randint(1, 9)
        x = random.randint(1, 9)
        b = random.randint(1, 9)
        y = m * x + b
        return f"{m}x + {b} = {y}"

    elif variant == 2:
        a = random.randint(1, 5)
        x = random.randint(1, 10)
        b = random.randint(1, 10)
        y = a * (x + b)
        return f"{a}(x + {b}) = {y}"

    elif variant == 3:
        x = random.randint(1, 10)
        b = random.randint(1, 10)
        y = (x + b)
        if y % 3 != 0:
            y += 3 - (y % 3)
        return f"(x + {b}) / 3 = {y // 3}"

    elif variant == 4:
        r1 = random.randint(1, 5)
        r2 = random.randint(1, 5)
        return f"(x + {r1})(x - {r2}) = 0"

    elif variant == 5:
    # Quadratische Gleichung mit reellen Lösungen
        while True:
            a = random.randint(1, 5)
            b = random.randint(1, 10)
            c = random.randint(1, 10)
            discriminant = b**2 - 4*a*c
            if discriminant > 0:
                return f"{a}x² + {b}x + {c} = 0"


    elif variant == 6:
        r1 = random.randint(1, 9)
        r2 = random.randint(1, 9)
        return f"(x + {r1})(x - {r2}) = 0"

    elif variant == 7:
        m = -random.randint(1, 9)
        x = random.randint(1, 9)
        b = random.randint(-10, 10)
        y = m * x + b
        return f"{m}x + {b} = {y}"

    elif variant == 8:
        s = random.randint(1, 9)
        x = random.randint(1, 10)
        right = (x + s) ** 2
        return f"(x + {s})² = {right}"

# === TEXTBILD ERSTELLEN ===
def create_text_image(text, width, height):
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Arial.ttf", 55)
    except:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 55) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") else ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - w) // 2, (height - h) // 2), text, font=font, fill="black")
    return np.array(img)

# === VIDEO ERSTELLEN ===
def create_math_video():
    equation = generate_equation_variant()
    clip = VideoFileClip(os.path.join(OUTPUT_FOLDER, "Vorlage.mp4")).subclip(0, 3)
    clip = clip.resize(height=1080)
    text_np = create_text_image(equation, clip.w, 200)
    text_clip = ImageClip(text_np, duration=clip.duration).set_position("center")
    final = CompositeVideoClip([clip, text_clip])
    filename = os.path.join(OUTPUT_FOLDER, f"{datetime.date.today()}_{int(time.time())}_math_video.mp4")
    final.write_videofile(filename, codec="libx264", audio=False, fps=24, preset="ultrafast", threads=2)
    return filename

# === CLOUDINARY UPLOAD ===
def upload_to_cloudinary(filepath):
    cloudinary.config(cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET)
    res = cloudinary.uploader.upload_large(filepath, resource_type="video")
    return res["secure_url"]

# === STATUS ABFRAGEN ===
def wait_for_media_ready(creation_id, access_token, max_wait=60, interval=5):
    url = f"https://graph.facebook.com/v18.0/{creation_id}?fields=status_code&access_token={access_token}"
    waited = 0
    while waited < max_wait:
        res = requests.get(url)
        if res.json().get("status_code") == "FINISHED":
            return True
        time.sleep(interval)
        waited += interval
    return False

# === INSTAGRAM REEL POSTEN ===
def post_to_instagram_reels(video_url, caption="Can you solve this? #math #reel #puzzle"):
    create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_USER_ID}/media"
    publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_USER_ID}/media_publish"

    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }

    res = requests.post(create_url, data=payload)
    print("Create media response:", res.text)
    res.raise_for_status()
    creation_id = res.json()["id"]

    if not wait_for_media_ready(creation_id, ACCESS_TOKEN):
        print("❌ Media nicht bereit – Abbruch.")
        return

    publish_payload = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }

    res_pub = requests.post(publish_url, data=publish_payload)
    print("Publish response:", res_pub.text)
    res_pub.raise_for_status()
    print("✅ Reel erfolgreich gepostet.")

# === DUMMY HTTP SERVER ===
def start_dummy_server(port=8080):
    def run_server():
        try:
            with socketserver.TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
                print(f"🌐 Dummy-HTTP-Server läuft auf Port {port}")
                httpd.serve_forever()
        except OSError as e:
            print(f"⚠️ Dummy-Server konnte nicht starten: {e}. Wahrscheinlich läuft er schon.")

    if check_port(port):
        threading.Thread(target=run_server, daemon=True).start()
    else:
        print(f"⚠️ Port {port} belegt – Dummy-Server wird nicht erneut gestartet.")

# === MAIN LOOP ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    start_dummy_server(port)

    print("📅 Scheduler läuft: Postet automatisch von 10–20 Uhr alle 50–70 Minuten. Abbruch mit STRG+C.")

    while True:
        now = datetime.datetime.now()

        if 10 <= now.hour < 20:
            print(f"\n⏰ Post gestartet um {now.strftime('%H:%M:%S')}")

            try:
                video_path = create_math_video()
                video_url = upload_to_cloudinary(video_path)
                post_to_instagram_reels(video_url)
            except Exception as e:
                print(f"❌ Fehler: {e}")

            wait_minutes = random.randint(50, 70)
            next_post = now + datetime.timedelta(minutes=wait_minutes)

            # Prüfen, ob nächster Post noch im Zeitfenster liegt
            if next_post.hour < 20:
                print(f"⏳ Warte {wait_minutes} Minuten (bis {next_post.strftime('%H:%M')}) bis zum nächsten Post.")
                time.sleep(wait_minutes * 60)
            else:
                # Warten bis zum nächsten Tag um 10:00
                next_start = now.replace(hour=10, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                wait_seconds = (next_start - now).total_seconds()
                print(f"🌙 Geplante nächste Zeit ({next_post.strftime('%H:%M')}) liegt außerhalb der Postzeit. Warte bis morgen 10:00 Uhr.")
                time.sleep(wait_seconds)

