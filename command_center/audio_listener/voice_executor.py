import logging
from datetime import datetime, timedelta
import pytz
from cc_alerts.models import Alert

logger = logging.getLogger(__name__)


class VoiceExecutor:
    def get_alerts_by_date(self, date_str, timezone_str='UTC'):
        try:
            # Get the timezone object from the string
            user_timezone = pytz.timezone(timezone_str)

            # Create a naive datetime object from the date string
            naive_start_of_day = datetime.strptime(date_str, "%Y-%m-%d")

            # Localize the naive datetime to the user's timezone
            start_of_day = user_timezone.localize(naive_start_of_day)

            # Calculate the end of the day in the user's timezone
            end_of_day = start_of_day + timedelta(days=1)

            # Convert the start and end of the day to UTC
            utc_start_of_day = start_of_day.astimezone(pytz.utc)
            utc_end_of_day = end_of_day.astimezone(pytz.utc)

            # Query alerts by date in UTC
            alerts = Alert.objects.filter(
                start_time__gte=utc_start_of_day,
                start_time__lt=utc_end_of_day
            ).order_by('start_time')

            if alerts.exists():
                return alerts
            else:
                logger.error(f"No alerts found on {date_str} in timezone {timezone_str}.")
                return None
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return None

    def get_alerts_by_severity(self, severity):
        try:
            alerts = Alert.objects.filter(severity=severity).order_by('-start_time')
            if not alerts.exists():
                logger.error(f"No alerts found with severity '{severity}'.")
                return None
            return alerts
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return None

    def handle_llm_result(self, llm_result, timezone='UTC'):
        if llm_result:
            logger.info(f"🤖 LLM Result: {llm_result}")
            if llm_result.get("action") == "get_alerts_by_date":
                date = llm_result.get("date")
                alerts = self.get_alerts_by_date(date, timezone)
                return alerts if alerts else None
            elif llm_result.get("action") == "get_alerts_by_severity":
                severity = llm_result.get("severity")
                alerts = self.get_alerts_by_severity(severity)
                return alerts if alerts else None
            elif llm_result.get("action") == "no_proper_response":
                return None
        else:
            logger.error("🚫 No response from LLM.")
            return None