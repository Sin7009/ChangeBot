import io
import logging
import time
import threading
import matplotlib
# Указываем, что у нас нет дисплея. Это обязательно для сервера.
matplotlib.use('Agg')
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import yfinance as yf
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)

# Cache structure: (pair, period) -> (timestamp, png_bytes)
_CHART_CACHE: Dict[Tuple[str, str], Tuple[float, bytes]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 300  # 5 minutes

def generate_chart(pair: str, period: str = "1mo") -> Optional[io.BytesIO]:
    """
    Generates a line chart for the given currency pair (e.g., 'RUB=X' for USD/RUB).
    Returns a BytesIO object containing the image.
    Uses in-memory caching to improve performance.
    """
    cache_key = (pair, period)
    current_time = time.time()

    # Check cache
    with _CACHE_LOCK:
        if cache_key in _CHART_CACHE:
            ts, data = _CHART_CACHE[cache_key]
            if current_time - ts < _CACHE_TTL:
                # logger.info(f"Chart cache hit for {pair}")
                return io.BytesIO(data)
            else:
                # logger.info(f"Chart cache expired for {pair}")
                del _CHART_CACHE[cache_key]

    # Fetch data
    try:
        ticker = yf.Ticker(pair)
        # yfinance history call is synchronous and network-bound
        hist = ticker.history(period=period)

        if hist.empty:
            return None

        # Extract Close prices
        dates = hist.index
        values = hist['Close']

        # Setup plot style
        c_line = '#00703B'
        c_bg = '#FAFAF1'
        c_grid = '#E3E6A1'

        # Optimization: Use Figure directly instead of pyplot state-machine
        # This is thread-safe and avoids global state overhead
        fig = Figure(figsize=(10, 5))
        fig.patch.set_facecolor(c_bg)

        ax = fig.subplots()
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

        # Title
        symbol_map = {"RUB=X": "USD/RUB", "EURRUB=X": "EUR/RUB"}
        title_text = symbol_map.get(pair, pair)
        ax.set_title(f"{title_text} ({period})", color='#333333', fontweight='bold')

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor=c_bg)

        # We don't need plt.close(fig) because we didn't use pyplot to create it.
        # The figure will be garbage collected.

        png_bytes = buf.getvalue()

        # Update cache
        with _CACHE_LOCK:
            _CHART_CACHE[cache_key] = (current_time, png_bytes)

        buf.seek(0)
        return buf

    except Exception as e:
        logger.error(f"Error generating chart for {pair}: {e}")
        return None
