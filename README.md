# Skillstorm — сайт игры

Промо-сайт Skillstorm: живой 3D-архипелаг (three.js, WebGPU с откатом на WebGL2), главы-острова,
бой прямо в браузере, ролики из игры, паутина комбо и карта-пергамент.

- `site/` — сам сайт, публикуется на GitHub Pages (`.github/workflows/pages.yml`) при каждом пуше в `main`.
- `serve.py` — локальный сервер: `python serve.py` → http://127.0.0.1:8099 (принимает кадры `__ss.shot()` в `shots/`).
- `tools_tripo/` — острова: вырезка из картины, Tripo-генерация, подготовка в Blender, раскладка (`build_islands.py`),
  скрипты правок страницы (лендинг, карта, паутина комбо — `build_combo_web.py`).
- `tools_islands/`, `tools_props/` — ранние процедурные острова и пропсы.
- `build_assets.py` — веб-версии артов и скриншотов игры.
- `vendor-assets/` — паки Kenney (CC0) и модули three.js (MIT).

Ролики глав записываются в игре скриптом `Downloads/Skillstorm/clips/_specs/record_site_beats.ps1`
(основной репозиторий игры, `tools/record-clip.ps1`).

Иконки навыков и титулов — game-icons.net, CC BY 3.0.
