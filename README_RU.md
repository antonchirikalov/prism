# prism

**prism** берёт папку с сырыми клиентскими документами — RFP, предложениями, заметками с встреч, PDF, таблицами — и превращает их в готовые технические артефакты: структурированную спецификацию требований, подборку вопросов для архитектора и полноценное предложение по архитектурному решению. Закидываете файлы, запускаете конвейер, получаете документы.

Внутри это мультиагентная AI-система. Агенты GitHub Copilot CLI читают и пишут документы; Python-раннеры занимаются оркестрацией — порядком фаз, параллелизмом, восстановлением после сбоев и логикой повторных попыток. Каждая передача данных между фазами — это файл на диске, поэтому любой шаг можно возобновить после сбоя без повторного выполнения уже завершённых этапов.

Три конвейера, одна входная папка:

| Конвейер | Раннер | Вход | Выход | Когда использовать |
|---|---|---|---|---|
| **Extract** | `runner.py` | Документы в `input/` | `_requirements.md` | Структурированная спецификация FR/NFR/BR из неструктурированных источников |
| **Discovery** | `runner.py --mode discovery` | Документы в `input/` | `discovery_report.md` | Подборка вопросов архитектора перед воркшопом |
| **Solution Design** | `solution_design_runner.py` | `_requirements.md` | `_solution_design.md` | Полноценное технической предложение по архитектуре |

---

## Конвейеры

<!-- ILLUSTRATION: type=pipeline -->

![Рис. 1 — Три конвейера: Extract, Discovery, Solution Design](docs/illustrations/pipeline.png)

*Рис. 1. Три конвейера — Extract, Discovery и Solution Design — управляются Python-раннерами. Extract и Discovery разделяют фазу 0 и фазу 1 (параллельная обработка источников). Solution Design принимает готовый документ требований и создаёт фиксированное архитектурное предложение.*

Два режима, один входной набор данных:

| Режим | Флаг | Что создаёт | Когда использовать |
|---|---|---|---|
| `extract` | `--mode extract` (по умолчанию) | `_requirements.md` — FR / NFR / BR / конфликты / пробелы | Когда нужна структурированная спецификация из сырых документов |
| `discovery` | `--mode discovery` | `discovery_report.md` — отобранные вопросы по пробелам, оценка AI-генерации | Перед воркшопом; когда нужно понять, чего не хватает |

---

## Быстрый старт

```bash
# Клонировать и настроить
git clone <repo>
cd prism
python3 -m venv .venv && .venv/bin/pip install loguru pyyaml

# Настроить окружение
cp .env.example .env   # добавить OPENAI_API_KEY (для агента Illustrator)

# Запустить извлечение требований (режим по умолчанию)
python3 runner.py run /path/to/project/input

# Запустить discovery
python3 runner.py run /path/to/project/input --mode discovery

# Запустить solution design (после extraction)
.venv/bin/python3 solution_design_runner.py run \
  /path/to/project/requirements_YYYYMMDD_HHMMSS/_requirements.md \
  --models claude-sonnet-4.6 gpt-5.5

# Возобновить прерванный solution design
.venv/bin/python3 solution_design_runner.py resume \
  /path/to/project/solution_design_YYYYMMDD_HHMMSS

# Интерактивный режим (HITL-паузы на контрольных точках)
python3 runner.py run /path/to/project/input --interactive

# Подробное логирование
python3 runner.py run /path/to/project/input --debug
```

### Флаги `runner.py`

| Флаг | По умолчанию | Описание |
|---|---|---|
| `--mode` | `extract` | `extract` или `discovery` |
| `--interactive` | выкл | Пауза на HITL-контрольных точках для уточнений |
| `--no-interactive` | — | Явно пропустить все HITL-паузы (фоновый режим) |
| `--debug` | выкл | DEBUG-логирование в stderr |

### Флаги `solution_design_runner.py`

