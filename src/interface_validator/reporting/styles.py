"""Tema CSS moderno compartido por los informes (ejecutivo y consolidado)."""

REPORT_CSS = r"""
:root{
  --bg:#f4f6fb; --card:#ffffff; --ink:#1e293b; --muted:#64748b;
  --primary:#3b5bdb; --primary-dark:#1f3c88;
  --ok:#15a34a; --ok-bg:#dcfce7; --bad:#dc2626; --bad-bg:#fee2e2;
  --warn:#d97706; --warn-bg:#fef3c7; --border:#e6ebf2;
}
*{ box-sizing:border-box; }
body{ font-family:'Segoe UI', system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif;
  background:var(--bg); color:var(--ink); margin:0; font-size:10.5pt; line-height:1.5;
  -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.container{ max-width:210mm; margin:0 auto; padding:22px; }

/* Cabecera */
.header{ background:linear-gradient(135deg,#1f3c88 0%,#3b5bdb 60%,#5b7cf0 100%); color:#fff;
  border-radius:16px; padding:24px 26px; box-shadow:0 8px 22px rgba(31,60,136,.22); }
.header .org{ font-size:9.5pt; opacity:.85; letter-spacing:.6px; text-transform:uppercase; }
.header h1{ font-size:19pt; font-weight:700; margin:6px 0 2px; letter-spacing:.3px; }
.header .sub{ font-size:9.5pt; opacity:.9; }
.chip{ display:inline-block; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.35);
  padding:2px 10px; border-radius:999px; font-size:8.5pt; margin-left:6px; }

/* Tarjetas / KPIs */
.cards{ display:flex; gap:14px; flex-wrap:wrap; margin:18px 0; align-items:stretch; }
.card{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px 18px;
  box-shadow:0 1px 3px rgba(15,23,42,.05); }
.kpi{ flex:1; min-width:140px; display:flex; flex-direction:column; gap:2px; }
.kpi .value{ font-size:23pt; font-weight:700; color:var(--primary-dark); line-height:1.05; }
.kpi .label{ color:var(--muted); font-size:9pt; }
.hero{ display:flex; gap:16px; align-items:center; margin:18px 0; flex-wrap:wrap; }

/* Donut (conic-gradient) */
.donut{ position:relative; width:104px; height:104px; border-radius:50%; flex:0 0 auto;
  background:conic-gradient(var(--dcol,#15a34a) calc(var(--pct,0)*1%), #eef2f7 0); }
.donut .hole{ position:absolute; inset:13px; background:var(--card); border-radius:50%;
  display:flex; flex-direction:column; align-items:center; justify-content:center; }
.donut .hole b{ font-size:16pt; color:var(--ink); }
.donut .hole small{ color:var(--muted); font-size:7.5pt; }

/* Títulos de sección */
.section-title{ font-size:12.5pt; font-weight:700; color:var(--primary-dark); margin:26px 0 10px;
  display:flex; align-items:center; gap:9px; }
.section-title::before{ content:''; width:5px; height:18px; background:var(--primary); border-radius:3px; }

/* Tablas */
table{ width:100%; border-collapse:separate; border-spacing:0; font-size:9.5pt; background:var(--card);
  border:1px solid var(--border); border-radius:12px; overflow:hidden; margin:6px 0 16px; }
th{ background:#eef2f9; color:#334155; text-align:left; padding:9px 11px; font-weight:600;
  border-bottom:1px solid var(--border); font-size:8.8pt; letter-spacing:.3px; text-transform:uppercase; }
td{ padding:8px 11px; border-bottom:1px solid #eef2f7; vertical-align:top; }
tr:last-child td{ border-bottom:none; }
tbody tr:nth-child(even) td{ background:#fafbfe; }
.center{ text-align:center; }

/* Pills / estados */
.pill{ display:inline-block; padding:3px 12px; border-radius:999px; font-weight:700; font-size:8.5pt; }
.pill-ok{ color:var(--ok); background:var(--ok-bg); }
.pill-bad{ color:var(--bad); background:var(--bad-bg); }

/* Barras */
.bar{ background:#eef2f7; border-radius:999px; height:9px; overflow:hidden; display:flex; min-width:120px; }
.bar .seg-ok{ background:var(--ok); height:100%; }
.bar .seg-bad{ background:var(--bad); height:100%; }
.bar-row{ display:flex; align-items:center; gap:12px; margin:7px 0; font-size:9.5pt; }
.bar-label{ width:120px; font-weight:600; color:#334155; }
.bar-count{ width:96px; text-align:right; color:var(--muted); font-size:8.8pt; }

.found{ font-family:'Cascadia Code', Consolas, monospace; color:var(--bad); font-size:8.5pt; word-break:break-word; }
.muted{ color:var(--muted); font-size:8.5pt; }
.ok-text{ color:var(--ok); font-weight:600; }
.note{ background:#f0f9ff; border:1px solid #bae6fd; border-radius:10px; padding:9px 13px; font-size:9pt; color:#075985; }
.linkbar{ background:#eef2ff; border:1px solid #c7d2fe; border-radius:12px; padding:12px 16px; font-size:9.5pt; }
.linkbar a{ color:var(--primary-dark); font-weight:600; text-decoration:none; }
.metastrip{ display:flex; gap:10px; flex-wrap:wrap; margin:14px 0; }
.metastrip .m{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:8px 12px; font-size:8.8pt; }
.metastrip .m b{ display:block; color:var(--muted); font-weight:600; font-size:7.8pt; text-transform:uppercase; letter-spacing:.4px; }
@page{ size:A4; margin:1.4cm; @bottom-right{ content:counter(page) " / " counter(pages); font-size:8.5pt; color:#94a3b8; } }
"""
