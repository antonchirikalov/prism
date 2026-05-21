# Jadwa Investment — Требования к системе
> Составлено: 1 апреля 2026 | Источники: звонок 26.03.2026 (Hamza Farooq) + письмо Хамзы в Teams-чате
> Обозначения: ✅ подтверждено дословно | ⚠️ интерпретация | ❓ требует уточнения

---

## 1. Контекст и заказчик

| Параметр | Значение |
|----------|----------|
| Компания | Jadwa Investment, Riyadh, Saudi Arabia |
| AUM | SAR 75B+ (~$20B) |
| Бизнес-спонсор | Fadi Idris, Director & Head of IT |
| Технический владелец | Hamza Farooq, Head of IT |
| Дедлайн ответа | 3 апреля 2026 |
| Срок проекта (запрос) | 5 месяцев (~4 impl + 1 stabilize) |

---

## 2. Инфраструктурные требования

| Требование | Источник |
|-----------|----------|
| ✅ Полностью on-premises | Звонок: *"AI engine have to be on premises on Jadwa disconnected from internet"* |
| ✅ Нет облачных подписок и токенов | Звонок: *"no cloud subscription or token-based billing"* |
| ✅ Имеющееся железо: HP Omen AI-Ready, Windows 11 Enterprise | Письмо Хамзы: *"Jadwa have already Power AI-Ready HP Omen machine on-premises"* |
| ✅ Open-source LLM | Звонок: не привязываться к вендору |
| ✅ Python-based стек | Звонок: *"Python is king at the moment"* |
| ✅ LangChain/LangGraph MIT | Звонок: Алекс подтвердил MIT license |
| ✅ Контроль доступа по пользователям | Звонок: *"permission control and apply it on this"* |
| ✅ Модульная архитектура | Звонок: *"I'm not bound to one vendor... one process done by you, one process done by someone else"* — каждый воркфлоу должен быть независимым модулем, расширяемым другой командой |
| ❓ VRAM HP Omen | Не уточнялось. Критично: LLaMA 3 70B требует ~40GB VRAM |
| ❓ Saudi CR | Письмо: *"do you have Saudi CR?"* — ответа нет |

---

## 2a. Модель поставки и ограничения

**Источник:** Звонок, Хамза (`~24:00–27:00`)

| Требование | Цитата | Статус |
|-----------|--------|--------|
| Нет отдельного UAT — live learning в production | *"we skip the UAT part and everything is just learned directly... the live learning model rather than spending time on UAT and then production"* | ✅ |
| Fine-tuning / prompt engineering роль в команде | *"someone who spent time on the problem learning, natural language learning like this function in this. If this question come, you need to ask and confirm this is the date format"* | ✅ |
| Предсказуемая стоимость на имеющемся железе | *"some people might come up with me for millions... I need to wait for shipment and custom clearance... never endless"* | ✅ |
| Модульность по воркфлоу — разные команды/вендоры могут работать над разными процессами | *"one process done by you, one process done by someone else. If I have the core [foundation] then my requirement will change"* | ✅ |

> ⚠️ **Риск live learning:** Анаста предупредила — *"the model must be fine-tuned... for this when you need to reach a greater accuracy it may take even more time than setting up the model"*. Хамза принял к сведению, но настаивает на отсутствии формального UAT.

---

## 3. Общая модель взаимодействия ("fire and forget")

**Источник:** Звонок, Хамза (`~13:00`):
> *"They will initiate this prompt and let the agentic AI engine do everything on itself"*

Паттерн:
1. Пользователь вводит NL-промпт
2. Агент при необходимости уточняет параметры (дата, период и т.п.)
3. Агент выполняет весь workflow автономно в фоне
4. По завершении — email + SMS с подтверждением и summary
5. Человек не вмешивается в процесс

---

## 4. Воркфлоу

### 4.1. Trading Session

**Источник:** Письмо Хамзы ✅

**Оригинал (дословно из письма):**
> Import trades from Jadwa broker · Receive the trading files from Brokers · Reconcile with PM file · Upload to APX · Send a summary for the reconcile · Send email to the team to post · Send trades to fund admin · Send Settlement instruction to the custodian · Send a summary to the team for the settlement instruction and fund admin reports

