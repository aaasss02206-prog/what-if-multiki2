import os, sys, time, json, subprocess

def run_with_retry(cmd, retries=5, delay=5):
    for attempt in range(1, retries + 1):
        res = subprocess.run(cmd, shell=True)
        if res.returncode == 0:
            return True
        print(f"[Попытка {attempt}/{retries}] Сбой команды, повтор через {delay} сек...", flush=True)
        time.sleep(delay)
    return False

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "Что если бы динозавры открыли пиццерию в городе"
    count = sys.argv[2] if len(sys.argv) > 2 else "2"
    os.makedirs("episodes", exist_ok=True)

    print(f"=== СТАРТ ПАЙПЛАЙНА: '{topic}' ({count} сцен) ===", flush=True)
    ok_prep = run_with_retry(f'python3 .opencode/skills/what-if/scripts/prepare_episode.py "{topic}" {count}')
    if not ok_prep:
        print("ОШИБКА: Не удалось подготовить исходники после 5 попыток.", flush=True)
        sys.exit(1)

    print("=== ОТПРАВКА НА KAGGLE GPU ===", flush=True)
    ok_kaggle = run_with_retry("python3 .opencode/skills/what-if/scripts/kaggle_render.py")
    if not ok_kaggle:
        print("ОШИБКА: Сбой при работе с Kaggle API.", flush=True)
        sys.exit(1)

    print("=== ГОТОВО! Проверьте папку episodes/ ===", flush=True)

if __name__ == "__main__":
    main()
