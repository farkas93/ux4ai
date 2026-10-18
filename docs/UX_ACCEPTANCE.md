# UX Acceptance Checklist

This checklist directly covers the improvement feedback that triggered the UI rebuild.

## Shell and terminology

- [ ] Header stays visible and includes language selection, active section title, and latest action feedback.
- [ ] Sidebar navigation follows this order: Value Hypothesis, Explore Dimensions, Explore Backlog, Explore Priority, Build Self-Improvement, Summary & Export.
- [ ] AI Safety and Project History are not reachable as workspace pages.
- [ ] AI Safety is absent from Summary & Export previews and downloaded reports.
- [ ] Changing products from any workflow page reloads that product's data across all pages.
- [ ] Setup, backlog, priorities, and the improvement loop load together; failed
  auxiliary comparison/report requests do not leave later workflow pages empty.
- [ ] Fetching saved priority values does not write them back or increase revisions.
- [ ] Compare to Product is saved to the active product and restored after switching away and back.
- [ ] Summary & Export shows Compare to Product in closed-by-default section accordions, with exports above the sections.
- [ ] Summary & Export progress omits hypotheses connected to value, priority hypothesis selected, and next experiment defined.
- [ ] Long multiline fields scroll when content exceeds their viewport.
- [ ] Explainability appears before Accessibility; Accessibility retains the existing target-demographics scale.
- [ ] Pending edits prompt with Save & Switch, Discard & Switch, and Cancel; saves apply to the project being left.
- [ ] User-facing copy consistently says product (not a mixture of project/product).
- [ ] Product name is entered once during creation and edited once in Product Setup.
- [ ] English/German switching does not reset entered content.

## Explore Dimensions

- [ ] No component displays an unexpected `Error` label on initial load.
- [ ] Each dimension appears as an accordion with status, 0–5 slider, rationale, basis, evidence, and uncertainty.
- [ ] Questions and assumptions can be added inside each dimension accordion.
- [ ] Live spider chart updates when dimension status/score changes.
- [ ] Unsaved-change warning is visible until values are saved.
- [ ] Optional comparator selection is above the chart in the same Explore Dimensions tab.
- [ ] Comparator table identifies incompatible dimensions and suppresses misleading differences.
- [ ] Adversarial-risk and feedback-loop reflections are below the dimensions.

## Explore Backlog

- [ ] Assumptions, questions, and hypothesis draft are visible side by side.
- [ ] Selecting a question/assumption prefills a hypothesis draft and preserves provenance.
- [ ] Saved hypotheses remain editable and relationship validation still applies.

## Explore Priority

- [ ] Each hypothesis opens to risk/evidence sliders (0–10, initial 0/0).
- [ ] Ranking updates in real time using `risk + (10 - evidence)`.
- [ ] Risk 10/evidence 0 ranks above risk 0/evidence 10.
- [ ] Matrix hover displays the hypothesis text.
- [ ] Experiment planning remains available below Explore Priority.

## Summary and lifecycle

- [ ] Summary refreshes for the selected product.
- [ ] PDF includes product setup, radar chart, risk/evidence matrix, ranking, notes, and experiments.
- [ ] JSON and Markdown exports remain available.
- [ ] A team can delete its own product only after explicit confirmation.
- [ ] Instructor can delete products; no retention policy or automatic deletion controls are visible.
