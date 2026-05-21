# RFP Manager — Design v2

> Детальная проработка фаз. Фиксирует решения по всем архитектурным проблемам, найденным в dry-run аудите DESIGN.md.

---

## Phase 0: Input Setup (Python only, deterministic)

### 0.1 Запуск и входные параметры

```
python3 runner.py run <project_dir> [--interactive | --no-interactive]
```

`<project_dir>` — папка с документами заказчика. Может быть любой путь, в т.ч. отдельный git-репозиторий. Никакого init не требуется — runner создаёт `plan/` и `_artifacts/` сам при первом запуске.

**При старте runner обязан:**
1. Проверить наличие `plan/params.yaml` — если нет, создать с дефолтами и вывести `[INFO] Created plan/params.yaml with defaults. Edit before proceeding.`
2. Проверить доступность `copilot` CLI — если нет в PATH, выдать `[ERROR]` и завершить
3. Проверить наличие хотя бы одного source-файла после сканирования — если нет, выдать `[ERROR]` и завершить

**Дефолтный params.yaml:**
```yaml
industry: unknown
project_type: software
domain_tags: []

models:
  default: claude-sonnet-4-5
  critic: o4-mini
  source_processor: claude-sonnet-4-5
  illustrator: claude-sonnet-4-5

illustration_mode: direct   # direct (~40s/fig) | pipeline (~3-5 min/fig)

trust_policy:
  source_priority:
    - formal_decision
    - explicit_statement
    - transcript
    - chat
    - notes
  auto_resolve: true
  escalate_on: [scope, budget, architecture, security]
```

---

### 0.2 Сканирование проекта

Рекурсивно сканируется `<project_dir>`. Исключаются:
- `plan/`
- `_artifacts/`
- `.git/` и любые папки, начинающиеся с `.`
- файлы, начинающиеся с `.` (dotfiles)

**Правило разбивки файлов/подпапок:**

> Файл принадлежит ровно одному агенту. Если файл лежит в подпапке — он обрабатывается subfolder-агентом, НЕ индивидуальным file-агентом.

```python
def scan_project(project_dir: Path) -> ScanResult:
    EXCLUDED_DIRS = {"plan", "_artifacts", ".git"}
    SUPPORTED_EXT = {".md", ".txt", ".docx", ".xlsx", ".pptx",
                     ".pdf", ".png", ".jpg", ".jpeg", ".webp"}

    root_files: list[Path] = []    # файлы прямо в корне проекта
    subfolders: list[Path] = []    # подпапки первого уровня

    for item in sorted(project_dir.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            if item.name not in EXCLUDED_DIRS:
                subfolders.append(item)
        elif item.is_file():
            if item.suffix.lower() in SUPPORTED_EXT:
                root_files.append(item)

    return ScanResult(root_files=root_files, subfolders=subfolders)
```

**Важно:** файлы внутри `subfolders` НЕ добавляются в `root_files`. Между file-агентами и subfolder-агентами нет дублирования.

**Вложенные подпапки:** subfolder-агент получает ВСЕ файлы подпапки рекурсивно (depth не ограничен, но предупреждение если > 3 уровней).

**Неподдерживаемые форматы** (`.zip`, `.mp4`, `.eml` и т.д.) логируются как `[WARN] Skipped unsupported file: <path>` и не попадают в manifest.

---

### 0.3 Разбор документов (Phase 0 parsing)

Поддерживаемые форматы и их обработка:

| Формат | Инструмент Python | Результат | Особенности |
|---|---|---|---|
| `.docx` | python-docx | `_artifacts/parsed/{slug}.md` + изображения в `_artifacts/parsed/assets/` | Текст + таблицы в markdown; изображения сохраняются в assets |
| `.xlsx` | openpyxl (`data_only=True`) | `_artifacts/parsed/{slug}.json` | **data_only=True** — сохраняются вычисленные значения, не формулы. Один объект: `{"Sheet1": [[headers...], [row...], ...], ...}` |
| `.pptx` | python-pptx | `_artifacts/parsed/{slug}.md` + изображения в `_artifacts/parsed/assets/` | Каждый слайд → секция markdown `## Slide N`. Изображения сохраняются |
| `.pdf` | — | Не парсится в Phase 0 | Агент читает напрямую через mcp_pdf-reader в Phase 1 |
| `.png/.jpg/.jpeg/.webp` | — | Не парсится в Phase 0 | Агент получает путь, использует vision-модель |
| `.md/.txt` | — | Не парсится в Phase 0 | Агент читает напрямую через `read` tool |

