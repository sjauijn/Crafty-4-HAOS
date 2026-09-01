from abc import ABC, abstractmethod
import logging
import datetime
import time
import requests
from jinja2 import BaseLoader
from jinja2.sandbox import ImmutableSandboxedEnvironment

from app.classes.helpers.helpers import Helpers

logger = logging.getLogger(__name__)
helper = Helpers()


class CraftyRestrictedEnvironment(ImmutableSandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, value):
        if attr.startswith("_"):
            return False
        return super().is_safe_attribute(obj, attr, value)


class WebhookProvider(ABC):
    """
    Base class for all webhook providers.

    Provides a common interface for all webhook provider implementations,
    ensuring that each provider will have a send method.
    """

    def __init__(self):
        self.jinja_env = CraftyRestrictedEnvironment(
            loader=BaseLoader(),
            autoescape=True,
        )

    WEBHOOK_USERNAME = "Crafty Webhooks"
    WEBHOOK_PFP_URL = (
        "https://gitlab.com/crafty-controller/crafty-4/-"
        + "/raw/master/app/frontend/static/assets/images/"
        + "Crafty_4-0.png"
    )
    CRAFTY_VERSION = helper.get_version_string()

    def _send_request(self, url, payload, headers=None):
        """Send a POST request to the given URL with the provided payload."""
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return "Dispatch successful"
        except requests.RequestException as error:
            logger.exception(error)
            raise RuntimeError(f"Failed to dispatch notification: {error}") from error

    def render_template(self, template_str, context):
        """
        Renders a Jinja2 template with the provided context.

        Args:
            template_str (str): The Jinja2 template string.
            context (dict): A dictionary containing all the variables needed for
            rendering the template.

        Returns:
            str: The rendered message.
        """
        try:
            template = self.jinja_env.from_string(template_str)
            return template.render(context)
        except Exception as error:
            logger.exception(f"Error rendering Jinja2 template: {error}")
            raise

    def add_time_variables(self, event_data):
        """
        Adds various time format variables to the event_data dictionary.

        Adds the following time-related variables to event_data:
        - time_iso: ISO 8601 formatted datetime (UTC)
        - time_unix: UNIX timestamp (seconds since epoch)
        - time_day: Day of month (1-31)
        - time_month: Month (1-12)
        - time_year: Full year (e.g., 2025)
        - time_formatted: Human-readable format (YYYY-MM-DD HH:MM:SS UTC)

        Args:
            event_data (dict): A dictionary containing event information.

        Returns:
            dict: The event_data dictionary with time variables added.
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        unix_timestamp = int(time.time())

        event_data["time_iso"] = now_utc.isoformat().replace("+00:00", "Z")
        event_data["time_unix"] = unix_timestamp
        event_data["time_day"] = now_utc.day
        event_data["time_month"] = now_utc.month
        event_data["time_year"] = now_utc.year
        event_data["time_formatted"] = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        return event_data

    @abstractmethod
    def send(self, server_name, title, url, message_template, event_data, **kwargs):
        """Abstract method that derived classes will implement for sending webhooks."""
