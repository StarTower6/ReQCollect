"""Current time tool."""

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from loguru import logger


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """Get the current date and time.

    Use this when you need to know the current time, date, or day of week.

    Args:
        timezone: Timezone string, defaults to Asia/Shanghai

    Returns:
        Formatted datetime string
    """
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return now.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception as e:
        logger.error(f"Time tool failed: {e}")
        return f"Failed to get time: {str(e)}"