| Подкоманда | Аргумент | По умолчанию | Описание |
|---|---|---|---|
| `run` | `requirements_path` | — | Путь к `_requirements.md` |
| `run` | `--models MODEL [...]` | `claude-sonnet-4.6 gpt-5.5` | Модели для параллельной фазы 1 |
| `run` | `--verbose` / `-v` | выкл | DEBUG-логирование в stderr |
| `resume` | `output_dir` | — | Папка с `state.json` |
| `resume` | `--verbose` / `-v` | выкл | DEBUG-логирование в stderr |

---

## Входные данные: что кладём в `input/`

Любое сочетание:

- `.pdf` — RFP-документы, предложения, спецификации (читаются через `mcp_pdf-reader`)
- `.docx` / `.pptx` / `.xlsx` — офисные документы
- `.md` / `.txt` — заметки с встреч, брифы, экспорты чатов
- `.png` / `.jpg` / `.jpeg` / `.webp` — скриншоты, архитектурные схемы (читаются через vision)
- Подпапки — обрабатываются как единый логический источник (один агент на папку)
- `.txt`-файлы с URL — страницы Confluence получаются через MCP; обычные URL скачиваются напрямую

**Исключаются автоматически:** `plan/`, `.git/`, любая папка, начинающаяся с `_artifacts`.

---

## Структура вывода

Каждый запуск создаёт **самодостаточную папку с временной меткой**, соседнюю с `input/`:

```
project/
  input/                              ← ваши исходные документы (не изменяются)
  requirements_20260521_152709/       ← или discovery_20260521_...
    _requirements.md                  ← итоговый артефакт
    plan/
      params.yaml                     ← параметры запуска (можно редактировать перед повтором)
    _artifacts_20260521_152709/
      runner.log
      intake/
        manifest.json                 ← все обнаруженные записи со статусом обработки
      extracts/
        <slug>/
          extract.json                ← структурированный вывод на каждый источник
          raw.txt                     ← сырой ответ агента
          agent.jsonl                 ← полный лог Copilot CLI в JSONL
        _requirements_writer/
          agent.jsonl
        _requirements_critic_r1/
          verdict.md                  ← VERDICT: APPROVED / REVISE
          agent.jsonl
      prompts/
        <slug>.md                     ← задача-промпт для каждого агента
        _requirements_writer.md
        _requirements_critic_r1.md
```

---

## Детали конвейеров

### Режим Extract — 4 фазы

```
Фаза 0 → Фаза 1 (параллельно) → Фаза 2 → Фаза 3 (цикл)
  скан    source_processor       writer     critic ↔ writer
```

#### Фаза 0 — Сканирование + Манифест

`runner.py` обходит `input/`, классифицирует каждый элемент, строит `manifest.json`:

| Тип записи | Что это | Инструмент чтения |
|---|---|---|
| `file` | Одиночный `.pdf`, `.docx`, `.md`, изображение и т.д. | `mcp_pdf-reader` / `vision` / `read` |
| `subfolder` | Папка со связанными файлами | `mixed` / `read` |
| `url` | URL из `.txt`-файла | `mcp_confluence` или `fetch` |

#### Фаза 1 — Параллельное извлечение из источников

Один агент `source_processor` на каждую запись манифеста, все запускаются одновременно через `ThreadPoolExecutor`. Каждый агент:

- определяет тип документа (транскрипт / чат / бриф / PDF / таблица / Q&A)
- применяет соответствующую стратегию извлечения
- выдаёт `extract.json` с полями: `requirements`, `decisions`, `constraints`, `open_questions`, `trust_level`

Таймаут агента: **20 минут** на агент. Heartbeat выводится каждые 10 секунд.

**HITL:clarify (при `--interactive`).** Если агент возвращает `needs_clarification: true`, раннер делает паузу и запрашивает уточнение у пользователя в терминале. До **2 раундов** уточнений.

#### Фаза 2 — Автор требований

`requirements_writer` читает все успешные `extract.json` и синтезирует `_requirements.md`:

- Функциональные требования (FR-001, FR-002, …)
- Нефункциональные требования (NFR-001, …)
- Бизнес-требования (BR-001, …)
- Реестр конфликтов — противоречия между источниками
- Реестр пробелов — без ответа вопросы
- Допущения

