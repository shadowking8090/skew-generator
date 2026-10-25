"""Colors shared by the theme and the sample data (no NiceGUI dependency)."""

PALETTE = dict(
    ink='#0F1B2D',        # header bar, reference line
    page='#F5F7FA',       # page background
    panel='#FFFFFF',      # plot and grid background
    text='#1B2735',       # primary text
    muted='#5B6B7F',      # axes, secondary text
    border='#E3E8EE',     # gridlines, card borders
    accent='#2F6FED',     # composite line and fill
    preview='#12A594',    # fallback color for a hover preview
    selected='#E8F0FE',   # selected grid row
    hover='#F0F4FA',      # hovered grid row
)

# One color per row, in row order. Chosen to sit alongside the blue accent and
# the navy ink without repeating either; add more here if you add more rows.
SERIES_COLORS = [
    '#12A594',   # teal
    '#7C5CFC',   # violet
    '#E8A33D',   # amber
    '#E5527A',   # rose
    '#84B84C',   # leaf green
    '#3FA7D6',   # sky
    '#B5651D',   # copper
    '#8A94A6',   # slate
]


def rgba(hex_color: str, alpha: float) -> str:
    """'#2F6FED', 0.15 -> 'rgba(47, 111, 237, 0.15)'"""
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'