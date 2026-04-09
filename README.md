```
cd /Users/lev/sinteh
source .venv/bin/activate
pip install -r requirements.txt
python create_food.py
python create_users.py --users-per-district 500 --output users.json
python calibrate.py
python simulate_demand.py --users users.json --food food.json --weights calibration.json
python generate_client_report_pdf.py --input demand_report.json --food food.json --output client_report.pdf
```

Сценарии `simulate_demand.py` по умолчанию: **промо** `−55 ₽` на позицию **№4** (медовая курица), **удаление** позиции **№19** (фокачча), **новое блюдо** — боул с индейкой и булгуром. Параметры: `--price-item-index`, `--price-delta-rub`, `--remove-item-index`, `--new-item-json`.# sintech
