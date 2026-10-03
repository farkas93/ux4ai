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
#toolkit-sections { margin: 0; border: 0; }
#toolkit-sections > .tab-nav { display: none !important; }
#toolkit-sections > .tabitem { min-width: 0; border: 0; padding: 0 !important; }
#toolkit-workspace { gap: 22px; align-items: flex-start; margin-top: 12px; }
#toolkit-sidebar { padding: 16px; }
#toolkit-menu { display: none; }
#toolkit-main { flex: 1 1 0 !important; min-width: 0 !important; }
#toolkit-desktop-section .wrap { display: flex; flex-direction: column; gap: 2px; }
#toolkit-desktop-section label { width: 100%; border: 0; border-radius: 8px; box-shadow: none;
    padding: 8px 10px; background: transparent; font-size: 13px; }
#toolkit-desktop-section label.selected { background: var(--background-fill-secondary); color: var(--color-accent); }
#toolkit-desktop-section input { position: absolute; opacity: 0; width: 1px; height: 1px; }
#toolkit-desktop-section label:focus-within { outline: 2px solid var(--color-accent); outline-offset: 2px; }
#aipm-app-bar { display: grid !important; grid-template-columns: 200px minmax(180px, 320px) 90px;
    justify-content: start; align-items: center; padding: 8px 0; gap: 14px; background: transparent; min-height: 0; }
#aipm-app-bar > * { min-width: 0 !important; width: auto !important; flex: none !important; }
#toolkit-brand { padding: 0; }
.toolkit-wordmark { font-size: 18px; letter-spacing: -.025em; }
#aipm-app-bar input { font-size: 14px; }
#toolkit-product-admin { margin: 6px 0 12px; max-width: 240px; }
#aipm-status-banner { font-size: 12px; padding: 4px 0; min-height: 0; }
#aipm-status-banner p { margin: 0; font-size: 12px; }
.gradio-container .prose h1 { font-size: 24px; }
.gradio-container .prose h2 { font-size: 24px; margin: 0 0 8px; }
.gradio-container .prose h3 { font-size: 18px; margin: 0 0 8px; }
.gradio-container .prose h4 { font-size: 15px; margin: 0 0 8px; }
.gradio-container .prose p { font-size: 14px; line-height: 1.6; margin: 0 0 10px; }
.gradio-container input, .gradio-container textarea { font-size: 14px !important; line-height: 1.5 !important; }
#toolkit-mobile-section { display: none; }
.toolkit-form-card, .toolkit-card, .backlog-entry { border: 1px solid var(--border-color-primary); border-radius: 12px; padding: 14px !important; background: var(--block-background-fill); }
.toolkit-note-composer { align-items: end; gap: 12px; }
.toolkit-note-composer > button { margin-bottom: 1px; }
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
  #toolkit-menu { display: block; grid-column: 1; grid-row: 1; }
  #aipm-app-bar { grid-template-columns: 76px minmax(0, 1fr) 72px; gap: 8px; padding: 6px 0 12px; }
  #toolkit-brand { grid-column: 2 / -1; grid-row: 1; }
  .toolkit-wordmark { font-size: 16px; }
  #toolkit-product { grid-column: 1 / 3; grid-row: 2; }
  #toolkit-new-product { grid-column: 3; grid-row: 2; }
  #toolkit-new-product { white-space: nowrap; min-height: 40px; padding: 8px; }
  #toolkit-main { width: 100%; min-width: 0 !important; }
}
@media (max-width: 767px) {
  .gradio-container { padding: 12px !important; }
  .toolkit-card, .toolkit-form-card, .backlog-entry { padding: 14px !important; }
  .backlog-fields, .backlog-actions, .toolkit-two-column { flex-direction: column !important; }
  .backlog-fields > *, .toolkit-two-column > * { width: 100%; min-width: 0 !important; }
  #toolkit-assessment-row { flex-direction: column-reverse !important; }
  .backlog-actions button { max-width: none; width: 100%; }
  #toolkit-workspace { display: block; margin-top: 12px; }
  #toolkit-desktop-section label { padding: 8px 6px; font-size: 12px; }
  .toolkit-note-composer { flex-direction: column; align-items: stretch; }
  .gradio-container input, .gradio-container textarea { font-size: 16px !important; }
  .toolkit-form-card { min-width: 0 !important; }
  #toolkit-setup-cards { display: flex !important; flex-direction: column !important; flex-wrap: nowrap !important; gap: 14px; }
  #toolkit-setup-cards > .toolkit-form-card { flex: none !important; width: 100% !important; min-width: 0 !important; }
  #page-project-setup { gap: 14px; }
  #aipm-app-bar { margin: 0 0 8px; }
}
"""