**Охранное условие для пустого parsed-файла:**

```python
def parse_docx(path: Path, out_dir: Path) -> ParseResult:
    md_text = convert_docx_to_markdown(path)
    assets = extract_docx_images(path, out_dir / "assets")

    if len(md_text.strip()) < 100 and not assets:
        # Документ без текста и без изображений — возможно, только embedded объекты
        return ParseResult(path=None, empty=True, assets=[], warning="docx appears empty")

    if len(md_text.strip()) < 100 and assets:
        # Документ почти без текста, но есть изображения — агент будет работать только с ними
        return ParseResult(path=write_markdown(md_text, out_dir, slug),
                           empty=False, assets=assets, warning="docx is mostly images")

    return ParseResult(path=write_markdown(md_text, out_dir, slug), empty=False, assets=assets)
```

Если `empty=True` → manifest помечает `"parse_status": "empty"`, агент всё равно создаётся, но получает предупреждение в промпте: *"Parsed text is empty — the source may contain only embedded objects or be a scan."*

**Фильтрация изображений (content-bearing vs decorative):**

Изображения из docx/pptx передаются агенту только если они контентные (не декоративные). Эвристика по двум признакам:

```python
MIN_SIZE_BYTES = 5_000       # < 5KB → иконка/буллет/divider
MIN_DIMENSION_PX = 150       # меньше 150px по любой стороне → декоративное
LOGO_ASPECT_RATIO = (3.0, float("inf"))  # очень широкие баннеры — пропускать

def is_content_image(img_path: Path) -> bool:
    if img_path.stat().st_size < MIN_SIZE_BYTES:
        return False
    with Image.open(img_path) as img:
        w, h = img.size
        if w < MIN_DIMENSION_PX or h < MIN_DIMENSION_PX:
            return False
        ratio = w / h
        if LOGO_ASPECT_RATIO[0] <= ratio:
            return False
    return True
```

Изображения, не прошедшие фильтр, сохраняются в `assets/` (для аудита), но НЕ включаются в список `assets` в manifest-записи агента.

---

### 0.4 Slug-генерация (source names → safe paths)

Имена файлов и подпапок используются как идентификаторы в `_artifacts/extracts/{slug}/`. Slug должен быть безопасен для файловой системы и grep.

```python
import re

def slugify(name: str) -> str:
    # убираем расширение для файлов
    stem = Path(name).stem if "." in name else name
    # заменяем всё не-alphanumeric на подчёркивание
    slug = re.sub(r"[^\w\-]", "_", stem)
    # коллапсируем повторные подчёркивания
    slug = re.sub(r"_+", "_", slug).strip("_").lower()
    return slug or "unnamed"

# Примеры:
# "client-chat (final v2).txt" → "client-chat__final_v2"
# "Onboarding Notes!.md"       → "onboarding_notes"
# "budget Q1 2026.xlsx"        → "budget_q1_2026"
```

**Коллизии:** если два файла дают одинаковый slug (редко, но возможно), добавляется числовой суффикс `_2`, `_3`.

---

### 0.5 Manifest

После сканирования и парсинга Python создаёт `_artifacts/intake/manifest.json`:

```json
{
  "project_dir": "/path/to/project",
  "created_at": "2026-05-04T10:00:00Z",
  "runner_version": "0.1.0",
  "entries": [
    {
      "kind": "file",
      "slug": "architecture_pdf",
      "original": "architecture.pdf",
      "parsed": null,
      "parse_status": "skipped",
      "read_tool": "mcp_pdf-reader",
      "assets": [],
      "agent_scope": "file"
    },
    {
      "kind": "file",
      "slug": "tech_spec",
      "original": "tech-spec.docx",
      "parsed": "_artifacts/parsed/tech_spec.md",
      "parse_status": "ok",
      "read_tool": "read",
      "assets": ["_artifacts/parsed/assets/tech_spec_fig1.png"],
      "agent_scope": "file"
    },
    {
      "kind": "file",
      "slug": "budget_q1_2026",
      "original": "budget Q1 2026.xlsx",
      "parsed": "_artifacts/parsed/budget_q1_2026.json",
      "parse_status": "ok",
      "read_tool": "read",
      "assets": [],
      "agent_scope": "file"
    },
    {
      "kind": "file",
      "slug": "kickoff_transcript",
      "original": "kickoff-transcript.md",
      "parsed": null,
      "parse_status": "skipped",
      "read_tool": "read",
      "assets": [],
      "agent_scope": "file"
    },
    {
      "kind": "subfolder",
      "slug": "onboarding",
      "original": "onboarding/",
      "parsed": null,
      "parse_status": "mixed",
      "read_tool": "mixed",
      "files": [
        {
          "original": "onboarding/flow-diagram.png",
          "read_tool": "vision",
          "assets": []
        },
        {
          "original": "onboarding/onboarding-notes.md",
          "parsed": null,
          "read_tool": "read",
          "assets": []
        }
      ],
      "agent_scope": "subfolder"
    }
  ]
}
```