```
1.  Импортировать сделки от брокера Jadwa (внутренняя брокерская система)
2.  Получить торговые файлы от внешних брокеров
3.  Сверить с PM-файлом (portfolio management)
4.  Загрузить в APX
5.  Отправить summary по reconciliation
6.  Отправить email команде для постинга
7.  Отправить сделки fund administrator
8.  Отправить Settlement Instruction кастодиану
9.  Отправить summary по settlement и fund admin reports
```

**Интеграции:** внутренний брокер Jadwa (API/формат ❓), внешние брокерские файлы (формат ❓), APX (API/коннектор), email, кастодиан (формат ❓), fund administrator (формат ❓)
**Bloomberg:** не задействован в этом воркфлоу

---

### 4.2. Reconcile Holdings and Cash (Custodian)

**Источник:** Письмо Хамзы ✅

**Оригинал (дословно из письма):**
> Receive the files from custodians · Import holding from DFN · Reconcile holding and cash for Jadwa custody and external custody · Send a summary for the reconcile and breaks · Upon team fixing the breaks, regenerate the files till there is no breaks appear, or confirmation from IOD team

```
1.  Получить файлы от кастодианов
2.  Импортировать holdings из DFN
3.  Сверить holdings и cash: Jadwa custody vs. external custody
4.  Отправить summary по breaks (расхождениям)
5.  Команда исправляет breaks вручную
6.  Регенерировать файлы
7.  Повторять цикл до нулевых расхождений
     ИЛИ до confirmation email от IOD team (принудительная остановка)
```

**Интеграции:** файлы кастодианов (7–8 форматов ✅), DFN (❓), email
**Bloomberg:** не задействован в этом воркфлоу

> ❓ **DFN** — неизвестная система. Не описана ни на звонке, ни в презентации. Нужно выяснить: что это, есть ли API, файловый обмен, база данных?

---

### 4.3. Bloomberg Reconcile

**Источник:** Письмо Хамзы ✅ + детализация на звонке ✅
На звонке Хамза назвал этот воркфлоу: *"complicated, a genetic complete flow"*

**Оригинал (дословно из письма):**
> Upload cash to Bloomberg · Import holding and cash from Bloomberg · Run SFTP file for Bloomberg files · Import holding and cash from APX · Run the reconcile using Recon · Send a summary for the breaks for their approval to upload the ticket · Upon the approval to upload the ticket, upload ticket to Bloomberg · Send email to PM for their approval · Upon PM email approval, regenerate the files from Bloomberg and APX · Reconcile and repeat the process till there is no differences appear or confirm email from IOD team to stop the process

```
1.  Upload cash в Bloomberg
2.  Импортировать holdings и cash из Bloomberg
3.  Run SFTP-файл для Bloomberg
4.  Импортировать holdings и cash из APX
5.  Run reconciliation через Recon
6.  Отправить summary breaks на апрувал команде
7.  После апрувала — Upload ticket в Bloomberg
8.  Отправить email PM для апрувала
9.  После апрувала PM — перегенерировать файлы из Bloomberg и APX
10. Повторять цикл до нулевых расхождений
     ИЛИ до confirmation email от IOD team (принудительная остановка)
```

**Детализация шагов по типу автоматизации:**

| Шаг | Операция | Тип автоматизации | Уверенность |
|-----|----------|-------------------|-------------|
| 1 | Upload cash | Bloomberg Terminal UI | ✅ Хамза вслух: *"go to the visual screen... mimic human interface, click here click here"* |
| 2 | Import from Bloomberg | Bloomberg BLPAPI или UI | ⚠️ Хамза сказал *"some areas have APIs"* — конкретно этот шаг не уточнял |
| 3 | Run SFTP | Bloomberg BBSFTP (paramiko) | ✅ Письмо: явно написано "SFTP file" |
| 4 | Import from APX | APX API/коннектор | ✅ Стандартная интеграция |
| 5 | Run Recon | Неизвестная система "Recon" | ❓ Что такое Recon? |
| 6 | Summary email | Email | ✅ |
| 7 | Upload ticket | Bloomberg Terminal UI или файл | ⚠️ Только в письме, не описан вслух |
| 8–9 | Email approval loop | Email + триггер | ✅ |
| 10 | Цикл до нуля | Оркестратор | ✅ |

