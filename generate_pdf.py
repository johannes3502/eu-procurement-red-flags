"""Generate workbook PDF with proper layout."""
import markdown
import subprocess
import re
from pathlib import Path

md_path = Path("doc/submission/workbook.md")
img_path = Path("doc/data-model/mer_model.png")
out_path = Path("doc/submission/workbook.html")
pdf_path = Path("doc/submission/workbook.pdf")

md_text = md_path.read_text("utf-8")
html = markdown.markdown(md_text, extensions=["fenced_code", "tables"])

# Absolute image path for file:// rendering
img_abs = img_path.resolve().as_posix()
html = html.replace('src="../data-model/mer_model.png"', f'src="file:///{img_abs}"')

# Wrap MER heading + image together in landscape div
# Original HTML: <h2>ME/R Model</h2>\n<p><img ... /></p>
# Replace entire block with landscape-page div
html = re.sub(
    r'<h2>ME/R Model</h2>\s*<p>(<img[^>]+>)</p>',
    r'<div class="landscape-page"><h2 style="page-break-before:avoid;border:none">ME/R Model</h2><p>\1</p></div>',
    html,
    flags=re.DOTALL
)

css = """
<style>
  @page { margin: 2.5cm 2cm; size: A4; }
  @page landscape { size: A4 landscape; margin: 1.5cm; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }
  h1 { font-size: 18pt; color: #003366; }
  h2 { font-size: 14pt; color: #004080; border-bottom: 1px solid #ccc; padding-bottom: 3px; margin-top: 1.5em; }
  h3 { font-size: 12pt; color: #0059b3; }
  code { background: #f0f0f0; padding: 1px 3px; font-size: 9pt; }
  pre { background: #f5f5f5; padding: 8px; border-left: 3px solid #003366; font-size: 8pt; line-height: 1.3; white-space: pre-wrap; }
  table { border-collapse: collapse; width: 100%; font-size: 9pt; }
  th, td { border: 1px solid #999; padding: 4px 8px; }
  th { background: #e0e8f0; }
  .landscape-page { page: landscape; page-break-before: always; page-break-after: always; text-align: center; }
  .landscape-page h2 { border: none; }
  .landscape-page img { max-width: 100%; max-height: 85vh; height: auto; display: inline; }
  hr { border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }
  blockquote { border-left: 3px solid #ccc; margin: 1em 0; padding: 0.5em 1em; background: #f9f9f9; font-style: italic; }
</style>"""

full_html = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\">{css}</head><body>{html}</body></html>"
out_path.write_text(full_html, "utf-8")

# Debug: verify landscape-page is in the HTML
if 'landscape-page' in out_path.read_text("utf-8"):
    print(f"HTML: {out_path} ({out_path.stat().st_size/1024:.0f} KB) [OK] landscape-page")
else:
    print(f"HTML: {out_path} ({out_path.stat().st_size/1024:.0f} KB) [WARNING] NO landscape-page!")

edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
pdf_abs = pdf_path.resolve()
html_abs = out_path.resolve()

cmd = [edge, "--headless=new", "--no-pdf-header-footer",
       f"--print-to-pdf={pdf_abs}", f"file:///{html_abs}"]
subprocess.run(cmd, capture_output=True, text=True, timeout=30)
print(f"PDF: {pdf_path} ({pdf_path.stat().st_size/1024:.0f} KB)")

out_path.unlink()
