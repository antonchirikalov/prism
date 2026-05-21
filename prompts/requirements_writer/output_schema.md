# Requirements Writer — Output Schema

Produce a single Markdown file following this exact structure.

---

## File Header (YAML front-matter)

```yaml
---
exemplar:
  id: <project-slug>
  industry: <industry>
  domain_tags: [<tag1>, <tag2>, ...]
  project_type: <platform | mobile-app | api | integration | other>
  complexity: <low | medium | high>
  source_types: [<list of source_type values from extracts>]
  source_count: <number of sources>
  fr_count: <total FR count>
  nfr_count: <total NFR count>
  sections: [domain-grounding, stakeholders, business-context, fr, nfr, business-rules, data-model, integrations, open-questions]
  quality_score: null
  language: <en | ru | other>
---
```

---

## Document Title and Meta

```markdown
# Requirements: <Project Name>

Generated: <date>  
Sources analysed: <N> documents  
Output language: <English | Russian | other>
```

---

## Document Index

Table of all source files:

```markdown
## Document Index

| # | File | Type |
|---|------|------|
| 1 | `<source_file>` | <source_type> |
...
```

---

## Section: Domain Grounding

One paragraph (3–5 sentences) describing the problem domain, the core value proposition, and the main user flows. No lists — prose only.

```markdown
## Domain Grounding

<paragraph>
```

---

## Section 1: Stakeholders & Roles

Table of all roles mentioned across extracts.

```markdown
## 1. Stakeholders & Roles

| Role | Description |
|------|-------------|
| <Role> | <description> |
...

[Source: `<files>`]
```

---

## Section 2: Business Context

Bullet list of key business facts (model, revenue, geography, timeline, constraints). Each bullet must cite its source.

```markdown
## 2. Business Context

- <topic>: <fact>. [Source: `<file>`]
...
```

---

## Section 3: Functional Requirements

Group requirements into logical subsections. Each subsection gets a numbered header (3.1, 3.2, …) and a table.

```markdown
## 3. Functional Requirements

### 3.1 <Subsection Name>

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-001 | <requirement text> | MUST / SHOULD / COULD | `<file>` |
...
```

Priority values: **MUST** (essential), **SHOULD** (important but not blocking), **COULD** (nice-to-have).

ID format: `FR-NNN` (sequential across all subsections, starting at FR-001).

Every requirement must have at least one source citation — the source file name in backticks.

---

## Section 4: Non-Functional Requirements

Single table. IDs: `NFR-NNN`.

```markdown
## 4. Non-Functional Requirements

| ID | Requirement | Category | Source |
|----|-------------|----------|--------|
| NFR-001 | <text> | Performance / Security / Scalability / Legal / UX / Ops | `<file>` |
...
```

---

## Section 5: Business Rules & Constraints

Single table. IDs: `BR-NNN`.

```markdown
## 5. Business Rules & Constraints

| ID | Rule | Source |
|----|------|--------|
| BR-001 | <rule text> | `<file>` |
...
```

---

## Section 6: Data Model

Table of entities explicitly referenced in the source documents. Mark entities that are **out of scope** clearly.

```markdown
## 6. Data Model (Derived from Sources)

| Entity | Key Attributes (Referenced) | Notes |
|--------|----------------------------|-------|
| <Entity> | attr1, attr2 | [Source: <file>] |
...
```

---

## Section 7: Integration Points

Table of all integrations (APIs, services, libraries) mentioned across sources.

```markdown
## 7. Integration Points

| Integration | Purpose | Priority | Source |
|-------------|---------|----------|--------|
| <Name> | <purpose> | MUST / SHOULD | `<file>` |
...
```

---

## Section 8: Open Questions, Conflicts & Assumptions

### 8.1 Conflicts Found

For each conflict detected between two or more source files:

```markdown
### 8.1 Conflicts Found

| # | Conflict | Documents in Conflict | Resolution |
|---|----------|-----------------------|------------|
| C-001 | <description of the conflict> | `<file1>` vs. `<file2>` | <resolution or "UNRESOLVED — needs stakeholder input"> |
...
```

If no conflicts: write "No inter-source conflicts detected."

### 8.2 Gaps

For each piece of information that is absent from all sources but is needed:

```markdown
### 8.2 Gaps (Information Not Found in Any Source Document)

| # | Gap | Impact |
|---|-----|--------|
| G-001 | <description of what is missing> | <what decision is blocked> |
...
```

### 8.3 Explicit Assumptions

```markdown
### 8.3 Explicit Assumptions

> Assumptions are marked clearly and have NOT been confirmed by source documents. They require validation with the client.

| # | Assumption | Basis |
|---|------------|-------|
| A-001 | <assumption text> | <why this was assumed> |
...
```

---

## End of Document

The document must end with:

```markdown
---

*End of requirements document.*
```
