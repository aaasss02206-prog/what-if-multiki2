import os, json, time, shutil, glob, asyncio, subprocess, base64
import requests
import numpy as np
import cv2
import edge_tts
from gtts import gTTS

# ==========================================
# НАСТРОЙКИ СЕРИИ
# ==========================================
TOPIC = "Ночь в глухой зимней деревне: бабушка уехала и оставила 7 строгих правил выживания до рассвета, а из леса приходят сущности, говорящие голосами близких"
TOTAL_ACTS = 4          # 4 главы по ~2.5 минуты = ~10 минут (для быстрого теста ставьте 1)
SCENES_PER_ACT = 25     # 25 сцен в главе (для быстрого теста ставьте 4)
RUN_ONLY_ACT = None     # None = весь фильм; или номер главы (1, 2, 3, 4)

BASE_DIR = "horror_movie"
CLIPS_DIR = f"{BASE_DIR}/clips"
TEMP_DIR = "/tmp/render_temp"
os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

CF_ACCOUNT_ID = base64.b64decode("ZDFjNTgxZWI0NTFhODIzNjMzYmMwMTY2MzYzNmU0OGY=").decode()
CF_API_TOKEN = base64.b64decode("Y2Z1dF9VZG1ONVZQeXVYb1h4SlVYY3VuSmwzaGtidm1yNWZhMXNRMGdpMmxsODYxODk5ZDM=").decode()
CF_BASE = base64.b64decode("aHR0cHM6Ly9hcGkuY2xvdWRmbGFyZS5jb20vY2xpZW50L3Y0").decode()
HEADERS = {"Authorization": f"Bearer {CF_API_TOKEN}"}

STYLE_HORROR_3D = (
    "High-budget 3D animated dark thriller movie still, Unreal Engine 5 and Pixar cinematic lighting, "
    "hyper-detailed realistic skin texture, subsurface scattering, dramatic chiaroscuro shadows, "
    "dimly lit old wooden Russian village house at winter night, warm amber stove glow vs cold eerie blue window light, "
    "medium close-up portrait facing camera, depth of field, 8k render, "
)

HERO_BIBLE = (
    "Max, a 20-year-old pale Russian young man with messy dark hair, dark circles under expressive eyes, "
    "wearing a worn grey hoodie"
)

def get_or_create_script():
    script_path = f"{BASE_DIR}/horror_script.json"
    if os.path.exists(script_path):
        print("📂 Загружен уже сохранённый сценарий...")
        with open(script_path, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"{CF_BASE}/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    outline_prompt = (
        f"Create a chilling {TOTAL_ACTS}-act horror story outline in Russian based on: '{TOPIC}'. "
        "Include creepy survival rules, knocking on windows/doors at night, voice mimicry from the woods, and an eerie twist. "
        "Return ONLY valid JSON with key 'acts_summary' (array of strings describing each act)."
    )
    resp = requests.post(url, headers=HEADERS, json={"messages": [{"role": "user", "content": outline_prompt}]}, timeout=60).json()
    raw = resp["result"]["response"]
    acts_summary = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])["acts_summary"]

    full_data = {"acts": []}
    for act_idx, act_plot in enumerate(acts_summary, start=1):
        print(f"✍️ Пишу Главу {act_idx}/{TOTAL_ACTS}...")
        act_prompt = (
            f"Write Act {act_idx} ({SCENES_PER_ACT} scenes) of a tense Russian horror story. "
            f"Act plot: '{act_plot}'. Main hero: {HERO_BIBLE}. "
            "Alternate between Max's terrified first-person narration and eerie dialogue lines (grandmother, neighbor, or creepy entity). "
            "Return ONLY valid JSON with key 'scenes' — array of objects with keys: "
            "'scene_id' (int 1..N), "
            "'speaker' ('max', 'babushka', or 'entity'), "
            "'emotion' ('fear', 'panic', 'shock', or 'calm'), "
            "'visual_details' (English detailed visual prompt: facial expression, cold sweat drops, trembling lips, shadow lighting, background detail), "
            "'text' (gripping Russian narration or dialogue line, 12-18 words)."
        )
        for _ in range(5):
            try:
                r = requests.post(url, headers=HEADERS, json={"messages": [{"role": "user", "content": act_prompt}]}, timeout=90).json()
                t = r["result"]["response"]
                scenes = json.loads(t[t.find("{"):t.rfind("}") + 1])["scenes"]
                full_data["acts"].append({"act_num": act_idx, "scenes": scenes})
                break
            except Exception:
                time.sleep(3)

    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    return full_data

def generate_3d_frame(prompt, out_path):
    url_flux = f"{CF_BASE}/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    for _ in range(5):
        try:
            resp = requests.post(url_flux, headers=HEADERS, json={"prompt": prompt}, timeout=60)
            res_json = resp.json()
            if resp.status_code == 200 and "image" in res_json.get("result", {}):
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(res_json["result"]["image"]))
                return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Сбой генерации 3D-кадра")