**Поля:**
- `kind` — `"file"` или `"subfolder"`
- `slug` — уникальный безопасный идентификатор
- `original` — путь относительно `project_dir`
- `parsed` — путь к результату Phase 0 парсинга, или `null`
- `parse_status` — `"ok"` / `"empty"` / `"skipped"` / `"error"` / `"mixed"` (для subfolder)
- `read_tool` — подсказка агенту: `"read"` / `"mcp_pdf-reader"` / `"vision"` / `"mixed"`
- `assets` — контентные изображения, прошедшие фильтр
- `agent_scope` — `"file"` или `"subfolder"` — определяет тип агента

---

## Phase 1: Source Extraction (parallel agents)

### 1.1 Агентный пул

По окончании Phase 0 Python строит список задач для Phase 1:

```python
tasks = []

for entry in manifest["entries"]:
    task = {
        "agent": "source_processor",
        "slug": entry["slug"],
        "manifest_entry": entry,
        "model": params["models"]["source_processor"],
    }
    tasks.append(task)
```

Каждая запись manifest → один агент. Нет дублирования (subfolder-записи уже отделены от file-записей при сканировании).

---

### 1.2 Вызов агента — `run_agent`

```python
from dataclasses import dataclass
from pathlib import Path
import subprocess, json, re, logging

AGENT_TIMEOUT_S = 300  # 5 минут на один агент
REPO_ROOT = Path(__file__).parent  # директория runner.py = корень rfp-manager

@dataclass
class AgentResult:
    slug: str
    success: bool
    raw_text: str        # полный вывод агента
    parsed_json: dict    # разобранный extract.json, или {}
    error: str = ""

def run_agent(agent_name: str, prompt_file: Path, slug: str,
              model: str = None, project_dir: Path = None) -> AgentResult:

    cmd = [
        "copilot",
        "-p", f"Read your task from: {prompt_file}",
        "--agent", agent_name,
        "--output-format", "json",
        "--allow-all",
        "--no-ask-user",
        "--add-dir", str(REPO_ROOT),       # промпты, exemplars, agent instructions
    ]
    if project_dir:
        cmd += ["--add-dir", str(project_dir)]   # проектные файлы
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return AgentResult(slug=slug, success=False, raw_text="",
                           parsed_json={}, error="timeout")

    if result.returncode != 0:
        err = result.stderr.strip() or f"exit code {result.returncode}"
        logging.error(f"[{slug}] agent failed: {err}")
        return AgentResult(slug=slug, success=False, raw_text=result.stdout,
                           parsed_json={}, error=err)

    raw = extract_assistant_text(result.stdout)  # парсим JSONL
    parsed = parse_json_from_agent_text(raw)
    return AgentResult(slug=slug, success=bool(parsed),
                       raw_text=raw, parsed_json=parsed,
                       error="" if parsed else "no valid JSON in response")
```

**Почему `-p "Read your task from: {prompt_file}"`, а не сам контент:**
- Промпт с полным содержимым docx 200 страниц → `ARG_MAX` (~2MB на macOS) риск при нескольких параллельных агентах
- Python пишет рендеренный промпт в `_artifacts/prompts/{slug}.md` до запуска агента
- Агент читает файл задания через свой `read` tool — первый вызов агента

**Два `--add-dir`:**
1. `REPO_ROOT` — агент видит `prompts/`, `.github/agents/`, `exemplars/`
2. `project_dir` — агент видит все исходные документы проекта

---