> ❓ **Recon** — неизвестная система. Не описана. Нужно выяснить: вендорский продукт/in-house, есть ли API?

---

### 4.4. Email Reconciliation (описан устно, в письме отдельно не выделен)

**Источник:** Только звонок, Хамза (`~14:00`) ✅

> *"Some emails we will receive maybe 20, 30 different of files are there... Based on predefined, the AI engine will pick them up automatically, do the reconciliation, analyze the files, compare the files with other files that we receive within the system, then generate a summary"*

```
1.  Мониторинг входящей почты
2.  Автоматический подбор писем (~20–30 за цикл) с вложениями
3.  Парсинг вложений (7–8 разных форматов файлов)
4.  Сверка файлов друг с другом и с данными внутренних систем
5.  Генерация summary с четырьмя статусами:
     - ✅ Matching (всё совпало)
     - ❌ Not matching (расхождение)
     - ⚠️  Needs attention (требует вмешательства)
     - ✅ Already posted correctly (уже обработано)
```

---

## 5. Что Bloomberg и как работает

| Утверждение | Статус |
|-------------|--------|
| Bloomberg Terminal — нативное Windows-приложение (Win32), не веб | ✅ |
| Bloomberg Anywhere (веб-версия) — **исключён из скоупа** | ✅ Хамза: *"disconnected from internet"* |
| Часть операций Bloomberg доступна через BLPAPI (read-only) | ✅ Хамза: *"for data we're consuming some parts, there are APIs"* |
| Часть операций Bloomberg **не имеет API** и требует UI | ✅ Хамза: *"in some areas there are no APIs at all. it has to be done using interface"* |
| Bloomberg BBSFTP — Bloomberg's own SFTP service | ✅ Явно в письме: "Run SFTP file for Bloomberg files" |
| UI-автоматизация Bloomberg: pywinauto (Win32 backend) | ⚠️ Техническое решение SA, требует PoC |
| UI-автоматизация Bloomberg: pywinauto (win32-backend) | ⚠️ Техническое решение SA, требует PoC |
| Bloomberg Datafeed Addendum: данные не могут покидать машину с Bloomberg | ⚠️ Юридическое ограничение Bloomberg — влияет на архитектуру |

---

## 6. Открытые вопросы (требуют ответа от Хамзы)

| # | Вопрос | Почему важно |
|---|--------|--------------|
| 1 | Шаги "Upload cash" и "Upload ticket" — есть файловый способ (SFTP / UPLD<GO>), или только ручная навигация по экранам Bloomberg? | Определяет объём UI-автоматизации |
| 2 | "Import holding and cash from Bloomberg" (шаг 2) — это BLPAPI или нужен экран? | Аналогично |
| 3 | Что такое **DFN**? Есть ли API, файловый обмен, база? | Workflow B невозможно оценить без этого |
| 4 | Что такое **Recon**? Вендорский продукт или in-house? Есть ли API? | Workflow C шаг 5 |
| 5 | "Import trades from Jadwa broker" (WF A шаг 1) — из какой системы? API, файл, база? | Workflow A: отдельный шаг от получения внешних файлов |
| 6 | Форматы файлов от внешних брокеров (WF A шаг 2) и формат Settlement Instruction для кастодиана? | Workflow A: определяет парсинг и генерацию |
| 7 | Формат отправки сделок fund administrator (WF A шаг 7)? | Workflow A: ещё одна интеграция |
| 8 | Какой GPU и VRAM в HP Omen? | LLaMA 3 70B требует ~40GB VRAM; от этого зависит выбор модели |
| 9 | **Saudi CR** — есть ли у ScienceSoft? | Хамза прямо спросил в письме, ответа нет |

---

## 7. Что НЕ входит в скоуп (явно или по умолчанию)

- Bloomberg Anywhere (требует интернет — исключён)
- Cloud LLM (ChatGPT, Claude API, AWS Bedrock) — исключён
- Проприетарное оборудование (Nvidia GPU под заказ) — Хамза: *"some people might come up with me for millions... I need to wait for shipment and custom clearance... never endless"*
- Формальный UAT-цикл — Хамза: *"we skip the UAT part... the live learning model"*
- Live trading / decision making — Хамза явно исключил на звонке
- Q&A по историческим данным / public offerings — *"we are not looking into that perspective at the moment"*
