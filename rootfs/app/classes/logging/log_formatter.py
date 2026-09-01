import logging
import logging.config
import json
from datetime import datetime


class JsonEncoderStrFallback(json.JSONEncoder):
    def default(self, o):
        try:
            return super().default(o)
        except TypeError as exc:
            if "not JSON serializable" in str(exc):
                return str(o)
            raise


class JsonEncoderDatetime(JsonEncoderStrFallback):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%dT%H:%M:%S%z")

        return super().default(o)


class JsonFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        """
        Override formatTime to customize the time format.
        """
        timestamp = datetime.fromtimestamp(record.created)
        if datefmt:
            # Use the specified date format
            return timestamp.strftime(datefmt)
        # Default date format: YYYY-MM-DD HH:MM:SS,mmm
        secs = int(record.msecs)
        return f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')},{secs:03d}"

    def format(self, record):
        log_data = {
            "level": record.levelname,
            "time": self.formatTime(record),
            "log_msg": record.getMessage(),
        }

        # Filter out standard log record attributes and include only custom ones
        custom_attrs = ["user_name", "user_id", "server_id", "source_ip"]
        extra_attrs = {
            key: value for key, value in record.__dict__.items() if key in custom_attrs
        }

        # Merge extra attributes with log data
        log_data.update(extra_attrs)
        return json.dumps(log_data)
