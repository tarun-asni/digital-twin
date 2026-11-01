import logging

from datetime import datetime, timezone


logger = logging.getLogger(__name__)

class TimeConverter:
    """
    Utility class for converting between UTC and local time,
    and formatting/parsing ISO 8601 date strings.
    """
    
    def utc_to_local(self, utc_date: datetime, naive: bool = False):
        """
        Convert UTC datetime to local aware datetime.
        Eg: 2025-11-24 17:59:26.155508+05:30
        """
        
        try:
            local_date = utc_date.astimezone()
            if naive:
                local_date = self._to_naive(local_date)
        except Exception as e:
            logger.error(f"Failed to convert UTC to local: {e}")
            return utc_date  # Fallback to original UTC date    
        return local_date


    def local_to_utc(self, local_date: datetime):
        """
        Convert local aware datetime to UTC datetime.
        Eg: 2025-11-24 12:29:26.155508+00:00
        """
        try:
            utc_date = local_date.astimezone(timezone.utc)
        except Exception as e:
            logger.error(f"Failed to convert local to UTC: {e}")
            return local_date  # Fallback to original local date
        
        return utc_date


    def to_iso_format(self, date_obj: datetime):
        """
        Convert datetime object to ISO 8601 formatted string.
        Eg: 2025-11-24T17:59:26.155508+05:30
        """
        try:
            return date_obj.isoformat()
        except Exception as e:
            logger.error(f"Failed to convert datetime to ISO format: {e}")
            return None


    def from_iso_format(self, iso_string: str, naive: bool = False):
        """
        Convert ISO 8601 formatted string to datetime object.
        Eg: 2025-11-24T17:59:26.155508+05:30
        """
        try:
            date_obj = datetime.fromisoformat(iso_string)
            if naive:
                date_obj = self._to_naive(date_obj)
            return date_obj
        except Exception as e:
            logger.error(f"Failed to convert ISO string to datetime: {e}")
            return None
        
    def _to_naive(self, date_obj: datetime):
        """
        Convert aware datetime to naive datetime (no timezone).
        Eg: 2025-11-24 17:59:26.155508
        """
        try:
            return date_obj.replace(tzinfo=None)
        except Exception as e:
            logger.error(f"Failed to convert to naive datetime: {e}")
            return date_obj  # Fallback to original date object


time_converter = TimeConverter()