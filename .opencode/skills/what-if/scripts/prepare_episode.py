import os, json, base64, asyncio, requests
import edge_tts
from gtts import gTTS

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN")
CF_BASE = base64.b64decode("aHR0cHM6Ly9hcGkuY2xvdWRmbGFyZS5jb20vY2xpZW50L3Y0L2FjY291bnRzLw==").decode()
HEADERS = {"Authorization": f"Bearer {CF_API_TOKEN}"}

STYLE_PREFIX = (
    "High-budget 2D animated series still, Disney and Gravity Falls style, "
    "clean crisp lineart, vibrant cel-shaded colors, wide establishing shot, "
    "full body view from head to toe, expressive pose, "
)

def generate_script(topic: str, scenes_count: int = 50):
    url = f"{CF_BASE}{CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    prompt = (
        f"Create a {scenes_count}-scene 2D animated cartoon script on topic: '{topic}'. "
        "Return ONLY a valid JSON object with two keys: "
        "'character_bible' (exact visual description of the main 2D character's hair, clothes, colors in English) and "
        "'scenes' (array of objects with keys: 'scene_id' (int), 'type' ('talk_gesture' for dialogue with expressive hand gestures and lip-sync, or 'action' for walking/running/dynamic movement), "
        "'scene_desc' (English description of setting and pose), "
        "'motion_prompt' (English description of smooth 2D hand gestures, facial expressions, and body movement), "
        "'text_ru' (Russian dialogue line, 12-18 words), 'text_en' (English dialogue line, 12-18 words), 'gender' ('male' or 'female'))."
    )
    resp = requests.post(url, headers=HEADERS, json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 4096})
    raw = resp.json()["result"]["response"]
    start, end = raw.find("{"), raw.rfind("}") + 1
    return json.loads(raw[start:end])

def generate_2d_image(prompt: str, out_path: str):
    url_flux = f"{CF_BASE}{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    resp = requests.post(url_flux, headers=HEADERS, json={"prompt": prompt})
    if resp.status_code == 200 and "image" in resp.json().get("result", {}):
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(resp.json()["result"]["image"]))
        return True
    url_sdxl = f"{CF_BASE}{CF_ACCOUNT_ID}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning"
    resp = requests.post(url_sdxl, headers=HEADERS, json={"prompt": prompt})
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return True

async def synthesize_voice(text: str, lang: str, gender: str, out_path: str):
    voices = {
        ("ru", "female"): "ru-RU-SvetlanaNeural",
        ("ru", "male"): "ru-RU-DmitryNeural",
        ("en", "female"): "en-US-AvaNeural",
        ("en", "male"): "en-US-AndrewNeural",
    }
    try:
        await edge_tts.Communicate(text, voices[(lang, gender)]).save(out_path)
    except Exception:
        gTTS(text=text, lang=lang).save(out_path)

async def build_assets(topic: str, scenes_count: int = 50):
    os.makedirs("kaggle_job/assets", exist_ok=True)
    data = generate_script(topic, scenes_count)
    bible = data.get("character_bible", "")
    scenes = data.get("scenes", [])

    for s in scenes:
        sid = f"{s['scene_id']:03d}"
        full_prompt = f"{STYLE_PREFIX} {bible}, {s['scene_desc']}"
        generate_2d_image(full_prompt, f"kaggle_job/assets/img_{sid}.png")
        await synthesize_voice(s["text_ru"], "ru", s["gender"], f"kaggle_job/assets/ru_{sid}.mp3")
        await synthesize_voice(s["text_en"], "en", s["gender"], f"kaggle_job/assets/en_{sid}.mp3")

    with open("kaggle_job/assets/manifest.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Готово! Создано {len(scenes)} 2D-сцен с единым дизайном персонажа.")

if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "Что если бы динозавры открыли пиццерию в городе"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    asyncio.run(build_assets(topic, count))