#### Фаза 3 — Цикл Критик ↔ Автор

`requirements_critic` читает `_requirements.md`, проверяет по исходным экстрактам, пишет вердикт:

```
VERDICT: APPROVED          ← цикл заканчивается, документ финальный
VERDICT: REVISE
- Раздел 2.1: не хватает NFR для ...
- Конфликт FR-004 и FR-017 не разрешён
```

При `REVISE` — вердикт добавляется в следующий промпт автора и `requirements_writer` делает правку. Повторяется до **`APPROVED`** или **лимита 5 раундов** (`MAX_CRITIC_ROUNDS`). Достижение лимита — предупреждение, не ошибка.

---

### Режим Discovery — 4 фазы

```
Фаза 0 → Фаза 1 (параллельно) → Фаза D1 → Фаза D2
  скан    source_processor         probe     critic
```

Фазы 0 и 1 идентичны режиму Extract.

#### Фаза D1 — arch_probe

Читает все `extract.json` и:

- оценивает каждый источник на признаки AI-генерации
- запускает веб-поиск Tavily для контекста по предметной области
- генерирует **20–30 черновых вопросов** — каждый привязан к конкретному пробелу или противоречию
- записывает структурированный JSON в `_arch_probe/probe_output.json`

#### Фаза D2 — arch_critic

Читает `probe_output.json` и:

- отбраковывает общие или легко отвечаемые вопросы
- отбирает **8–15 вопросов**, без ответа на которые невозможно принять архитектурное решение
- пишет `discovery_report.md` напрямую в папку вывода

---

### Конвейер Solution Design — `solution_design_runner.py`

Принимает готовый `_requirements.md` и создаёт `_solution_design.md` — единственное фиксированное архитектурное решение: карта стейкхолдеров, план поставки по фазам, детальные сценарии, NFR, инфраструктурный справочник. Никакого меню вариантов, никаких оценок трудозатрат.

```
Фаза 1 (параллельно) → Фаза 2    → Фаза 3 (цикл)       → Фаза 4
  N × solution_designer  selector   critic ↔ designer     summary
```

#### Фаза 1 — Параллельная генерация

Один агент `solution_designer` на каждую модель, все запускаются одновременно. Каждый агент:

- читает документ требований и запускает веб-поиск Tavily
- создаёт `_design_<model_slug>.md` — полное решение в одной фиксированной архитектуре

Модели по умолчанию: `claude-sonnet-4.6`, `gpt-5.5`. Переопределяется через `--models`.

#### Фаза 2 — Выбор

Если успешно завершил только один кандидат: копируется как `_solution_design.md`.

Если несколько: `solution_design_selector` выбирает сильнейшего, пишет `_selection_report.md` с `WINNING_MODEL: <model>`.

#### Фаза 3 — Цикл Критик

`solution_design_critic` проверяет `_solution_design.md` и пишет вердикт. При `REVISE` — блок замечаний добавляется в промпт правки, `solution_designer` делает ревизию. До **лимита 3 раундов** (`MAX_CRITIC_ROUNDS`).

#### Фаза 4 — Сводка

Выводит пути ко всем артефактам, выигравшую модель, финальный вердикт критика и количество плейсхолдеров `<!-- ILLUSTRATION: -->` для агента Illustrator.

#### Структура вывода — Solution Design

```
project/
  requirements_20260521_152709/       ← вход (не изменяется)
    _requirements.md
  solution_design_20260601_152115/    ← соседняя папка
    _solution_design.md               ← финальный артефакт
    _design_claude-sonnet-4_6.md      ← кандидат фазы 1 (claude)
    _design_gpt-5_5.md                ← кандидат фазы 1 (gpt)
    _selection_report.md              ← отчёт выбора (WINNING_MODEL: ...)
    _verdict_round1.md                ← вердикты критика
    _design_revised_r1.md             ← правка (если REVISE)
    state.json                        ← отказоустойчивый журнал состояния
    prompts/
    logs/
```

#### Восстановление после сбоя

