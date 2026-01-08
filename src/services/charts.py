import io
import logging
import time
import threading
import matplotlib
# Указываем, что у нас нет дисплея. Это обязательно для сервера.
matplotlib.use('Agg')
# Use Figure directly to avoid global state from pyplot
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.dates as mdates
import yfinance as yf
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

class ChartCache:
    """
    Thread-safe in-memory cache for generated chart images.
    Stores raw bytes to avoid stateful BytesIO issues.
    """
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[Tuple[str, str], Tuple[float, bytes]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(self, pair: str, period: str) -> Optional[bytes]:
        key = (pair, period)
        with self._lock:
            if key in self._cache:
                timestamp, data = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    logger.debug(f"Cache hit for chart {key}")
                    return data
                else:
                    logger.debug(f"Cache expired for chart {key}")
                    del self._cache[key]
        return None

    def set(self, pair: str, period: str, data: bytes):
        key = (pair, period)
        with self._lock:
            # Clean up old entries occasionally?
            # For now, simple dict is fine as volume is low.
            self._cache[key] = (time.time(), data)

# Global cache instance
_chart_cache = ChartCache(ttl_seconds=300)

def generate_chart(pair: str, period: str = "1mo") -> Optional[io.BytesIO]:
    """
    Generates a line chart for the given currency pair (e.g., 'RUB=X' for USD/RUB).
    Returns a BytesIO object containing the image.
    Uses in-memory caching to reduce Matplotlib overhead and API calls.
    """
    # Check cache first
    cached_bytes = _chart_cache.get(pair, period)
    if cached_bytes:
        return io.BytesIO(cached_bytes)

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

        # OPTIMIZATION: Use Figure directly instead of plt.subplots()
        # This avoids interacting with the global pyplot state machine,
        # which is safer for threaded environments and slightly faster (less overhead).
        fig = Figure(figsize=(10, 5))
        # Attach a canvas to the figure (required for saving)
        FigureCanvasAgg(fig)

        ax = fig.add_subplot(111)

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

        # OPTIMIZATION: Manually adjust margins instead of using bbox_inches='tight'.
        # bbox_inches='tight' requires a secondary render to calculate the bounding box,
        # which increases generation time by ~30-40%.
        # Since we have a fixed figure size and predictable content, we can set fixed margins.
        fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)

        # Save to buffer
        buf = io.BytesIO()
        # Removed bbox_inches='tight' for performance
        fig.savefig(buf, format='png', facecolor=c_bg)
        buf.seek(0)

        # No need to call plt.close(fig) as we didn't use pyplot

        # Store in cache
        image_bytes = buf.getvalue()
        _chart_cache.set(pair, period, image_bytes)

        return buf

    except Exception as e:
        logger.error(f"Error generating chart for {pair}: {e}")
        return None
