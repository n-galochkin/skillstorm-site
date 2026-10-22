# UE 5.8 в браузере — разведка (2026-10-20)

Черновик вне проекта. Решение принимается в чате; здесь доказательства и детали.

## Вывод в одну строку

Официального пути нет и не предвидится, но есть работающий сторонний: **SimplyStream (Wonder Interactive)** собирает проекты на UE 5.8/6.0 в WebAssembly+WebGPU. Проверено лично — их сборка Cropout идёт в браузере 60 FPS при 38 МБ загрузки. Риск не технический, а зависимость от вендора; отдельный вопрос — телефоны.

## Что проверено лично (не со слов вендора)

Открыл их публичную демку Cropout (`https://simplystream.dev/uehati8z`) в своём браузере:

| Параметр | Факт |
|---|---|
| Загрузка | **38 МБ**, скорость 12 МБ/с |
| Время до главного меню | ~25 с (загрузка + прогрев шейдеров) |
| FPS в игре | **60** (их же оверлей Performance Metrics) |
| Latency | 0 мс — рендер на моей GPU, не видеострим |
| GPU | Intel Xe-LPG (встроенная), WebGPU включён |
| Изоляция | `crossOriginIsolated: true`, `SharedArrayBuffer` есть → многопоточный wasm |
| Упаковка страницы | игра внутри `iframe` на их домене `simplystream.dev/<slug>` |

Дефекты, которые видно глазом: в главном меню чёрные квадраты-артефакты и сильный пересвет; в игре (топ-даун остров) картинка чистая. Сцена Cropout — ровно наша арт-база, так что это близкий к нам тест, а не абстрактный бенчмарк.

Прочие их демки: Lyra, Electric Dreams (PCG), City Sample, Game Animation Sample, SpaceLancers (UE6, мультиплеер). Все отмечены как прошедшие проверку в режимах SM5 и ES3.1.

## Карта вариантов

### 1. Официальный Epic — нет
HTML5-таргет выкинут после UE 4.24, в UE5 веб-таргета нет, в 5.8 ничего не изменилось. Рынок предсказаний даёт ~7% на появление официальной поддержки WebGPU до 2027. Официальный ответ Epic на «игра в браузере» — Pixel Streaming, то есть видеострим с сервера.

### 2. SimplyStream / Wonder Interactive — рабочий путь
- Движок: **их форк UE 5.8 и 6.0**; линия выбирается при создании проекта, сборка всегда на свежем релизе линии.
- Сборка идёт **на их машинах** (агент Strata). Локально паковать не надо, Windows как хост поддержан.
- Пайплайн: `strata init --repo <name>` → `strata commit` → `strata push` из папки с `.uproject`. Своя история файлов, `.git` игнорируется, работает рядом с git. На выходе — ссылка «играть», сборка автоматически проверяется на реальной GPU в режимах SM5 и ES3.1, битый кадр валит проверку.
- Память: 32-битный wasm, **потолок кучи 3998 МБ** — всё, что игра держит в пике, должно влезть.
- Цены: Free — 2 сборки в день, 1 место, $10 кредитов на облачный стрим. Indie — **$25/мес**, сборки без лимита, 2 параллельно. Studio — $250/мес. **Рендер в браузере игроку бесплатен — $0 за минуту**; по минутам тарифицируется только облачный стрим как запасной путь.
- Компания: Wonder Interactive, показывали Lyra в WebGPU ещё в 2024, тех-ревил на Unreal Fest. Не Epic, не эндорснуты Epic.

### 3. Свободный форк PooyaEimandar/UnrealEngine-WebGPU — не для нас
UE 5.8.3, ветка `5.8-webgpu`, рендер через мобильный рендерер UE. Поддержано: C++/BP, скелетная анимация, Chaos, Slate/UMG, тач, стриминг ассетов. Не запланированы: Nanite, Lumen, RT, Virtual Shadow Maps, Live Coding. **Паковка проверена только на macOS Apple Silicon**, Windows «coming soon». 7 коммитов, 1 звезда, доступ к форку по заявке. Как опора под продакшен — нет.

### 4. Pixel Streaming — дорого на публичном лендинге
Настоящий билд, настоящий баланс, тач в браузере поддержан. Но GPU-машина на каждого одновременного игрока: голое железо от ~$0.24–1.0/час за GPU (CoreWeave, AWS g4dn/g5), готовые платформы — Eagle3D от $100 за одновременного пользователя в месяц либо от $0.10/мин. Для лендинга, куда может прийти толпа после ролика, это неуправляемый счёт и очередь.

### 5. Своя веб-реализация боя (TypeScript + WebGPU)
Полный контроль, мегабайты вместо десятков мегабайт, гарантированно работает на телефоне. Цена — вторая кодовая база боя, которая расходится с игрой при каждой правке.

## Что это значит для нашего проекта

Наш стек против веб-пути:

