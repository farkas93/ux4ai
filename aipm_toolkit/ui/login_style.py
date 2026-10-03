"""Self-contained login styling: no third-party fonts, scripts or images."""

LOGIN_CSS = """
:root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #172b43; background: #f3f6fa; }
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; }
main { max-width: 1120px; margin: auto; padding: 64px 32px; }
.brand { display: flex; align-items: center; gap: 12px; font-weight: 750; font-size: 18px; }
.brand-mark { display: grid; place-items: center; background: #0f766e; color: white;
  width: 42px; height: 42px; border-radius: 12px; font-size: 14px; }
.layout { display: grid; grid-template-columns: 1.25fr 1fr; gap: 72px; align-items: center; margin-top: 64px; }
.eyebrow { color: #0f766e; font-size: 12px; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }
h1 { font-size: clamp(32px, 4vw, 48px); line-height: 1.12; letter-spacing: -.035em; margin: 16px 0 24px; }
.intro { font-size: 18px; color: #526277; line-height: 1.65; }
.steps { list-style: none; padding: 0; margin: 28px 0; }
.steps li { display: flex; gap: 14px; margin: 20px 0; line-height: 1.5; }
.step { flex-shrink: 0; display: grid; place-items: center; width: 30px; height: 30px;
  border: 1px solid #bddad7; border-radius: 50%; color: #0f766e; font-weight: 700; font-size: 13px; }
.steps small { display: block; color: #526277; font-size: 14px; }
.card { background: white; padding: 36px; border: 1px solid #dfe7ef; border-radius: 20px;
  box-shadow: 0 16px 48px #172b4309; }
h2 { font-size: 24px; margin: 0 0 8px; letter-spacing: -.02em; }
.hint { color: #526277; font-size: 14px; line-height: 1.6; }
label { display: block; font-size: 14px; font-weight: 650; margin: 24px 0 8px; }
input:not([type=hidden]) { display: block; width: 100%; font: inherit; padding: 13px 14px;
  border: 1px solid #bac8d8; border-radius: 9px; background: #fff; color: #172b43; }
input:focus-visible, button:focus-visible { outline: 3px solid #99d5ce; outline-offset: 3px; }
button { width: 100%; margin-top: 28px; padding: 14px; border: none; border-radius: 9px;
  background: #0f766e; color: white; font: inherit; font-weight: 700; cursor: pointer; }
button:hover { background: #115e59; }
.error { border: 1px solid #f4b4b4; border-radius: 9px; background: #fff4f4; padding: 12px;
  color: #9b1c1c; font-size: 14px; line-height: 1.5; }
.help { border-top: 1px solid #e7edf3; margin-top: 24px; padding-top: 16px; }
footer { color: #64748b; font-size: 12px; margin-top: 48px; }
@media (max-width: 760px) { main { padding: 28px 20px; } .layout { grid-template-columns: 1fr;
  gap: 24px; margin-top: 36px; } .card { padding: 24px; } footer { margin-top: 24px; } }
"""