### 1.3 Параллельное выполнение с partial recovery

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_agents_parallel(tasks: list[dict],
                        project_dir: Path) -> list[AgentResult]:
    results: list[AgentResult] = []
    failed: list[dict] = []

    with ProcessPoolExecutor() as pool:
        future_to_task = {
            pool.submit(
                run_agent,
                t["agent"],
                t["prompt_file"],
                t["slug"],
                model=t.get("model"),
                project_dir=project_dir,
            ): t
            for t in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                if not result.success:
                    failed.append(task)
            except Exception as e:
                # исключение из самого future (редко — только если run_agent упал неожиданно)
                slug = task["slug"]
                logging.error(f"[{slug}] unexpected exception: {e}")
                results.append(AgentResult(slug=slug, success=False,
                                           raw_text="", parsed_json={},
                                           error=str(e)))
                failed.append(task)

    if failed:
        slugs = [t["slug"] for t in failed]
        print(f"[WARN] {len(failed)} agent(s) failed: {slugs}")

    return results
```

**Гарантия:** если 1 из 6 агентов упал — остальные 5 результатов сохраняются. Pipeline продолжается с частичными данными; упавшие источники отмечаются в manifest как `extract_status: "failed"`.

---

### 1.4 Промпт-файл для Source Processor

Python рендерит промпт и пишет в `_artifacts/prompts/{slug}.md` **до** запуска пула.

Шаблон `prompts/source_processor/extract.md` (переменные `{{...}}` заменяются):

```markdown
## Your Task

You are processing one source document as part of a requirements extraction pipeline.

**Source entry from manifest:**
```json
{{manifest_entry_json}}
```

**Reading instructions:**
- read_tool: `{{read_tool}}`
{{#if assets}}
- This document also has **{{asset_count}} associated image(s)**. Read each one listed in `assets` using your vision capability and include visual content in your extraction.
{{/if}}
{{#if parse_status_empty}}
- ⚠️ The parsed text is empty. The source may contain only embedded objects or be a scan. Focus on any assets provided.
{{/if}}
{{#if clarification_answer}}
- **User clarification provided:** {{clarification_answer}}
{{/if}}

**Output format:**
Write your result as a JSON code block (```json ... ```) — Python will parse it.
See the schema in `prompts/source_processor/output_schema.md`.

**Strategy selection:**
Read the first ~50 lines of the document to determine content type, then load the appropriate strategy from `prompts/source_processor/strategies/`.
{{auto_hints}}
{{exemplar_ref}}
```

> Шаблон использует `{{...}}` замену. Условные блоки `{{#if}}` — простой if-else в `render_prompt`, не logic в промпте.

**Переменные `render_prompt` для Source Processor:**

```python
variables = {
    "manifest_entry_json": json.dumps(entry, indent=2),
    "read_tool": entry["read_tool"],
    "assets": entry["assets"],
    "asset_count": len(entry["assets"]),
    "parse_status_empty": entry.get("parse_status") == "empty",
    "clarification_answer": clarification.get(entry["slug"], ""),
    "auto_hints": load_auto_hints(),   # из _auto/ если есть
    "exemplar_ref": load_exemplar_ref(params),
}
```

Незаменённые переменные (нет значения) → заменяются на `""`. Логируется `[DEBUG] Template var '{{x}}' was empty for slug=...`.

---

### 1.5 Инструменты агента Source Processor

В `.github/agents/source_processor.agent.md`:

```yaml
tools:
  - read           # читать файлы (текст + изображения через vision модель)
  - mcp_pdf-reader # читать PDF: read_pdf, smart_extract_pdf, ocr_pdf
```

**Vision для изображений:** когда агент вызывает `read` на `.png`/`.jpg`/`.webp`, copilot CLI передаёт файл как vision-input к модели. Это стандартное поведение CLI — не нужен отдельный "vision tool". Агент просто вызывает `read` на путь к изображению.

**mcp_pdf-reader:** должен быть сконфигурирован в copilot CLI окружении. Pre-flight проверка при старте runner:

```python
def check_mcp_pdf_reader() -> bool:
    """Проверяем доступность mcp_pdf-reader запуском минимального агента."""
    # Простой heuristic: проверяем что в конфиге CLI есть mcp_pdf-reader
    config_paths = [
        Path.home() / ".config" / "copilot" / "mcp.json",
        Path.home() / ".copilot" / "mcp.json",
    ]
    for p in config_paths:
        if p.exists():
            cfg = json.loads(p.read_text())
            if "mcp_pdf-reader" in cfg.get("servers", {}):
                return True
    return False  # если не найдено — предупреждение, но не блокировка

# При старте:
if not check_mcp_pdf_reader() and any_pdf_in_manifest(manifest):
    print("[WARN] mcp_pdf-reader not found in CLI config. PDF files may fail in Phase 1.")
    print("[WARN] Configure it at: ~/.config/copilot/mcp.json")
```

---

### 1.6 Парсинг ответа агента → extract.json

Агент возвращает текст с JSON-блоком внутри. Python:

```python
import json, re

def parse_json_from_agent_text(text: str) -> dict:
    # 1. Ищем ```json ... ``` блок
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        candidate = m.group(1)
    else:
        # 2. Fallback: ищем первый { ... } на верхнем уровне
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            candidate = m.group(1)
        else:
            return {}

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logging.warning(f"JSON parse error: {e}")
        return {}
```

После парсинга Python пишет результат:

```python
def save_extract(result: AgentResult, artifacts_dir: Path):
    extract_dir = artifacts_dir / "extracts" / result.slug
    extract_dir.mkdir(parents=True, exist_ok=True)

    if result.success and result.parsed_json:
        (extract_dir / "extract.json").write_text(
            json.dumps(result.parsed_json, ensure_ascii=False, indent=2)
        )
        (extract_dir / "raw.txt").write_text(result.raw_text)  # для отладки
    else:
        # Пишем маркер ошибки — Phase 2 знает, что этот источник неполный
        (extract_dir / "extract.json").write_text(
            json.dumps({"error": result.error, "source_file": result.slug,
                        "partial_raw": result.raw_text[:2000]})
        )
```

---

### 1.7 Схема extract.json

Все поля опциональны, кроме `source_file` и `source_type`. Агент включает только то, что есть в документе.

```json
{
  "source_file": "kickoff-transcript.md",
  "source_type": "transcript",
  "source_type_confidence": "high",
  "date": "2026-03-15",
  "participants": ["Ahmad Al-Rashid (CTO)", "Sara Chen (PM)"],
  "topics": ["custody workflow", "T+1 settlement", "SWIFT integration"],

  "requirements": [
    {
      "id": "SRC-KT-001",
      "text": "System must support T+1 settlement for equity trades",
      "type": "FR",
      "confidence": "high",
      "speaker": "Ahmad Al-Rashid (CTO)",
      "quote": "We absolutely need T+1 by Q3, the regulator is watching"
    }
  ],

  "decisions": [
    "On-premise deployment chosen over cloud (security constraints)"
  ],

  "constraints": [
    "Must integrate with existing SWIFT MT515 gateway (no replacement)"
  ],

  "open_questions": [
    "Custody fee structure not discussed — needs follow-up with Finance"
  ],

  "potential_conflicts": [
    "Ahmad says T+1 settlement; tech-spec.docx says T+2 — sources contradict"
  ],

  "trust_level": "transcript",

  "needs_clarification": false,
  "clarification_request": ""
}
```

**Поле `trust_level`** — агент классифицирует сам источник, не отдельные требования. Возможные значения: `formal_decision`, `explicit_statement`, `transcript`, `chat`, `notes`. Python использует это для conflict resolution в Phase 2.

**Поле `needs_clarification`** — `true` если агент не смог извлечь критичный контекст:
- анонимные участники в транскрипте
- документ без даты и контекста
- противоречивые данные внутри одного документа
- файл пустой или нечитаемый

Поле `clarification_request` — описание что именно неизвестно: *"Participant 'the product team' is unnamed — who are they?"*

---

### 1.8 Стратегии извлечения

Агент сам определяет тип контента по первым 50 строкам/первому экрану. Стратегии в `prompts/source_processor/strategies/`:

| Тип | Сигналы | Стратегия |
|---|---|---|
| `transcript` | Обороты Q&A, метки спикеров (`Ahmad:`, `[00:05:12]`), временны́е метки | `strategies/transcript.md` |
| `chat` | Короткие сообщения, @-упоминания, временны́е метки в формате мессенджера | `strategies/chat.md` |
| `brief` | Прозаические параграфы, заголовки секций, нет меток спикеров | `strategies/brief.md` |
| `qa` | Нумерованные вопросы + письменные ответы | `strategies/qa.md` |
| `pdf` | Формат источника — PDF (независимо от содержимого) | `strategies/pdf.md` |
| `spreadsheet` | Формат `.xlsx` / JSON из openpyxl | `strategies/spreadsheet.md` |

**PDF sub-type:** `strategies/pdf.md` включает инструкцию: *после чтения первой страницы определить подтип (brief / spec / transcript / chart) и применить соответствующий угол анализа*. Отдельный файл стратегии для PDF не нужен — он является оберткой над другими.

**Гибридные документы:** агент может применить две стратегии одновременно (например, PDF с транскриптом). В `source_type` пишет `"transcript+pdf"`.

**Неоднозначность:** если не удалось определить → `brief.md` + `source_type_confidence: "low"` в extract.json.

---

### 1.9 HITL:clarify — пакетный раунд после пула

После завершения всего пула Python собирает агенты с `needs_clarification: true`:

```python
def collect_clarification_flags(results: list[AgentResult]) -> list[ClarifyRequest]:
    flagged = []
    for r in results:
        if r.parsed_json.get("needs_clarification"):
            flagged.append(ClarifyRequest(
                slug=r.slug,
                source_file=r.parsed_json.get("source_file"),
                question=r.parsed_json.get("clarification_request", "No details provided"),
            ))
    return flagged
```

Если `flagged` не пустой → вывести одним блоком:

```
[HITL:clarify]
{
  "requests": [
    {"slug": "kickoff_transcript", "source": "kickoff-transcript.md",
     "question": "Participant 'the product team' is unnamed — who are they?"},
    {"slug": "budget_q1_2026", "source": "budget Q1 2026.xlsx",
     "question": "Column 'Reserve' meaning unclear — is this contingency or earmarked funds?"}
  ]
}
```

Orchestrator собирает ответы пользователя и возвращает:
```json
{"action": "clarify", "answers": {"kickoff_transcript": "Ahmad's team: Ahmad (CTO), Sara (PM), Yusuf (Arch)", "budget_q1_2026": "Reserve is contingency, ~15% buffer"}}
```

**Повторный запуск помеченных агентов:**

```python
if answers:
    retry_tasks = [build_task(slug, clarification=answers[slug])
                   for slug in answers]
    retry_results = run_agents_parallel(retry_tasks, project_dir)
    # replace old results with new ones
    results = merge_results(results, retry_results)
```

**Множественные раунды:** после re-run снова проверяем `needs_clarification`. Если опять `true` — второй `[HITL:clarify]`. Максимум **2 раунда** (3-й игнорируется, агент продолжает с тем что есть, `clarification_request` записывается в `open_questions`).

**Headless режим (`--no-interactive`):** если flagged не пустой и режим headless → пропустить clarify, продолжить с partial extracts. Записать в state.json: `"skipped_clarifications": [...]`.

---

### 1.10 Итоговое состояние после Phase 1

```
_artifacts/
  intake/
    manifest.json          ← обновлён: поле extract_status у каждой записи
  parsed/
    tech_spec.md
    budget_q1_2026.json
    assets/
      tech_spec_fig1.png
  extracts/
    kickoff_transcript/
      extract.json         ← успешно разобран
      raw.txt
    architecture_pdf/
      extract.json         ← успешно разобран (через mcp_pdf-reader)
      raw.txt
    budget_q1_2026/
      extract.json         ← успешно разобран
      raw.txt
    onboarding/
      extract.json         ← unified extract для всей подпапки
      raw.txt
  prompts/
    kickoff_transcript.md  ← рендеренный промпт (для отладки)
    architecture_pdf.md
    ...
```

`manifest.json` после Phase 1 обновляется полем `extract_status` для каждой записи:

```json
{
  "slug": "kickoff_transcript",
  "extract_status": "ok",          // "ok" | "failed" | "partial" | "needs_clarification"
  "extract_path": "_artifacts/extracts/kickoff_transcript/extract.json"
}
```

Phase 2 (Analyst) работает только с записями `extract_status: "ok"` или `"partial"`. Записи `"failed"` логируются в `[WARN]` и упоминаются в Analyst-промпте: *"The following sources could not be extracted and are excluded: ..."*

---

## Открытые вопросы (требуют решения до имплементации)

1. **Retry для упавших агентов:** делать ли автоматический retry (1x) для `failed` результатов до перехода к Phase 2? Или только через `[ERROR]` HITL?
2. **Размер пула:** `ProcessPoolExecutor()` без `max_workers` = `os.cpu_count()`. Для 10 файлов на 4-ядерной машине — 4 параллельных агента, остальные в очереди. Нужен ли явный `max_workers`?
3. **Copilot CLI `--add-dir` семантика:** добавляет ли `--add-dir` директорию в контекст агента как "рабочая директория" или только как доступные файлы? Влияет на то, как агент вызывает `read` с относительными путями.
