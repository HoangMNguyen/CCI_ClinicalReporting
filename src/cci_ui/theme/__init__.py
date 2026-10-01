"""Colors, sizes, fonts, and the stylesheet shared by every CCI tool.

- :mod:`~cci_ui.theme.tokens`: the design values (pure Python, no Qt).
- :mod:`~cci_ui.theme.palette` and :mod:`~cci_ui.theme.qss`: Qt palette and
  stylesheet generated from the tokens.
- :mod:`~cci_ui.theme.fonts`: the bundled Inter font.
- :mod:`~cci_ui.theme.glyphs`: draws the icons in token colors, and writes
  the small images the stylesheet needs (combo arrows, the checkbox tick).
- :mod:`~cci_ui.theme.manager`: applies the theme and remembers the choice.

Nothing is imported here so that ``cci_ui.theme.tokens`` stays importable
without Qt.
"""
