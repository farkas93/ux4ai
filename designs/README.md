# Responsive app design · Draft 01

These are **review mockups only**, not app implementation. Each numbered SVG places a desktop proposal on the left and a mobile proposal on the right. Open `index.html` locally for a gallery, or view individual SVG files in a browser. The existing `app-bar.svg` is preserved as the earlier direction.

## Implementation status

The approved shared layout is now implemented: compact workspace branding, desktop sidebar, tablet/mobile section selector, card-based backlog with stacked inputs, reorganized assessment profile, collapsible administration, and history cards. The SVGs remain the reference for further visual review. Decorative sample progress counts, filters, and one-click file preparation in the mockups are not substituted for existing backend state; the actual interface continues to use the existing checklist and export preparation actions. Browser screenshot verification still needs a machine with Playwright Chromium installed.

The sidebar now uses explicit radio navigation instead of restyling Gradio's tab navigation: its tab overflow logic produced an unwanted menu in the initial implementation. Label colors, padding, and font sizes are set through Gradio theme tokens as well as scoped CSS. Browser verification currently requires the Chromium system libraries; downloading the Playwright browser alone was insufficient in the development container.

Following visual feedback, section pages are now plain visibility-controlled containers: Gradio Tabs are not instantiated at all. Sidebar-only navigation is retained at every breakpoint, with a narrower sidebar on small screens. Product administration sits beneath navigation instead of occupying space above the exercise. Compact question/assumption type dropdowns reduce the height of learning-note forms.

Mobile correction: navigation now uses Gradio's native collapsible `Sidebar`, initially closed. A mobile Menu button opens it; choosing a section closes it on small screens. There is no fixed sidebar consuming the phone's form width. The mobile header uses a compact grid, and text inputs use 16px text to avoid iOS focus zoom. Native drawer behavior and actual device appearance still require browser verification with the host libraries installed.

## Pages to review

| File | Review focus |
| --- | --- |
| `01-login.svg` | Brand, description, student learning path, sign-in |
| `02-project-setup.svg` | Product idea → user/problem → value hypothesis |
| `03-assessment.svg` | Dimension editor, radar, questions and comparison |
| `04-ai-safety.svg` | Six discussion topics and question/assumption capture |
| `05-self-improvement.svg` | One loop, five capability prompts, open questions |
| `06-backlog-creator.svg` | Source context and question/assumption → hypothesis editing |
| `07-prioritization.svg` | Risk/evidence inputs, ranking, matrix |
| `08-summary-export.svg` | Value summary, progress and downloads |
| `09-project-history.svg` | Readable activity timeline |
| `10-instructor.svg` | Course overview, sharing, accounts, collapsed administration |

## Shared design direction

- Login carries the explanation. The signed-in workspace uses a compact brand/product header, without a repeated introductory banner or sign-in message.
- Desktop: section navigation in a narrow left sidebar; product/account/language controls in a short header.
- Tablet (768–1023 px): compact header, section selector, flexible one/two-column content depending on available width.
- Mobile (<768 px): product and section selectors, stacked editors, full-width primary actions. The assessment profile is collapsible and comes before the dimension editor.
- Plain labels, a restrained teal accent, softer borders, and consistent form spacing replace badge-like labels and oversized controls.
- Delete is a secondary product/account action, not a prominent top-level button. Confirmation remains required.
- Save feedback belongs near the relevant action; global errors should still be visible. Draft indicators must reflect real state, not visual-only success messages.
- Safety scoring and advanced Self-Improvement features remain absent.

The first draft uses light mode for legibility and layout review. A matching dark-mode board can follow once the structure is agreed. This is not a decision to remove dark mode.

## Gradio feasibility

Most layout changes are feasible using `Row`, `Column`, `Accordion`, `State`, form components, theme tokens, scoped CSS, and navigation callbacks. A desktop sidebar and mobile section selector can control the same section containers while retaining state. Breakpoint behavior needs browser testing rather than relying on fixed SVG dimensions.

The backlog proposal deliberately explores cards/detail editing instead of a wide table. Filters, inline download buttons, account menus, progress widgets, and detailed before/after history are **proposed UX**, not claims about existing functionality. They require explicit approval and suitable callbacks/services before implementation. Radar typography should use actual dimension titles; abbreviated labels in the sketch illustrate spacing only.

For implementation, use semantic native controls where possible, keyboard/focus support, responsive chart sizing, and theme-aware Plotly colors. The SVG is a layout specification, not markup to embed as the working UI.

## How to give feedback

Start with `03-assessment.svg` and `06-backlog-creator.svg`, because they exercise the shared shell and the most complex editing layout. For each page, tell me:

1. What should be more or less prominent?
2. Which controls should remain visible versus collapsed?
3. Does desktop/mobile ordering match the way students work?
4. What wording or grouping is confusing?
5. Should we keep the current table, use cards, or use a selected-entry editor for the backlog?

Keep revisions numbered so we can compare proposals. `render_mockups.py` is a design-only authoring helper used to generate the SVGs; it does not import or modify the application.
