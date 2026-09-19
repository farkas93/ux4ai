# UX Acceptance Checklist

This checklist directly covers the improvement feedback that triggered the UI rebuild.

## Shell and terminology

- [ ] Header stays visible and includes language selection, active section title, and latest action feedback.
- [ ] Navigation uses real tabs: Project Setup, Assessment, Backlog creator, Prioritization, Summary & Export.
- [ ] User-facing copy consistently says product (not a mixture of project/product).
- [ ] Product name is entered once during creation and edited once in Product Setup.
- [ ] English/German switching does not reset entered content.

## Assessment

- [ ] No component displays an unexpected `Error` label on initial load.
- [ ] Each dimension appears as an accordion with status, 0–5 slider, rationale, basis, evidence, and uncertainty.
- [ ] Questions and assumptions can be added inside each dimension accordion.
- [ ] Live spider chart updates when dimension status/score changes.
- [ ] Unsaved-change warning is visible until values are saved.
- [ ] Optional comparator selection is above the chart in the same Assessment tab.
- [ ] Comparator table identifies incompatible dimensions and suppresses misleading differences.
- [ ] Adversarial-risk and feedback-loop reflections are below the dimensions.

## Backlog creator

- [ ] Assumptions, questions, and hypothesis draft are visible side by side.
- [ ] Selecting a question/assumption prefills a hypothesis draft and preserves provenance.
- [ ] Saved hypotheses remain editable and relationship validation still applies.

## Prioritization

- [ ] Each hypothesis opens to risk/evidence sliders (0–10, initial 0/0).
- [ ] Ranking updates in real time using `risk + (10 - evidence)`.
- [ ] Risk 10/evidence 0 ranks above risk 0/evidence 10.
- [ ] Matrix hover displays the hypothesis text.
- [ ] Experiment planning remains available below prioritization.

## Summary and lifecycle

- [ ] Summary refreshes for the selected product.
- [ ] PDF includes product setup, radar chart, risk/evidence matrix, ranking, notes, and experiments.
- [ ] JSON and Markdown exports remain available.
- [ ] A team can delete its own product only after explicit confirmation.
- [ ] Instructor can delete products; no retention policy or automatic deletion controls are visible.
