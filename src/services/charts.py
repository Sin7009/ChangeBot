import io
import matplotlib
# Указываем, что у нас нет дисплея. Это обязательно для сервера.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
from typing import Optional

def generate_chart(pair: str, period: str = "1mo") -> Optional[io.BytesIO]:
    """
    Generates a line chart for the given currency pair (e.g., 'RUB=X' for USD/RUB).
    Returns a BytesIO object containing the image.
    """
    # Fetch data
    try:
        ticker = yf.Ticker(pair)
        hist = ticker.history(period=period)

        if hist.empty:
            return None

        # Extract Close prices
        dates = hist.index
        values = hist['Close']

        # Setup plot style
        # Sberbank colors:
        # Main line: RGB(0, 112, 59) -> #00703B
        # Background: RGB(250, 250, 241) -> #FAFaf1
        # Grid: RGB(227, 230, 161) -> #E3E6A1

        c_line = '#00703B'
        c_bg = '#FAFAF1'
        c_grid = '#E3E6A1'

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(c_bg)
        ax.set_facecolor(c_bg)

        # Plot line
        ax.plot(dates, values, color=c_line, linewidth=2)

        # Minimalist style: remove top/right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color(c_grid)

        # Grid
        ax.grid(True, color=c_grid, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)

        # Format X-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        # Rotate dates if needed, but for 1mo it usually fits

        # Title
        symbol_map = {"RUB=X": "USD/RUB", "EURRUB=X": "EUR/RUB"}
        title_text = symbol_map.get(pair, pair)
        ax.set_title(f"{title_text} ({period})", color='#333333', fontweight='bold')

        # Save to buffer
        buf = io.BytesIO()
        # Use fig.savefig instead of plt.savefig for thread safety
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor=c_bg)
        buf.seek(0)
        plt.close(fig)

        return buf

    except Exception as e:
        print(f"Error generating chart for {pair}: {e}")
        return None
