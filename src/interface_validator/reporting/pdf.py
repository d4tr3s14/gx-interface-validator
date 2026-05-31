"""
Conversión HTML -> PDF con backend automático.

El PDF se genera a partir del MISMO HTML que el informe de usuario, de modo que
contenga exactamente la misma información. Se intentan, en orden:

  1. WeasyPrint        (ideal en Linux/CI; en Windows requiere librerías GTK)
  2. Chromium headless (Edge o Chrome; renderizado idéntico al navegador)

Devuelve (ok, backend_o_error).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

# Rutas habituales de navegadores basados en Chromium en Windows.
_CHROMIUM_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _find_chromium() -> str | None:
    for name in ("msedge", "chrome", "chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    for path in _CHROMIUM_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def _try_weasyprint(html: str, out_path: Path) -> tuple[bool, str]:
    try:
        from weasyprint import HTML  # noqa: PLC0415

        HTML(string=html).write_pdf(str(out_path))
        return True, "weasyprint"
    except Exception as exc:  # noqa: BLE001
        return False, f"weasyprint: {exc}"


def _try_chromium(html: str, out_path: Path) -> tuple[bool, str]:
    browser = _find_chromium()
    if not browser:
        return False, "chromium: no se encontró Edge/Chrome"

    # Chromium imprime desde un archivo local; usamos uno temporal.
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "report.html"
        html_path.write_text(html, encoding="utf-8")
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out_path}",
            html_path.as_uri(),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except subprocess.CalledProcessError:
            # Algunas versiones no soportan --headless=new; reintentar con --headless
            cmd[1] = "--headless"
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)

    if out_path.exists():
        return True, f"chromium ({Path(browser).stem})"
    return False, "chromium: no se generó el PDF"


def html_to_pdf(html: str, out_path: str | Path) -> tuple[bool, str]:
    """Convierte HTML a PDF probando los backends disponibles."""
    out_path = Path(out_path)
    errors = []
    for backend in (_try_weasyprint, _try_chromium):
        ok, info = backend(html, out_path)
        if ok:
            return True, info
        errors.append(info)
    return False, " | ".join(errors)