| Наше | Статус в веб-сборке |
|---|---|
| Lumen + HW RT (`r.DynamicGlobalIlluminationMethod=1`) | В вебе рендерер мобильный/ES3.1. Lumen не будет — картинка пойдёт по мобильному пути, который у нас и так обязан работать (`r.Mobile.ShadingPath=0`, `MobileHDR=1`) |
| PCG | Косвенно подтверждено: их демка Electric Dreams — витрина PCG |
| Cropout-арт (наша база) | Подтверждено прямым запуском |
| GAS, StateTree, Mover, CommonUI, MVVM, Niagara | Не документировано. Движковые плагины, шанс высокий, но нужна проверка сборкой |
| **Mutable** | Главный риск. Рантайм-кастомизация персонажа. **Для демки не нужна вовсе** — один сет виладжера можно собрать обычными скелетными мешами и плагин выключить |
| Content 1.8 ГБ | В демку не лезет. Нужен обрезанный таргет: один остров, один сет, одно оружие, вырезанные паки (`PPFantasyWeapons` 153 МБ, `Inferno_World_Free` 81 МБ, `SourceArt` 69 МБ, `Environment` 457 МБ — чистится по задаче) |

Ориентир по размеру: Cropout = 38 МБ. Наша демка того же порядка, если резать жёстко.

## Мобильные браузеры — отдельный вопрос

API есть везде:
- **iOS/iPadOS 26+**: Safari 26 включил WebGPU по умолчанию; на iOS все браузеры на WebKit, значит Chrome на айфоне получает то же самое.
- **Android**: Chrome с версии 121 на Android 12+ (Qualcomm/ARM/Intel GPU). Firefox на Android — ещё нет, целятся в конец 2026.

Но API — не главное. Главное — **память**. На iOS Safari заявленный wasm-максимум в 2 ГБ валится ещё на инициализации; практический потолок по сообщениям разработчиков — сотни мегабайт, причём Safari не возвращает ошибку, а **убивает вкладку** без предупреждения. Куча UE-сборки объявлена в 3998 МБ. То есть айфон — зона риска, и упрётся это не в красоту, а в «вкладка перезагрузилась».

Вендор про телефоны не пишет ничего: ни в доках, ни на странице демок. Есть запасной путь — профиль запуска может увести неподходящее устройство в облачный стрим (платный по минутам).

**Решается одним действием:** открыть `https://simplystream.dev/uehati8z` на айфоне и на андроиде. Если Cropout идёт — наша демка тоже пойдёт. Если вкладка умирает — телефоны либо через облачный стрим, либо через свою веб-реализацию.

## Риски зависимости от вендора

1. Движок — их форк. Наш апдейт движка привязан к тому, что они собрали.
2. Сборка — на их машинах. Нет их сервиса — нет демки.
3. Ссылка — на их домене (`simplystream.dev/<slug>`). Про свой домен и про embed в доках **ничего не сказано**. Игра у них лежит в iframe, так что технически вставка на наш сайт выглядит естественно, но гарантий в доках нет.
4. Мы отдаём исходники и контент проекта третьей стороне (их агент шлёт папку проекта целиком).
5. Матрицы поддержки фич нет: Nanite/Lumen/Niagara/Mutable в доках не упомянуты ни разу.

## Что спросить у вендора до старта

1. Можно ли встроить плеер в свой сайт (iframe) и повесить на свой домен?
2. Какие плагины заведомо не собираются? Конкретно Mutable, Mover, GAS, StateTree, CommonUI, MVVM, Niagara (включая GPU-симуляцию).
3. Поддержка телефонов: iOS Safari и Chrome Android — заявлена или нет, какой потолок кучи ставить для мобильного профиля.
4. Куда девается наш контент: хранение, удаление, права.
5. Есть ли лимит на размер проекта в бесплатном тарифе.

## Источники

- [UnrealEngineHTML5/Documentation issue #170 — UE 5.8.3 WebGPU fork](https://github.com/UnrealEngineHTML5/Documentation/issues/170)
- [PooyaEimandar/UnrealEngine-WebGPU](https://github.com/PooyaEimandar/UnrealEngine-WebGPU)
- [SimplyStream](https://simplystream.com/) · [цены](https://simplystream.com/pricing) · [Strata](https://simplystream.com/docs/strata) · [build guides](https://simplystream.com/docs/build-guides) · [troubleshooting](https://simplystream.com/docs/troubleshooting) · [демки](https://simplystream.com/demos)
- [GamesBeat: SimplyStream unlocks web compatibility for UE5](https://gamesbeat.com/simplystream-unlocks-web-compatibility-for-unreal-engine-5-enabling-high-quality-webgpu-gaming-in-the-browser/)
- [Epic forum: Lyra sample running in WebGPU](https://forums.unrealengine.com/t/lyra-sample-running-in-webgpu-demo-below/1932180)
- [Epic docs: Pixel Streaming](https://dev.epicgames.com/documentation/en-us/unreal-engine/pixel-streaming-in-unreal-engine)
- [Manifold: официальная поддержка WebGPU до 2027 (~7%)](https://manifold.markets/j7/will-unreal-engine-gain-official-we)
- [caniuse: WebGPU](https://caniuse.com/webgpu) · [WebGPU в iOS 26](https://appdevelopermagazine.com/webgpu-in-ios-26/)
- [godot#70621 — wasm 2 ГБ падает на iOS Safari](https://github.com/godotengine/godot/issues/70621) · [dotnet/runtime#84638 — MAXIMUM_MEMORY на мобильном Safari](https://github.com/dotnet/runtime/issues/84638) · [WebKit bug 221530 — Safari убивает вкладку вместо ошибки](https://bugs.webkit.org/show_bug.cgi?id=221530)
- [Eagle3D — цены pixel streaming](https://www.eagle3dstreaming.com/?p=4179) · [CoreWeave](https://coreweave.com/solutions/pixel-streaming)
