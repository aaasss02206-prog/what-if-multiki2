import os, time, json, subprocess

SLUG = "yavuzismailov/what-if-live-3d-studio"
DATASET_SLUG = "yavuzismailov/what-if-current-assets"

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def push_assets():
    meta = {
        "title": "what-if-current-assets",
        "id": DATASET_SLUG,
        "licenses": [{"name": "CC0-1.0"}]
    }
    with open("kaggle_job/assets/dataset-metadata.json", "w") as f:
        json.dump(meta, f)
    res = run("kaggle datasets version -p kaggle_job/assets -m 'update 2d assets' -r zip")
    if res.returncode != 0:
        run("kaggle datasets create -p kaggle_job/assets -r zip")

def push_and_wait():
    push_assets()
    with open("kaggle_job/kernel-metadata.json", "r") as f:
        kmeta = json.load(f)
    kmeta["dataset_sources"] = [DATASET_SLUG]
    with open("kaggle_job/kernel-metadata.json", "w") as f:
        json.dump(kmeta, f, indent=2)

    print("Отправка задачи на видеокарту Kaggle T4...", flush=True)
    push_res = run("kaggle kernels push -p kaggle_job")
    print(push_res.stdout, push_res.stderr, flush=True)

    while True:
        time.sleep(25)
        status = run(f"kaggle kernels status {SLUG}").stdout.strip()
        print("Статус:", status, flush=True)
        if "complete" in status.lower() or "error" in status.lower():
            break

    os.makedirs("episodes", exist_ok=True)
    out_res = run(f"kaggle kernels output {SLUG} -p episodes")
    print(out_res.stdout, out_res.stderr, flush=True)

if __name__ == "__main__":
    push_and_wait()
