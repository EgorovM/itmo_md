#!/usr/bin/env python3
"""Скрипт для исправления дашборда Grafana."""

import json
from pathlib import Path

# Читаем дашборд
dashboard_path = (
    Path(__file__).parent.parent
    / "grafana"
    / "dashboards"
    / "bankshield-dashboard.json"
)
with open(dashboard_path) as f:
    dashboard = json.load(f)

# Получаем UID DataSource из API (или используем известный)
# В реальности нужно сделать API запрос, но для простоты используем известный UID
ds_uid = "PCC52D03280B7034C"


# Обновляем все ссылки на DataSource
def update_datasource(obj):
    if isinstance(obj, dict):
        if "datasource" in obj:
            if isinstance(obj["datasource"], dict):
                obj["datasource"]["uid"] = ds_uid
                obj["datasource"]["type"] = "postgres"
        for value in obj.values():
            update_datasource(value)
    elif isinstance(obj, list):
        for item in obj:
            update_datasource(item)


update_datasource(dashboard)

# Сохраняем обновленный дашборд
with open(dashboard_path, "w") as f:
    json.dump(dashboard, f, indent=2)

print(f"✅ Дашборд обновлен с UID DataSource: {ds_uid}")
