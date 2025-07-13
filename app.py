import os
import time
import random
import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
import cloudinary
import cloudinary.uploader
import requests

# === ENV ===
CLOUD_NAME = os.environ.get("CLOUD_NAME")
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
OUTPUT_FOLDER = "daily_tiktoks"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

if not all([CLOUD_NAME, API_KEY, API_SECRET, INSTAGRAM_USER_ID, ACCESS_TOKEN]):
    raise EnvironmentError("Mindestens eine Umgebungsvariable fehlt (CLOUD_NAME, API_KEY, API_SECRET, INSTAGRAM_USER_ID, ACCESS_TOKEN)")

# === Equation Generator ===
def generate_equation_variant():
    variant = random.randint(1, 8)

    if variant == 1:
        m, x, b = random.randint(1, 9), random.randint(1, 9), random.randint(1, 9)
        y = m * x + b
        return f"{m}x + {b} = {y}"
    elif variant == 2:
        a, x, b = random.randint(1, 5), random.randint(1, 10), random.randint(1, 10)
        return f"{a}(x + {b}) = {a * (x + b)}"
    elif variant == 3:
        x, b = random.randint(1, 10), random.randint(1, 10)
        y = x + b
        y += (3 - y % 3) if y % 3 != 0 else 0
        return f"(x + {b}) / 3 = {y // 3}"
    elif variant == 4 or variant == 6:
        r1, r2 = random.randint(1, 5), random.randint(1, 5)
        return f"(x + {r1})(x - {r2}) = 0"
    elif variant == 5:
        while True:
            a, b, c = random.randint(1, 5), random.randint(1, 10), random.randint(1, 10)
            if b**2 - 4*a*c > 0:
                return f"{a}x² + {b}x + {c} = 0"
    elif variant == 7:
        m, x, b = -random.randint(1, 9), random.randint(1, 9), random.randint(-10, 10)
        y = m * x + b
        return f"{m}x + {b} = {y}"
    elif variant == 8:
        s, x = random.randint(1, 9), random.randint(1, 10)
        return f"(x + {s})² = {(x + s) ** 2}"

# === Text to Image ===
def create_text_image(text, width, height):
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Arial.ttf", 55)
    except Exception:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - w) // 2, (height - h) // 2), text, font=font, fill="black")
    return np.array(img)

# === Video erstellen ===
def create_math_video():
    equation = generate_equation_variant()
    print(f"[INFO] Generierte Gleichung: {equation}")

    template_path = os.path.join(OUTPUT_FOLDER, "Vorlage.mp4")
    print(f"[DEBUG] Suche Vorlage unter: {template_path}")

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Vorlage.mp4 nicht gefunden unter: {template_path}")

    clip = VideoFileClip(template_path).subclip(0, 3).resize(height=1080)
    text_np = create_text_image(equation, clip.w, 200)
    text_clip = ImageClip(text_np, duration=clip.duration).set_position("center")
    final = CompositeVideoClip([clip, text_clip])

    filename = os.path.join(OUTPUT_FOLDER, f"{datetime.date.today()}_{int(time.time())}_math_video.mp4")
    final.write_videofile(filename, codec="libx264", audio=False, fps=24, preset="ultrafast", threads=2)

    print(f"[INFO] Video gespeichert: {filename}")
    return filename

# === Upload to Cloudinary ===
def upload_to_cloudinary(filepath):
    cloudinary.config(cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET)
    print(f"[INFO] Upload von {filepath} zu Cloudinary gestartet.")
    res = cloudinary.uploader.upload_large(filepath, resource_type="video")
    print(f"[INFO] Upload fertig, URL: {res['secure_url']}")
    return res["secure_url"]

# === Media Status warten ===
def wait_for_media_ready(creation_id, access_token, max_wait=60, interval=5):
    url = f"https://graph.facebook.com/v18.0/{creation_id}?fields=status_code&access_token={access_token}"
    waited = 0
    while waited < max_wait:
        res = requests.get(url)
        status = res.json().get("status_code")
        print(f"[DEBUG] Media Status: {status}")
        if status == "FINISHED":
            return True
        time.sleep(interval)
        waited += interval
    return False

# === Post to Instagram ===
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
    res.raise_for_status()
    creation_id = res.json()["id"]

    if not wait_for_media_ready(creation_id, ACCESS_TOKEN):
        print("[ERROR] Media nicht bereit – Abbruch.")
        return

    res_pub = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    })
    res_pub.raise_for_status()
    print("[INFO] Reel erfolgreich gepostet.")

# === Flask App ===
app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def trigger_post():
    if request.method == "HEAD":
        return "", 200

    try:
        now = datetime.datetime.now()
        print(f"[INFO] Trigger gestartet um {now}")
        if 10 <= now.hour < 20:
            video_path = create_math_video()
            video_url = upload_to_cloudinary(video_path)
            post_to_instagram_reels(video_url)
            return "✅ Reel gepostet", 200
        else:
            print("[INFO] Nicht im Zeitfenster 10–20 Uhr")
            return "⏳ Zeitfenster nicht erreicht", 200
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        return f"❌ Fehler: {e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
