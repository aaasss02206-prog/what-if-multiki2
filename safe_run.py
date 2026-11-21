import sys, subprocess
if len(sys.argv) < 2:
    sys.exit("Укажите файл")
target = sys.argv.pop(1)
with open(target, "r", encoding="utf-8") as f:
    code = f.read()
fixed = code.replace('EPISODES["scenes"]', 'EPISODES[0]["scenes"]').replace('for tx in:', 'for tx in (130, 190, 260, 310):')
if fixed != code:
    with open(target, "w", encoding="utf-8") as f:
        f.write(fixed)
subprocess.run([sys.executable, "-u", target])
