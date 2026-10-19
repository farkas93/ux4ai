# AI product comparison references

**Assessment dates: 18–19 October 2026 · Current application rubric: version 1**

This catalog contains 16 ready-to-import, scoped design assessments for
**Explore Dimensions**. The scores are AI-assisted estimates based on the linked
official product documentation. No hands-on trials, user studies, accuracy
measurements, or production performance tests were performed. Each JSON records
the assessment basis, scope, per-dimension rationale, confidence, uncertainty,
and sources so the estimates can be reviewed or revised.

## Files and scores

Import only the JSON files in `products/`. `import_manifest.json` is separate so
the importer will not mistake it for a product assessment.

| File in `products/` | Scoped product | Conversation | Specialization | Autonomy | Explainability | Accessibility |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `chatgpt.json` | ChatGPT: standard chat | 5.0 | 0.5 | 1.0 | 1.5 | 4.5 |
| `claude.json` | Claude: document chat | 5.0 | 1.0 | 1.5 | 2.0 | 4.0 |
| `google_gemini.json` | Google Gemini: standard chat | 5.0 | 0.5 | 1.0 | 1.5 | 4.5 |
| `grok_bot.json` | Grok Bot: cross-app research and drafting | 4.0 | 2.0 | 4.0 | 3.5 | 3.0 |
| `microsoft_365_copilot.json` | Microsoft 365 Copilot: Word authoring | 4.0 | 3.5 | 2.5 | 3.0 | 3.5 |
| `perplexity.json` | Perplexity: ordinary web search | 4.5 | 3.0 | 2.0 | 4.0 | 4.0 |
| `gemini_notebook.json` | Gemini Notebook / NotebookLM: source Q&A | 4.0 | 3.5 | 2.0 | 4.5 | 3.5 |
| `deepl_translator.json` | DeepL Translator: text translation | 0.5 | 5.0 | 1.0 | 2.0 | 4.5 |
| `grammarly.json` | Grammarly: inline writing suggestions | 0.5 | 4.5 | 1.5 | 4.0 | 4.0 |
| `canva_ai.json` | Canva AI: Magic Design for Presentations | 2.0 | 4.0 | 2.5 | 2.0 | 4.0 |
| `adobe_firefly.json` | Adobe Firefly: image generation and editing | 1.5 | 4.5 | 2.0 | 1.5 | 4.0 |
| `github_copilot.json` | GitHub Copilot: VS Code suggestions and chat | 3.0 | 4.5 | 2.0 | 2.5 | 2.5 |
| `otter.json` | Otter: transcription and summaries | 1.0 | 4.0 | 2.5 | 3.5 | 3.5 |
| `cursor.json` | Cursor: coding agent | 4.0 | 4.5 | 3.5 | 3.5 | 2.0 |
| `fin.json` | Fin: knowledge-base customer support | 4.0 | 4.5 | 3.0 | 2.0 | 4.0 |
| `zapier_agents.json` | Zapier Agents: expense classification (legacy) | 1.5 | 4.5 | 3.5 | 3.5 | 2.5 |

### How to interpret the five dimensions

All five keys and scale versions match `aipm_toolkit/dimensions.py`:

- **`conversational`**: guided interaction (0) to open-ended conversation (5).
  Accepting natural-language input alone does not make a workflow conversational.
- **`specialization`**: general-purpose (0) to task/domain-specific (5). A prompt
  about one topic does not turn a general assistant into a specialized product.
- **`autonomy`**: consulting (0) to theoretical full autonomous agency (5).
  The assumed approvals, integrations, and action permissions matter. No profile
  is scored 5; higher autonomy is not a target.
- **`explainability`**: opaque product experience (0) to fully transparent (5).
  Citations, highlighted changes, and activity logs improve inspectability but
  do not demonstrate faithful access to internal model reasoning.
- **`accessibility`**: how well the product supports its intended target
  demographics, from narrow (0) to broad (5). This is not a WCAG/accessibility
  audit; the evaluated demographics are stated in each file.

Half-point scores express coarse judgment, not measured precision. These are
one-assessment reference profiles (`n = 1`), not student-cohort aggregates. Median,
minimum, maximum, and quartiles will therefore coincide after import; this is not
evidence of evaluator agreement. Use a profile as a task comparator only when the
task and configuration are reasonably comparable; otherwise use it as a design
contrast.

Canva is scoped to the documented Magic Design presentation workflow; newly
announced Canva AI 2.0 automation is excluded. Gemini Notebook is the renamed
NotebookLM; source Q&A excludes its newer cloud-computer capabilities. Zapier's
documentation now describes migration from Agents to AI by Zapier. Its file
explicitly assesses the legacy Agents experience, not the replacement product.

Grok Bot is scoped to a single persistent cloud Bot researching across approved
apps and preparing drafts for human review. This is the Grok Bot agent product;
ordinary Grok chat, coding workflows, schedules and multi-Bot orchestration are
outside this assessment. Its documentation review is dated **19 October 2026**;
the original 15 profiles retain their **18 October 2026** review dates.

## Import in production

Use a deployed application containing the internal-name repairs from this task.
The menu labels remain **Value Hypothesis → Explore Dimensions → Explore Backlog
→ Explore Priority → Build Self-Improvement → Summary & Export**. Database names,
Python symbols, note origins, migration definitions, and export keys retain their
original internal identifiers. These repairs require no new database migration
on an existing, previously working database.

### Instructor upload

1. Sign in with the production instructor account.
2. Open **Historical reference import**.
3. Upload the 16 JSON files from `baseline/products/` into **Legacy JSON files**.
4. Upload `baseline/import_manifest.json` into **Import manifest JSON**.
5. Click **Preview import**. Expect 16 records, 16 distinct product names, and no
   invalid values. Then use **Publish preview**.
6. Reload the team workspace. The scoped product names appear under
   **Explore Dimensions → Compare to Product**.

If the original 15 references are already published, upload only
`baseline/products/grok_bot.json` alongside the same
`baseline/import_manifest.json`, preview **1 record** with no invalid values,
then use **Publish preview**. The existing cohort label is retained so the
addition leaves published references and saved comparison snapshots intact;
Grok Bot's own review date and provenance are stored with its dataset.

### CLI import

Run from the application repository root with the existing production
`AIPM_DATABASE_URL` available in the environment. If production uses the
container's installed Python package, replace `uv run python` with `python`.

Preview the files without writing to the database:

```bash
uv run python -m aipm_toolkit.import_baselines baseline/products --manifest baseline/import_manifest.json --preview
```

Import and publish the cohort named by the manifest:

```bash
uv run python -m aipm_toolkit.import_baselines baseline/products --manifest baseline/import_manifest.json --publish
```

The manifest sets **every dimension to version 1**, including autonomy. Omitting
it uses legacy defaults that mark autonomy incompatible with the current rubric.

Scoped names distinguish these references from the older `solutions/` records.
Importing this dated cohort does not overwrite published legacy references or
previous comparison snapshots. Re-importing an already published cohort is
skipped. For a later reassessment, use a new dated cohort or the existing
replacement-dataset workflow.

The importer stores `product_name` and `scores` as catalog/score data and the
complete source JSON in `BaselineAssessment.raw_record`. Per-product
`provenance_notes` are also retained on the dataset and in report provenance.
This keeps the date, mode, limitations and sources available alongside the
comparison. The additional `scope`, `dimensions`, and `sources` fields are
reference documentation; they are not new required importer fields.
