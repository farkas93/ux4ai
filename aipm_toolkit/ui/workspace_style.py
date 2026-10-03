"""Responsive workspace styling for the approved desktop/mobile review boards."""

WORKSPACE_CSS = """
footer { display: none !important; }
.gradio-container { max-width: 1530px !important; margin: auto !important; padding: 20px !important; }
#toolkit-brand h1 { font-size: 20px; letter-spacing: -.025em; margin: 0; }
#toolkit-brand { padding: 8px 0; }
#toolkit-login { max-width: 460px; margin: 40px auto; padding: 28px; border: 1px solid var(--border-color-primary); border-radius: 16px; }
#aipm-app-bar { align-items: center; padding: 12px 0 20px; border-bottom: 1px solid var(--border-color-primary); }
#aipm-app-bar button { min-width: 80px; }
#aipm-status-banner { padding: 6px 12px; color: var(--body-text-color-subdued); }
#toolkit-sections { display: grid; grid-template-columns: 185px minmax(0, 1fr); gap: 24px; margin-top: 22px; }
#toolkit-sections > .tab-nav { display: flex; flex-direction: column; align-items: stretch; border: 0; gap: 5px; position: sticky; top: 20px; align-self: start; }
#toolkit-sections > .tab-nav button { text-align: left; border: 0; border-radius: 8px; padding: 12px; font-size: 14px; white-space: normal; }
#toolkit-sections > .tab-nav button.selected { background: var(--background-fill-secondary); color: var(--color-accent); }
#toolkit-sections > .tabitem { grid-column: 2; grid-row: 1; min-width: 0; border: 0; padding: 0 !important; }
#toolkit-mobile-section { display: none; }
.toolkit-form-card, .toolkit-card, .backlog-entry { border: 1px solid var(--border-color-primary); border-radius: 12px; padding: 20px !important; background: var(--block-background-fill); }
.backlog-table-container { gap: 18px; }
.backlog-fields { align-items: stretch; }
.backlog-actions { align-items: end; }
.backlog-actions button { max-width: 130px; }
.toolkit-page-heading h2 { margin-top: 0; font-size: 26px; letter-spacing: -.025em; }
.toolkit-page-heading p { color: var(--body-text-color-subdued); }
.toolkit-account a { color: var(--body-text-color-subdued); text-decoration: none; font-size: 13px; }
.toolkit-account { text-align: right; }
.toolkit-history-card { border: 1px solid var(--border-color-primary); border-radius: 12px;
  padding: 18px 20px; margin-bottom: 14px; background: var(--block-background-fill); }
.toolkit-history-card small { color: var(--body-text-color-subdued); }
.toolkit-history-card h3 { margin: 10px 0; font-size: 16px; }
.toolkit-history-card p { margin: 6px 0 0; color: var(--body-text-color-subdued); font-size: 13px; }
#toolkit-workspace-note, #toolkit-session-note { display: none !important; }
label span { background: transparent !important; color: var(--body-text-color) !important; }
@media (max-width: 1023px) {
  #toolkit-mobile-section { display: block; margin-top: 14px; }
  #toolkit-sections { display: block; margin-top: 20px; }
  #toolkit-sections > .tab-nav { display: none; }
}
@media (max-width: 767px) {
  .gradio-container { padding: 12px !important; }
  .toolkit-card, .toolkit-form-card, .backlog-entry { padding: 14px !important; }
  .backlog-fields, .backlog-actions, .toolkit-two-column { flex-direction: column !important; }
  .backlog-fields > *, .toolkit-two-column > * { width: 100%; min-width: 0 !important; }
  #toolkit-assessment-row { flex-direction: column-reverse !important; }
  .backlog-actions button { max-width: none; width: 100%; }
}
"""
