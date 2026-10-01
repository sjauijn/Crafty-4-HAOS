import logging

logger = logging.Logger(__name__)

LOG_ERROR = "Failed to capture object data from BigBucket data with error %s"


class HytaleCommands:
    def __init__(self, input_dict: dict[str, int | str | dict[str, int | str]]):
        try:
            self.version: int = input_dict["version"]
            self.download_latest_command: str = input_dict["download_latest_command"]
            self.download_path_command: str = input_dict["download_path_command"]
            # Repeat for all commands...
        except KeyError as why:
            # shape must have changed of json
            logger.exception(LOG_ERROR, why)
            raise


class HytaleParsingLines:
    def __init__(self, input_dict: dict[str, int | str]):
        try:
            self.version: int = input_dict["version"]
            self.url_line_start: str = input_dict["verify_url_line_start"]
            self.auth_code_line_start: str = input_dict["auth_code_line_start"]
        except KeyError as why:
            # shape must have changed of json
            logger.exception(LOG_ERROR, why)
            raise


class HytalePlugins:
    def __init__(self, input_dict: dict[str, int | str]):
        try:
            self.version: int = input_dict["version"]
            self.query_plugin_url: str = input_dict["query_plugin"]
            self.webserver_plugin_url: str = input_dict["webserver_plugin"]
            # Repeat for all plugins...
        except KeyError as why:
            # shape must have changed of json
            logger.exception(LOG_ERROR, why)
            raise


class HytaleJSON:
    def __init__(self, input_dict: dict[str, int | str | dict[str, int | str]]):
        try:
            self.version: int = input_dict["version"]
            self.linux_installer_url: str = input_dict["linux_installer"]
            self.linux_installer_hash: str = input_dict["linux_installer_hash"]
            self.windows_installer_url: str = input_dict["windows_installer"]
            self.commands: HytaleCommands = HytaleCommands(input_dict["commands"])
            self.parsing_lines: HytaleParsingLines = HytaleParsingLines(
                input_dict["parsing_lines"]
            )
            self.plugins: HytalePlugins = HytalePlugins(input_dict["plugins"])
        except KeyError as why:
            # shape must have changed of json
            logger.exception(LOG_ERROR, why)
            raise
