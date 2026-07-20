"""Generación de PDF a partir del mismo HTML usado por /preview.

Usa Playwright + Chromium headless (page.pdf()) en vez de WeasyPrint:
WeasyPrint requiere el runtime nativo GTK3/Pango/Cairo, que en Windows
implica instalar MSYS2 aparte (mismo tipo de fricción que tuvimos con
Graphviz, pero sin una vía sin permisos de administrador). Playwright
en cambio descarga su propio Chromium autocontenido dentro del entorno
del proyecto — cero dependencias nativas adicionales del sistema
operativo (ver prueba de viabilidad de esta sesión).

Requiere haber corrido una vez `playwright install chromium` en este
entorno (además de `pip install playwright`) — no alcanza con el
paquete Python solo.
"""

from playwright.sync_api import sync_playwright


def html_a_pdf_bytes(html: str) -> bytes:
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page()
        pagina.set_content(html, wait_until="load")
        pdf_bytes = pagina.pdf(format="A4", print_background=True)
        navegador.close()
        return pdf_bytes