`state.json` записывается атомарно после каждого шага (`tmp → os.replace`). Любой шаг со статусом `running` при запуске сбрасывается в `pending`. Возобновление — командой `resume`: уже завершённые шаги пропускаются, упавшие — повторяются.

---

## Архитектура

<!-- ILLUSTRATION: type=architecture -->

![Рис. 2 — Python-раннеры, группы агентов и дисковые артефакты](docs/illustrations/agents.png)

*Рис. 2. Python-раннеры — это мозг: детерминированный порядок фаз, параллелизм через ThreadPoolExecutor, отказоустойчивый журнал. Агенты — это stateless-воркеры Copilot CLI. Файлы на диске — протокол между фазами.*

### Три принципа

**Python = мозг.** Весь порядок фаз, ветвления, лимиты повторений и параллелизм живут в `runner.py`. Агенты не содержат оркестрационной логики.

**Агенты = stateless-воркеры.** Каждый агент — это `.agent.md`-файл в `.github/agents/`. Запускается как subprocess `copilot` CLI — читает промпт задачи с диска, пишет вывод на диск, завершается.

**Файлы = протокол.** Каждая передача между фазами — файл на диске. `runner.py` валидирует каждый файл перед переходом к следующей фазе.

---

## Агенты

Все 12 агентов живут в `.github/agents/`. Каждый — `.agent.md`-файл с YAML frontmatter (`name`, `description`, `model`, `tools`).

| Агент | Конвейер | Роль | Вход | Выход |
|---|---|---|---|---|
| `source_processor` | Extract / Discovery | Читает один источник (файл, папка, URL), определяет тип, извлекает данные | Любой файл/папка/URL из `input/` | `extract.json` |
| `arch_probe` | Discovery | Оценивает AI-генерацию, веб-поиск по домену, генерирует черновые вопросы | Все `extract.json` | `probe_output.json` (20–30 вопросов) |
| `arch_critic` | Discovery | Фильтрует вопросы, отбирает блокирующие архитектуру | `probe_output.json` | `discovery_report.md` (8–15 вопросов) |
| `requirements_writer` | Extract | Синтезирует экстракты в структурированный документ требований | Все `extract.json` + опциональный вердикт | `_requirements.md` |
| `requirements_critic` | Extract | Проверяет документ требований по источникам, пишет APPROVED/REVISE | `_requirements.md` + экстракты | `verdict.md` |
| `solution_designer` | Solution Design | Создаёт архитектурное предложение: стейкхолдеры, план по фазам, NFR, инфраструктура | `_requirements.md` | `_design_<model>.md` |
| `solution_design_selector` | Solution Design | Сравнивает N кандидатов, выбирает сильнейшего | N `_design_*.md` | `_solution_design.md` + `_selection_report.md` |
| `solution_design_critic` | Solution Design | Проверяет дизайн по требованиям, пишет APPROVED/REVISE | `_solution_design.md` | `_verdict_roundN.md` |
| `orchestrator` | Интерактивная обёртка | Агент VS Code chat; запускает `runner.py`, выводит HITL-точки, передаёт ответы пользователя | Ввод в чате | Команды терминала + `vscode_askQuestions` |
| `Illustrator` | Standalone | Генерирует PNG-иллюстрации через PaperBanana (Retriever → Planner → Stylist → Visualizer ↔ Critic) | Плейсхолдеры `<!-- ILLUSTRATION: -->` в Markdown | PNG-файлы + подписи |
| `Confluence Publisher` | Standalone | Публикует документ в Confluence — конвертирует в XHTML, создаёт/обновляет страницу, загружает PNG | `_requirements.md` или `_solution_design.md` + иллюстрации | Страница Confluence |
| `word_form_builder` | Standalone | Генерирует интерактивную форму Word `.docx` — SDT-чекбоксы, выпадающие списки, предзаполненные таблицы | `_requirements.md` + экстракты | `clarification_form_rN.docx` |

### Вызов агентов

```bash
copilot \
  -p "Read your task from: /path/to/prompt.txt" \
  --agent <agent_name> \
  --output-format json \
  --allow-all \
  --no-ask-user \
  --add-dir /path/to/prism \
  --add-dir /path/to/extra/dir \
  --model <model>
```

