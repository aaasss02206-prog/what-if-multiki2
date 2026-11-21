#!/bin/bash
TOPIC="${1:-Что если бы динозавры открыли пиццерию в городе}"
COUNT="${2:-2}"
mkdir -p episodes
nohup python3 -u .opencode/skills/what-if/scripts/run_pipeline.py "$TOPIC" "$COUNT" > episodes/pipeline.log 2>&1 &
echo "Запущено в фоне! PID: $!"
echo "Смотреть ход работы: tail -f episodes/pipeline.log"
