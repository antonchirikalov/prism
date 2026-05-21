# Requirements Writer — Conflict Resolution Rules

When synthesising requirements from multiple source documents, you will encounter contradictions. Apply these rules consistently.

---

## Rule 1: Trust Hierarchy

When two sources contradict each other, the higher-trust source wins **unless** the lower-trust source is more recent.

Trust order (highest to lowest):
1. `formal_decision` — signed specs, contracts, approved decisions
2. `explicit_statement` — written requirements documents, RFP/RFQ
3. `transcript` — meeting recordings or transcripts
4. `chat` — messaging exports, email threads
5. `notes` — informal notes, drafts

**Example:** A formal RFQ says Hyperledger Fabric. An informal Architecture Notes says Polygon L2. The RFQ wins because `explicit_statement` > `notes`. But if the Architecture Notes is dated 3 months later, flag it as an unresolved conflict and escalate.

---

## Rule 2: Never Silently Choose

You must **never** silently resolve a conflict by picking one source and ignoring the other. Every conflict must appear in Section 8.1 with:
- A clear description of what contradicts what
- Which documents are in conflict
- A proposed resolution (or UNRESOLVED if you cannot determine the winner)

---

## Rule 3: Technical Choice Conflicts

When sources disagree on technical choices (blockchain platform, framework, language, infrastructure provider):
- List **all options** mentioned across sources in the relevant FR/NFR row, e.g.: `"Hyperledger Fabric (per RFQ) / Polygon L2 (per Architecture Notes)"`
- Create a conflict entry in 8.1
- Proposed resolution: defer to the document with higher trust level, or mark UNRESOLVED

---

## Rule 4: Scope Conflicts

When one source includes a feature and another excludes it:
- Include the feature as a requirement if **any** source requires it
- Add `[SCOPE CONFLICT: see C-XXX]` to the Source column
- Document in 8.1

---

## Rule 5: Quantitative Conflicts

When sources give different numbers (SLA, timeout, budget, timeline):
- Use the **more conservative / more constraining** value in the requirement
- Note the conflict in 8.1
- **Example:** Source A says "response time < 2s", Source B says "< 500ms" → use `< 500ms` (stricter)

---

## Rule 6: Gaps vs. Conflicts

A **gap** is information that is absent from all sources (not contradicted — just missing). Gaps go in Section 8.2, not 8.1.

A **conflict** is when two or more sources say different things about the same topic. Conflicts go in Section 8.1.

---

## Rule 7: Intra-source Inconsistencies

If a single source document contradicts itself internally (e.g., the Technical Annex lists 4 protection layers in section 2 but 5 layers in section 5), note this in the source's `potential_conflicts` field (already present in the extract). Document it in Section 8.1 as well, attributed to a single source.

---

## Rule 8: Language and Version

If a document exists in multiple languages (e.g., Italian + English) and they differ:
- The English version is authoritative for technical terms
- Flag any substantive differences between language versions as a conflict

---

## Rule 9: Assumption Marking

When you cannot determine the correct value due to a conflict or gap and you must make a choice to complete the document, mark it as an assumption in Section 8.3. Format:

> **A-NNN** | [assumption text] | Basis: [why this was assumed, which rule was applied]