---

## Опциональные standalone-агенты

Эти агенты **не входят ни в один автоматизированный конвейер** — вызываются вручную после запуска конвейера.

### `Confluence Publisher`

```bash
export CONFLUENCE_URL="https://your-confluence.example.com"
export CONFLUENCE_PERSONAL_TOKEN="<your-PAT>"

.venv/bin/python .github/skills/confluence-publisher/scripts/publish_to_confluence.py \
  --draft path/to/_requirements.md \
  --illustrations path/to/illustrations/ \
  --parent-id <parent-page-id> \
  --space <SPACE_KEY>
```

### `word_form_builder`

Обычно вызывается после конвейера Extract, перед клиентским воркшопом.

**Вход:** `_requirements.md` + папка с экстрактами  
**Выход:** `clarification_form_r<N>.docx`

---

## Интерактивный режим (HITL)

Запускается через агента `@orchestrator` в чате VS Code:

```
@orchestrator analyze /path/to/project/input
```

| Контрольная точка | Фаза | Что происходит |
|---|---|---|
| Source clarification | Фаза 1 | Агент поднял `needs_clarification` — пользователь даёт контекст, агент перезапускается |
| Conflicts | Фаза 2 | Пользователь выбирает победителя среди противоречащих источников |
| Final review | Фаза 3 | Пользователь может принять APPROVED-вердикт или принудить к ещё одной правке |

Фоновый режим (по умолчанию):

```bash
python3 runner.py run /path/to/input           # --no-interactive по умолчанию
python3 runner.py run /path/to/input --debug   # подробные логи в stderr
```

---

## Конфигурация

`plan/params.yaml` создаётся при первом запуске со значениями по умолчанию. Редактируйте перед повторным запуском:

```yaml
industry: fintech
project_type: software
domain_tags: [payments, SWIFT, KYC]

models: {}   # переопределить модель для отдельных агентов при необходимости

trust_policy:
  auto_resolve: true
  escalate_on: [scope, budget, architecture, security]
```

---

## Необходимые MCP-серверы

MCP-серверы настраиваются в VS Code (`mcp.json`) и используются агентами как инструменты Copilot.

| MCP-сервер | Используется | Когда нужен |
|---|---|---|
| `pdf-reader` | `source_processor` | Любые PDF в `input/` |
| `tavily-remote` | `arch_probe`, `requirements_writer`, `solution_designer` | Всегда — веб-поиск для обогащения контекстом |
| `mcp-atlassian` (Confluence) | `source_processor` | `.txt`-файлы с URL Confluence |

`.env` (нужен только для агента Illustrator):

```
OPENAI_API_KEY=sk-...
```

---

## Структура проекта

```
prism/
  runner.py                          ← оркестратор Extract / Discovery
  solution_design_runner.py          ← оркестратор Solution Design
  requirements_runner.py             ← алиас / точка входа (то же, что runner.py)
  .env                               ← секреты (в .gitignore)
  .venv/                             ← виртуальное окружение Python
  .github/
    agents/
      source_processor.agent.md
      arch_probe.agent.md
      arch_critic.agent.md
      requirements_writer.agent.md
      requirements_critic.agent.md
      solution_designer.agent.md
      solution_design_selector.agent.md
      solution_design_critic.agent.md
      orchestrator.agent.md
      Illustrator.agent.md
      Confluence Publisher.agent.md
      word_form_builder.agent.md
    instructions/
      illustrator/
      shared/
    skills/
      requirements-template/
      solution-design-template/
      word-form-builder/
  prompts/
    source_processor/
    requirements_writer/
    arch_critic/
  docs/
    illustrations/
      pipeline.png          ← Рис. 1
      agents.png            ← Рис. 2
```

---

## Зависимости

```bash
pip install loguru pyyaml                          # runner.py + solution_design_runner.py
pip install "paperbanana[openai]" python-dotenv   # только для агента Illustrator
```

Требуется `copilot` CLI (GitHub Copilot CLI) в `PATH`.