async def synthesize_horror_voice(text, speaker, emotion, out_mp3):
    if speaker == "babushka":
        voice, rate, pitch = "ru-RU-SvetlanaNeural", "-10%", "-12Hz"
    elif speaker == "entity":
        voice, rate, pitch = "ru-RU-DmitryNeural", "-16%", "-18Hz"
    else:
        voice = "ru-RU-DmitryNeural"
        if emotion in ("fear", "panic"):
            rate, pitch = "+10%", "+4Hz"
        elif emotion == "shock":
            rate, pitch = "-12%", "-5Hz"
        else:
            rate, pitch = "-2%", "-2Hz"

    try:
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out_mp3)
    except Exception:
        gTTS(text=text, lang="ru").save(out_mp3)

def render_scene_fx(img_path, mp3_path, emotion, clip_path):
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    base_anim = f"{TEMP_DIR}/base.mp4"
    subprocess.run(
        f'ffmpeg -y -loop 1 -i "{img_path}" -i "{mp3_path}" '
        f'-vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" '
        f'-c:v libx264 -preset fast -crf 18 -r 24 -shortest "{base_anim}"',
        shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    cap = cv2.VideoCapture(base_anim)
    fps = 24.0
    w, h = 1280, 720
    fx_vid = f"{TEMP_DIR}/fx.mp4"
    writer = cv2.VideoWriter(fx_vid, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt(((X - w/2)/(w*0.65))**2 + ((Y - h/2)/(h*0.65))**2)
    vignette = np.clip(1.0 - 0.45 * (dist**2), 0.35, 1.0)[:, :, np.newaxis]

    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = idx / fps
        if emotion == "panic":
            dx = np.sin(t * 55.0) * 4.5 + np.cos(t * 37.0) * 2.5
            dy = np.cos(t * 61.0) * 4.0
            scale = 1.04 + min(0.06, t * 0.01)
        elif emotion == "fear":
            dx = np.sin(t * 42.0) * 2.5
            dy = np.cos(t * 47.0) * 2.0
            scale = 1.02 + min(0.04, t * 0.006)
        else:
            dx = np.sin(t * 1.4) * 2.5
            dy = np.cos(t * 1.2) * 2.0
            scale = 1.01 + min(0.03, t * 0.004)

        M = cv2.getRotationMatrix2D((w * 0.5, h * 0.5), 0, scale)
        M += dx
        M += dy
        out_f = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        out_f = (out_f.astype(np.float32) * vignette).astype(np.uint8)
        writer.write(out_f)
        idx += 1

    cap.release()
    writer.release()

    subprocess.run(
        f'ffmpeg -y -i "{fx_vid}" -i "{mp3_path}" -c:v libx264 -preset fast -crf 17 -c:a aac -b:a 192k -shortest "{clip_path}"',
        shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

async def main():
    script_data = get_or_create_script()
    for act in script_data["acts"]:
        act_num = act["act_num"]
        if RUN_ONLY_ACT and act_num != RUN_ONLY_ACT:
            continue

        print(f"\n🕯️ === ГЛАВА {act_num} ИЗ {TOTAL_ACTS} ===")
        act_clips = []

        for s in act["scenes"]:
            sid = f"act{act_num:02d}_sc{s['scene_id']:03d}"
            clip_p = f"{CLIPS_DIR}/{sid}.mp4"
            act_clips.append(clip_p)

            if os.path.exists(clip_p) and os.path.getsize(clip_p) > 10000:
                print(f"⏭️ {sid} уже готова, пропускаю...")
                continue

            img_p = f"{TEMP_DIR}/img.png"
            mp3_p = f"{TEMP_DIR}/aud.mp3"
            emo = s.get("emotion", "fear")
            spk = s.get("speaker", "max")

            print(f"🎥 {sid} [{spk.upper()} | {emo.upper()}]: рендер...")
            subject = HERO_BIBLE if spk == "max" else "Mysterious eerie shadow figure outside a frosted winter window or dimly lit rustic hallway"
            prompt = f"{STYLE_HORROR_3D} {subject}, {s['visual_details']}"

            generate_3d_frame(prompt, img_p)
            await synthesize_horror_voice(s["text"], spk, emo, mp3_p)
            render_scene_fx(img_p, mp3_p, emo, clip_p)

        act_concat = f"{BASE_DIR}/concat_ch_{act_num}.txt"
        with open(act_concat, "w") as f:
            for c in act_clips:
                if os.path.exists(c):
                    f.write(f"file '{c}'\n")
        act_out = f"{BASE_DIR}/HORROR_CHAPTER_{act_num}.mp4"
        subprocess.run(f'ffmpeg -y -f concat -safe 0 -i "{act_concat}" -c copy "{act_out}"', shell=True, check=True)
        print(f"✅ Глава {act_num} собрана: {act_out}")

    if not RUN_ONLY_ACT:
        full_concat = f"{BASE_DIR}/concat_full.txt"
        with open(full_concat, "w") as f:
            for c in sorted(glob.glob(f"{CLIPS_DIR}/*.mp4")):
                f.write(f"file '{c}'\n")
        final_movie = f"{BASE_DIR}/HORROR_STORY_FULL_10MIN.mp4"
        subprocess.run(f'ffmpeg -y -f concat -safe 0 -i "{full_concat}" -c copy "{final_movie}"', shell=True, check=True)
        print(f"\n🏆 ГОТОВО! Полный фильм: {final_movie}")

if __name__ == "__main__":
    asyncio.run(main())
