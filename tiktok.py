import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
import time
import random
import datetime
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
import cloudinary
import cloudinary.uploader
import requests

# DATEN
CLOUD_NAME = os.environ["CLOUD_NAME"]
API_KEY = os.environ["API_KEY"]
API_SECRET = os.environ["API_SECRET"]
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]

OUTPUT_FOLDER = "daily_tiktoks"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def generate_equation_variant():
    variant = random.choice([1, 2, 3, 4, 5, 6, 7, 8])
    
    if variant == 1:
        # einfache lineare Gleichung: 3x + 5 = 14
        m = random.randint(1, 9)
        x = random.randint(1, 9)
        b = random.randint(1, 9)
        y = m * x + b
        return f"{m}x + {b} = {y}"

    elif variant == 2:
        # Gleichung mit Klammern: 2(x + 3) = 16
        a = random.randint(1, 5)
        x = random.randint(1, 10)
        b = random.randint(1, 10)
        y = a * (x + b)
        return f"{a}(x + {b}) = {y}"

    elif variant == 3:
        # Bruchgleichung mit ganzzahligem Ergebnis: (x + 4) / 3 = 5
        x = random.randint(1, 10)
        b = random.randint(1, 10)
        y = (x + b)
        if y % 3 != 0:
            y += 3 - (y % 3)  # auf nächste teilbare Zahl aufrunden
        return f"(x + {b}) / 3 = {y // 3}"

    elif variant == 4:
        # Zwei Klammern: (x + 2)(x - 3) = ...
        r1 = random.randint(1, 5)
        r2 = random.randint(1, 5)
        return f"(x + {r1})(x - {r2}) = 0"

    elif variant == 5:
        # Quadratische Gleichung Standardform: x² + 3x + 2 = 0
        a = random.randint(1, 5)
        b = random.randint(1, 10)
        c = random.randint(1, 10)
        return f"{a}x² + {b}x + {c} = 0"

    elif variant == 6:
        # Produktform quadratische Gleichung: (x + 3)(x - 2) = 0
        r1 = random.randint(1, 9)
        r2 = random.randint(1, 9)
        return f"(x + {r1})(x - {r2}) = 0"

    elif variant == 7:
        # Negative lineare Gleichung: -3x + 5 = -10
        m = -random.randint(1, 9)
        x = random.randint(1, 9)
        b = random.randint(-10, 10)
        y = m * x + b
        return f"{m}x + {b} = {y}"

    elif variant == 8:
        # Klammerquadratische Gleichung: (x + 2)² = 49
        s = random.randint(1, 9)
        x = random.randint(1, 10)
        right = (x + s) ** 2
        return f"(x + {s})² = {right}"


def create_math_video():
    equation = generate_equation_variant()
    video_path = os.path.join("daily_tiktoks", "Vorlage.mp4")
    clip = VideoFileClip(video_path).subclip(0, 5)

    txt_clip = TextClip(
        equation,
        fontsize=130,
        color="black",
        font="Arial-Bold",
        method="caption",
        size=(clip.w, None)
    ).set_position("center").set_duration(clip.duration)

    final = CompositeVideoClip([clip, txt_clip])

    audio = AudioFileClip("sound.mp3").set_duration(final.duration)
    final = final.set_audio(audio)

    filename = f"{OUTPUT_FOLDER}/{datetime.date.today()}_{int(time.time())}_math_video.mp4"
    final.write_videofile(
        filename,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        fps=30,
        preset="medium",
        threads=4
    )
    return filename

def upload_to_cloudinary(filepath):
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=API_KEY,
        api_secret=API_SECRET
    )
    upload_result = cloudinary.uploader.upload_large(
        filepath,
        resource_type="video"
    )
    return upload_result["secure_url"]

def wait_for_media_ready(creation_id, access_token, max_wait=60, interval=5):
    status_url = f"https://graph.facebook.com/v18.0/{creation_id}?fields=status_code&access_token={access_token}"
    waited = 0
    while waited < max_wait:
        res = requests.get(status_url)
        data = res.json()
        if data.get("status_code") == "FINISHED":
            return True
        time.sleep(interval)
        waited += interval
    return False

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
        print("Media nicht fertig in Zeit. Abbruch.")
        return

    publish_payload = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }

    res_publish = requests.post(publish_url, data=publish_payload)
    print("Publish response:", res_publish.text)
    res_publish.raise_for_status()

    print("✅ Reel erfolgreich gepostet.")

if __name__ == "__main__":
    print("Starte Posting-Scheduler mit zufälligen Abständen von ca. 1 Stunde (zwischen 50 und 70 Minuten)... Stop mit STRG+C.")
    while True:
        now = datetime.datetime.now()
        if 10 <= now.hour < 20:
            print(f"Starte Post um {now.strftime('%H:%M:%S')}")
            video_path = create_math_video()
            video_url = upload_to_cloudinary(video_path)
            post_to_instagram_reels(video_url)
            
            wait_minutes = random.randint(50, 70)
            print(f"Warte {wait_minutes} Minuten bis zum nächsten Post.")
            time.sleep(wait_minutes * 60)
        else:
            # außerhalb der Zeiten: bis 10 Uhr schlafen
            next_start = now.replace(hour=10, minute=0, second=0, microsecond=0)
            if now.hour >= 20:
                next_start += datetime.timedelta(days=1)
            wait_seconds = (next_start - now).total_seconds()
            print(f"Außerhalb Post-Zeitfenster. Warte {int(wait_seconds // 60)} Minuten bis 10 Uhr.")
            time.sleep(wait_seconds)
