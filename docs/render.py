"""Render the deck to PDF. WeasyPrint defaults to latin-1 when the document
carries no charset declaration, which mangles every Greek letter and em dash —
so the encoding is pinned explicitly here."""
from weasyprint import HTML
HTML(filename="deck.html", encoding="utf-8").write_pdf("snowstorm_deck.pdf")
