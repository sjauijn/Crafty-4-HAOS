import uuid
import json
import shlex
import logging
import subprocess
from pathlib import PurePosixPath, Path

from app.classes.models.server_permissions import (
    EnumPermissionsServer,
)
from app.classes.big_bucket.hytale import HytaleJSON

logger = logging.getLogger(__name__)

HYTALE_0UTPUT_NAME = "hytale.zip"


class HytaleInstaller:
    def __init__(self, helper, file_helper, websocket_manager):
        self.helper = helper
        self.file_helper = file_helper
        self.websocket_manager = websocket_manager

    def install(self, bb_cache: dict, server_path: Path, new_id: uuid.UUID):
        try:
            self.hytale_json = HytaleJSON(bb_cache)
            unix_exe = PurePosixPath(self.hytale_json.linux_installer_url).name
            windows_exe = PurePosixPath(self.hytale_json.windows_installer_url).name
            install_command = self._get_install_command(
                server_path, windows_exe, unix_exe
            )
        except KeyError:
            logger.exception("Failed to create Hytale server with keyerror")
            return
        self._download_component(server_path, unix_exe, windows_exe)
        self._run_installer(install_command, server_path, new_id)
        self._setup_server(bb_cache, server_path, new_id)

    def _get_install_command(
        self, server_path: Path, windows_exe: str, unix_exe: str
    ) -> str:
        """Creates hytale install command based on system type

        Args:
            server_path (Path): path to server directory
            windows_exe (str): windows executable name
            unix_exe (str): unix executable name

        Returns:
            str: installation command string
        """
        if self.helper.is_os_windows():
            return (
                f"{server_path}/{windows_exe} "
                f"{self.hytale_json.commands.download_path_command} "
                f"{HYTALE_0UTPUT_NAME}"
            )
        return (
            f"./{unix_exe} "
            f"{self.hytale_json.commands.download_path_command} {HYTALE_0UTPUT_NAME}"
        )

    def _download_component(self, server_path: Path, unix_exe, windows_exe):
        if self.helper.is_os_windows():
            self.file_helper.ssl_get_file(
                self.hytale_json.windows_installer_url, server_path, windows_exe
            )
        else:
            self.file_helper.ssl_get_file(
                self.hytale_json.linux_installer_url, server_path, unix_exe
            )
            # ssl_get_file writes the binary with mode 644 (no execute bit), so
            # _run_installer would fail with PermissionError when launching
            # "./<unix_exe>". Mark it executable, mirroring the bedrock path.
            Path(server_path, unix_exe).chmod(0o0744)

    def _run_installer(
        self, install_command: str, server_path: Path, new_id: uuid.UUID
    ):
        """Runs installer process for Hytale servers

        Args:
            install_command (str): startup command constructed in an earlier call
            server_path (Path): path to server directory
            new_id (uuid.UUID): server ID
        """
        install_command = shlex.split(install_command)
        process = subprocess.Popen(
            install_command,
            cwd=server_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        url_line = ""
        while process.poll() is None:
            line = process.stdout.readline().strip()
            if not line:
                continue

            line = line.strip()
            if len(self.websocket_manager().clients) > 0:
                self.websocket_manager().broadcast_page_params(
                    "/panel/server_detail",
                    {"id": new_id},
                    "vterm_new_line",
                    {"line": line + "<br />"},
                    required_permission=EnumPermissionsServer.TERMINAL,
                )
            if (
                line.startswith(self.hytale_json.parsing_lines.url_line_start)
                and url_line == ""
            ):
                url_line = line
                with open(
                    Path(server_path, "hytale_install_auth_url.txt"),
                    "w",
                    encoding="utf-8",
                ) as auth_file:
                    auth_file.write(url_line)
                self.websocket_manager().broadcast_to_server_users(
                    new_id,
                    "hytale_auth",
                    {"link": line, "server_id": new_id},
                )

    def _setup_server(self, bb_cache: dict, server_path: Path, new_id: uuid.UUID):
        """Unzips downloaded server archive.

        Args:
            bb_cache (dict): server repo cached data
            server_path (Path): filesystem location of the server data
            new_id (uuid.UUID): Crafty ID for the server
        """
        # Unzip downloaded archive.
        self.file_helper.unzip_file(
            Path(server_path, HYTALE_0UTPUT_NAME),
            server_path,
        )
        self._install_or_update_monitoring_plugins(bb_cache, new_id, server_path)

    def _install_or_update_monitoring_plugins(
        self, bb_cache: dict, server_id: uuid.UUID, server_path: str | Path
    ):
        """Downloads newest versions of Hytale monitoring plugins.

        Args:
            bb_cache (dict): server repo cached data
            server_id (uuid.UUID): Crafty ID for the server
            server_path (str | Path): filesystem location of the server data
        """
        try:
            hytale_json = HytaleJSON(bb_cache)
        except KeyError:
            logger.exception("Failed to download hytale plugins with keyerror")
            return
        logger.info("Installing Nitrado Webserver Plugin to server %s", server_id)
        # make sure our mods dir exists before doing anything
        # Download webserver plugin required for query plugin
        self.helper.ensure_dir_exists(Path(server_path, "mods"))
        self.file_helper.ssl_get_file(
            hytale_json.plugins.webserver_plugin_url,
            Path(server_path, "mods"),
            "nitrado-webserver.jar",
        )
        # Download query plugin
        logger.info("Installing Nitrado Query Plugin to server %s", server_id)
        self.file_helper.ssl_get_file(
            hytale_json.plugins.query_plugin_url,
            Path(server_path, "mods"),
            "nitrado-query.jar",
        )
        self._modify_permissions_json(server_path)

    def _modify_permissions_json(self, server_path: str | Path):
        """Checks if hytale specific permissions file exists...if it does not exist we
        modify permissions on the server to allow the Nitrado plugins to access player
        information

        Args:
            server_path (str | Path): filesystem location of the server data
        """
        # Make sure we do not overwrite user data
        if not self.helper.check_file_exists(
            str(Path(server_path, "permissions.json"))
        ):
            with open(
                Path(server_path, "permissions.json"), "w", encoding="utf-8"
            ) as perms_file:
                decoded = {
                    "groups": {
                        "ANONYMOUS": [
                            "nitrado.query.web.read.server",
                            "nitrado.query.web.read.universe",
                            "nitrado.query.web.read.players",
                        ]
                    }
                }
                perms_file.write(json.dumps(decoded, indent=4))
