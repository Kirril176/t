# Sekerinskiy Trader — архивы обновлений

Backtest v0.2: `sekerinskiy-trader-backtest-v0.2.zip`.

Скачать и проверить на VPS:
```bash
cd /opt/sekerinskiy-trader
curl -fL --retry 3 -o /tmp/sekerinskiy-trader-backtest-v0.2.zip https://raw.githubusercontent.com/Kirril176/t/main/sekerinskiy-trader-backtest-v0.2.zip
echo '64456b938567dc0bbea83019fa2621ff9506de141b9410ff3c332a1238a63333  /tmp/sekerinskiy-trader-backtest-v0.2.zip' | sha256sum -c -
unzip -o /tmp/sekerinskiy-trader-backtest-v0.2.zip -d /tmp/
install -m 600 /tmp/sekerinskiy-trader-backtest-v02/backtest.py ./backtest.py
install -m 600 /tmp/sekerinskiy-trader-backtest-v02/test_sekerinskiy_backtest.py ./test_sekerinskiy_backtest.py
.venv/bin/python -m unittest -v test_sekerinskiy_backtest
.venv/bin/python -u backtest.py --days 30
```

Архив не содержит API ключей и не отправляет реальные торговые ордера.

Старое содержимое репозитория сохранено в ветке `backup-before-trader-2026-11-17`.
