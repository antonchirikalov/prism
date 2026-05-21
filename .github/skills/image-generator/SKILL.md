---
name: image-generator
description: Generates publication-quality academic illustrations using the PaperBanana package (llmsresearch/paperbanana) — a multi-agent pipeline (Retriever → Planner → Stylist → Visualizer ↔ Critic) with OpenAI as the provider.
---

# Image Generator (PaperBanana Pipeline)

## When to use
- When Illustrator agent needs to generate academic diagrams
- When regenerating specific diagrams after Critic feedback

## CRITICAL: Choosing the right mode

### Full PaperBanana pipeline (DEFAULT — all illustration types)
```bash
.venv/bin/python .github/skills/image-generator/scripts/paperbanana_generate.py "[description]" "illustrations/diagram_N.png" --context "[section text, 200-500 words]" --critic-rounds 2
```

The wrapper calls the real `paperbanana` package (`PaperBananaPipeline.generate()`) with OpenAI provider:
- **Phase 1 (Linear Planning):** Retriever → Planner → Stylist
- **Phase 2 (Iterative Refinement):** Visualizer ↔ Critic (default 2 rounds)

VLM agent (Planner/Stylist/Critic) uses `gpt-5.2`, image generation (Visualizer) uses `gpt-image-1.5`.

**Pipeline takes 3–5 min per illustration (5–7 API calls).** Always use `run_in_terminal` with `timeout: 0` (no timeout limit).

### Direct generation (via `--direct` flag)
```bash
.venv/bin/python .github/skills/image-generator/scripts/paperbanana_generate.py "[description]" "illustrations/diagram_N.png" --direct
```

**Use `--direct` when:** explicitly requested via flag or prompt. Single API call, ~40 sec.

**Prompt guidelines for `--direct`:**
- Keep prompts SHORT (2-4 sentences max)
- Focus on visual structure, not exact text labels
- Describe shapes, colors, spatial layout
- Do NOT list exact text for every label
- Do NOT write multi-paragraph layout specs — this causes ASCII-art output

## Configuration

The script reads from `.env` file in project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key for all agents |
| `TEXT_MODEL` | `gpt-5.2` | VLM model for Planner/Stylist/Critic |
| `IMAGE_MODEL` | `gpt-image-1.5` | Image generation model |
| `MAX_CRITIC_ROUNDS` | `2` | Visualizer-Critic refinement iterations |

## Dependencies

```
pip install "paperbanana[openai]" python-dotenv
```

## Output
- Generates one PNG at the specified path (copied from PaperBanana's `outputs/` dir)
- All intermediate iterations and metadata saved by PaperBanana in `outputs/`
