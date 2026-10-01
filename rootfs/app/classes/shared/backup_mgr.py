import datetime
import io
import json
import logging
import os
import shutil
import time
from pathlib import Path

# TZLocal is set as a hidden import on win pipeline
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tzlocal import get_localzone

from app.classes.helpers.cryptography_helper import CryptoHelper
from app.classes.helpers.file_helpers import FileHelpers
from app.classes.helpers.helpers import Helpers
from app.classes.models.management import HelpersManagement
from app.classes.models.server_permissions import PermissionsServers
from app.classes.models.users import HelperUsers
from app.classes.shared.console import Console
from app.classes.shared.server import ServerInstance
from app.classes.shared.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

backup_validation_exception = Exception("Unable to validate requested backup file.")


class BackupManager:
    SNAPSHOT_BACKUP_DATE_FORMAT_STRING = "%Y-%m-%d-%H-%M-%S"
    SNAPSHOT_SUFFIX = ".manifest"
    ARCHIVE_SUFFIX = ".zip"

    def __init__(self, helper, file_helper, management_helper):
        self.helper = helper
        self.file_helper = file_helper
        self.management_helper = management_helper
        try:
            self.tz = get_localzone()
        except ZoneInfoNotFoundError as e:
            logger.exception(
                "Could not capture time zone from system. Falling back to Europe/London"
                f" error: {e}"
            )
            self.tz = ZoneInfo("Europe/London")

    def broadcast_rejected_restore(self, backup_config, server) -> None:
        """
        Sends rejection message if a backup restore has been rejected.

        Args:
            backup_config: The backup configuration for the rejected restore
            server: Server object.

        Returns: None

        """
        logger.info(
            f"Rejecting backup restore for server {server.name} (ID {server.server_id})"
            f" Backup ID: {backup_config['backup_id']}"
        )
        server_users = PermissionsServers.get_server_user_list(server.server_id)
        for user in server_users:
            WebSocketManager().broadcast_user(
                user,
                "send_error",
                self.helper.translation.translate(
                    "notify", "restoreFailed", HelperUsers.get_user_lang_by_id(user)
                ),
            )

    def restore_starter(  # pylint: disable=too-many-positional-arguments
        self, backup_config, backup_location: Path, svr_obj, in_place
    ):
        """Validates that a restore is correct and without traversal.
        Assumes backup_location has already been validated for traversal.

        Args:
            backup_config: The backup configuration for this backup.
            backup_location: Full path to the backup file.
            svr_obj: The server object.
            in_place: Should the backup restore in place?
        """
        logger.debug("Starting backup restore validation")

        # Backup file is only expected to be `datetime.zip` or `datetime.manifest`.
        # We can do some intensive validation of this value by ensuring that the
        # filename can actually resolve to a datetime. We will reject it if not.
        backup_location = Path(backup_location)
        backup_file = backup_location.name
        backup_file_parts = backup_file.split(".")
        if len(backup_file_parts) != 2:
            logger.error(
                "backup file given to restore is not of the correct format. Possible "
                "suspicious activity."
            )
            logger.error(
                f"The filename we were given to restore was called `{backup_file}`, "
                f"rejected because the split length was incorrect"
            )

            self.broadcast_rejected_restore(backup_config, svr_obj)
            return

        allowed_extensions = ["zip", "manifest"]
        if backup_file_parts[1] not in allowed_extensions:
            logger.error(
                f"Extension of given backup file to restore is not in allowed extension"
                f" types. Possible suspicious activity. Got {backup_file}"
            )

            self.broadcast_rejected_restore(backup_config, svr_obj)
            return

        # We use a different timestamp format between snapshot backups and zip files.
        # This is very funny
        if backup_config["backup_type"] == "zip_vault":
            timestamp_format = "%Y-%m-%d_%H-%M-%S"
        else:
            timestamp_format = "%Y-%m-%d-%H-%M-%S"

        try:
            _ = datetime.datetime.strptime(backup_file_parts[0], timestamp_format)
        except ValueError as why:
            # The given name of the backup file does not match what Crafty would write.
            # This must be something we need to reject.
            logger.exception(
                f"Unable to parse a given backup filename with error {why}"
            )

            self.broadcast_rejected_restore(backup_config, svr_obj)
            return

        logger.info("Starting a restore after validation")
        self.valid_restore_starter(
            backup_config, backup_location, backup_file, svr_obj, in_place
        )

    def valid_restore_starter(  # pylint: disable=too-many-positional-arguments
        self, backup_config, backup_location: Path, backup_file, svr_obj, in_place
    ):
        """Starts a restore after the restore attempt has been validated.
        This function assumes that the inputs are trusted and validated for traversal.
        Ensure that all inputs are correct.

        Args:
            backup_config: The backup configuration for this backup.
            backup_location: Path to the backup_location.
            backup_file: File to restore, zip or snapshot manifest.
            svr_obj: The server object.
            in_place: Should the backup restore in place?
        """
        server_path = svr_obj.settings["path"]
        error = False
        if svr_obj.check_running():
            svr_obj.stop_server()

        if backup_config["backup_type"] != "zip_vault":
            logger.debug("Starting a snapshot backup restore")
            self.snapshot_restore(backup_config, backup_file, svr_obj)
        else:
            error = self.zip_vault_restore(server_path, backup_location, in_place)
        server_users = PermissionsServers.get_server_user_list(svr_obj.server_id)
        time.sleep(3)
        if error:
            for user in server_users:
                WebSocketManager().broadcast_user(
                    user,
                    "send_error",
                    self.helper.translation.translate(
                        "notify", "restoreFailed", HelperUsers.get_user_lang_by_id(user)
                    ),
                )
        else:
            for user in server_users:
                WebSocketManager().broadcast_user(
                    user,
                    "notification",
                    self.helper.translation.translate(
                        "notify",
                        "restoreSuccess",
                        HelperUsers.get_user_lang_by_id(user),
                    ),
                )

    @staticmethod
    def validate_backup_location(
        server_inst: ServerInstance, backup_config: dict
    ) -> bool:
        """Check backup location is not within backup target.

        Args:
            server_inst (ServerInstance): server object the backup is called on
            backup_config (dict): target backup config

        Returns:
             backup_valid (bool): true is backup location is valid
        """
        server_path = Path(server_inst.settings["path"]).resolve()
        backup_target = Path(backup_config["backup_location"]).resolve()
        # Preventing server path from being a parent of backup path
        if server_path in backup_target.parents:
            return False
        if server_path == backup_target:
            return False
        return True

    def backup_starter(self, backup_config, server) -> tuple:
        """Notify users of backup starting, and start the backup.

        Args:
            backup_config (_type_): _description_
            server (_type_): Server object to backup
        """

        # Notify users of backup starting
        logger.info(f"Starting server {server.name} (ID {server.server_id}) backup")
        server_users = PermissionsServers.get_server_user_list(server.server_id)
        # Alert the start of the backup to the authorized users.
        for user in server_users:
            WebSocketManager().broadcast_user(
                user,
                "notification",
                self.helper.translation.translate(
                    "notify", "backupStarted", HelperUsers.get_user_lang_by_id(user)
                ).format(server.name),
            )
        time.sleep(3)
        size = False
        if not self.validate_backup_location(server, backup_config):
            self.fail_backup(
                ValueError(
                    "Recursive backup target: backup location can not be within "
                    "directory that is being backed up"
                ),
                backup_config,
                server,
            )
            return (False, "error")
        # Start the backup
        if backup_config.get("backup_type", "zip_vault") == "zip_vault":
            backup_file_name = self.zip_vault(backup_config, server)
            if (
                backup_file_name
                and Path(backup_file_name).suffix != self.ARCHIVE_SUFFIX
            ):
                backup_file_name += self.ARCHIVE_SUFFIX
            if backup_file_name:
                size = (
                    Path(
                        backup_config["backup_location"],
                        backup_config["backup_id"],
                        backup_file_name,
                    )
                    .stat()
                    .st_size
                )
        else:
            backup_file_name = self.snapshot_backup(backup_config, server)
            if (
                backup_file_name
                and Path(backup_file_name).suffix != self.SNAPSHOT_SUFFIX
            ):
                backup_file_name += self.SNAPSHOT_SUFFIX
        if backup_file_name:
            return (backup_file_name, size)
        return (False, "error")

    def zip_vault(self, backup_config, server) -> str | bool:
        # Adjust the location to include the backup ID for destination.
        backup_location = os.path.join(
            backup_config["backup_location"], backup_config["backup_id"]
        )
        # Check if the backup location even exists.
        if not backup_location:
            Console.critical("No backup path found. Canceling")
            return False

        self.helper.ensure_dir_exists(backup_location)

        try:
            backup_filename = f"{backup_location}/" f"""{
                    datetime.datetime.now()
                    .astimezone(self.tz)
                    .strftime("%Y-%m-%d_%H-%M-%S")
                }"""
            logger.info(
                f"Creating backup of server {server.name}"
                f" (ID#{server.server_id}, path={server.settings['path']}) "
                f"at '{backup_filename}'"
            )
            excluded_dirs = HelpersManagement.get_excluded_backup_dirs(
                backup_config["backup_id"]
            )
            server_dir = Helpers.get_os_understandable_path(server.settings["path"])

            self.file_helper.make_backup(
                Helpers.get_os_understandable_path(backup_filename),
                server_dir,
                excluded_dirs,
                server.server_id,
                backup_config["backup_id"],
                backup_config["backup_name"],
                backup_config["compress"],
            )

            self.remove_old_backups(backup_config, server)

            logger.info(f"Backup of server: {server.name} completed")
            results = {
                "percent": 100,
                "total_files": 0,
                "current_file": 0,
                "backup_id": backup_config["backup_id"],
            }
            if len(WebSocketManager().clients) > 0:
                WebSocketManager().broadcast_page_params(
                    "/panel/server_detail",
                    {"id": str(server.server_id)},
                    "backup_status",
                    results,
                )
            server_users = PermissionsServers.get_server_user_list(server.server_id)
            for user in server_users:
                WebSocketManager().broadcast_user(
                    user,
                    "notification",
                    self.helper.translation.translate(
                        "notify",
                        "backupComplete",
                        HelperUsers.get_user_lang_by_id(user),
                    ).format(server.name),
                )
            # pause to let people read message.
            HelpersManagement.update_backup_config(
                backup_config["backup_id"],
                {"status": json.dumps({"status": "Standby", "message": ""})},
            )
            time.sleep(5)
            return Path(backup_filename).name
        except Exception as e:
            self.fail_backup(e, backup_config, server)
            return False

    @staticmethod
    def fail_backup(why: Exception, backup_config: dict, server) -> None:
        """
        Fails the backup if an error is encountered during the backup.

        Args:
            why: Exception raised to fail backup.
            backup_config: Backup config dict
            server: Server object.

        Returns: None

        """
        logger.exception(
            f"Failed to create backup of server {server.name} (ID {server.server_id})"
        )
        results: dict = {
            "percent": 100,
            "total_files": 0,
            "current_file": 0,
            "backup_id": backup_config["backup_id"],
        }
        if len(WebSocketManager().clients) > 0:
            WebSocketManager().broadcast_page_params(
                "/panel/server_detail",
                {"id": str(server.server_id)},
                "backup_status",
                results,
            )

        HelpersManagement.update_backup_config(
            backup_config["backup_id"],
            {"status": json.dumps({"status": "Failed", "message": f"{why}"})},
        )

    def list_backups(self, backup_config: dict, server_id) -> list:
        if not backup_config:
            logger.info(
                f"Error putting backup file list for server with ID: {server_id}"
            )
            return []
        backup_location = os.path.join(
            backup_config["backup_location"],
            backup_config["backup_id"],
        )
        if backup_config["backup_type"] == "snapshot":
            backup_location = os.path.join(
                backup_config["backup_location"], "snapshot_backups", "manifests"
            )
        if not Helpers.check_path_exists(
            Helpers.get_os_understandable_path(backup_location)
        ):
            return []
        files = Helpers.get_human_readable_files_sizes(
            Helpers.list_dir_by_date(
                Helpers.get_os_understandable_path(backup_location)
            )
        )
        if backup_config["backup_type"] == "snapshot":
            return [
                {
                    "path": os.path.relpath(
                        f["path"],
                        start=Helpers.get_os_understandable_path(backup_location),
                    ),
                    "size": "",
                }
                for f in files
                if f["path"].endswith(self.SNAPSHOT_SUFFIX)
            ]
        return [
            {
                "path": os.path.relpath(
                    f["path"],
                    start=Helpers.get_os_understandable_path(backup_location),
                ),
                "size": f["size"],
            }
            for f in files
            if f["path"].endswith(self.ARCHIVE_SUFFIX)
        ]

    def remove_old_backups(self, backup_config, server):
        while (
            len(self.list_backups(backup_config, server)) > backup_config["max_backups"]
            and backup_config["max_backups"] > 0
        ):
            backup_list = self.list_backups(backup_config, server.server_id)
            oldfile = backup_list[0]
            oldfile_path = os.path.join(
                backup_config["backup_location"],
                backup_config["backup_id"],
                oldfile["path"],
            )
            logger.info(f"Removing old backup '{oldfile['path']}'")
            os.remove(Helpers.get_os_understandable_path(oldfile_path))

    def snapshot_backup(self, backup_config, server) -> str | bool:
        """
        Creates snapshot style backup of server. No file will be saved more than once
        over all backups. Designed to enable encryption of files and s3 compatability in
        the future.

        Args:
            backup_config: Backup config to use.
            server: Server instance.

        Returns:

        """
        logger.info(f"Starting snapshot style backup for {server.name}")

        # Create backup variables.
        use_compression = backup_config["compress"]
        source_path = Path(server.settings["path"])
        backup_repository_path = (
            Path(backup_config["backup_location"]) / "snapshot_backups"
        )
        backup_time = datetime.datetime.now()
        backup_time_filesafe = backup_time.strftime(
            self.SNAPSHOT_BACKUP_DATE_FORMAT_STRING
        )
        backup_manifest_path = (
            backup_repository_path / "manifests" / f"{backup_time_filesafe}.manifest"
        )

        excluded_dirs = HelpersManagement.get_excluded_backup_dirs(
            backup_config["backup_id"]
        )
        list_of_files: list[Path] = FileHelpers.discover_files(
            source_path, excluded_dirs
        )

        # Create manifest file
        try:
            backup_manifest_path.parent.mkdir(exist_ok=True, parents=True)
            manifest_file: io.TextIOWrapper = backup_manifest_path.open("w+")
        except OSError as why:
            self.fail_backup(why, backup_config, server)
            return False

        # Write manifest file version.
        manifest_file.write("00\n")

        # Iterate over source files and save into backup repository.
        for file in list_of_files:
            try:
                file_hash = CryptoHelper.blake2_hash_file(file)
                self.file_helper.save_file(
                    file, backup_repository_path, file_hash, use_compression
                )
                # May return OSError if file path is not logical.
                file_local_path = self.file_helper.get_local_path_with_base(
                    file, source_path
                )
            except OSError as why:
                manifest_file.close()
                backup_manifest_path.unlink(missing_ok=True)
                self.fail_backup(why, backup_config, server)
                return False

            # Write saved file into manifest.
            manifest_file.write(
                f"{CryptoHelper.bytes_to_b64(file_hash)}:"
                f"{CryptoHelper.str_to_b64(file_local_path)}\n"
            )

        manifest_file.close()

        self.file_helper.clean_old_backups(
            backup_config["max_backups"], backup_repository_path
        )

        HelpersManagement.update_backup_config(
            backup_config["backup_id"],
            {"status": json.dumps({"status": "Standby", "message": ""})},
        )

        return Path(backup_manifest_path).name

    def zip_vault_restore(self, server_path, backup_location, in_place) -> bool:
        """Zip style restore function. Returns a boolean if an error was encountered or
        not.

        Args:
              server_path: Target to restore server to
              backup_location: Source zip file to restore
              in_place: Boolean value if servers should be restored in place

        Returning: Boolean false if no error was experienced, true if an error was
        encountered.
        """
        error = False
        if not in_place:  # If user does not want to back up in place we will
            error = self.clean_server_for_zip_restore(server_path)

        self.file_helper.restore_archive(backup_location, server_path)

        return error

    def clean_server_for_zip_restore(self, server_path) -> bool:
        """Cleans the server directory in preparation for a zip restore.

        Args:
            server_path: Path to server directory

        Returning: Boolean false if no error was encountered. True if an error was
        encountered.
        """
        error = False
        # clean the server dir
        for item in os.listdir(server_path):
            if os.path.isdir(os.path.join(server_path, item)) and item != "db_stats":
                result = self.file_helper.del_dirs(os.path.join(server_path, item))
                if not result:
                    error = True
            else:
                result = self.file_helper.del_file(os.path.join(server_path, item))
                if not result:
                    error = True
        return error

    def snapshot_restore(
        self, backup_config: {str}, backup_manifest_filename: str, server
    ) -> None:
        """
        Restores snapshot style backup.

        Args:
            backup_config: Backup Config.
            backup_manifest_filename: Filename of backup manifest.
            server: Server config.

        Returns:
        """
        destination_path = Path(server.settings["path"])
        source_manifest_path = Path(
            backup_config["backup_location"],
            "snapshot_backups",
            "manifests",
            backup_manifest_filename,
        )
        # /snapshot_backups/manifests/manifest.manifest
        backup_repository_path = source_manifest_path.parent.parent

        # Ensure destination is not a file.
        if destination_path.is_file():
            raise RuntimeError(
                f"Destination path {destination_path} for restore is a file."
            )

        # Ensure target is empty.
        if destination_path.exists():
            shutil.rmtree(destination_path)

        # Ensure target directory exists.
        destination_path.mkdir(exist_ok=True, parents=True)

        # Open backup manifest.
        try:
            backup_manifest_file: io.TextIOWrapper = source_manifest_path.open(
                "r", encoding="utf-8"
            )
        except OSError as why:
            raise RuntimeError(
                f"Unable to open backup manifest at {source_manifest_path}."
            ) from why

        # Ensure backup manifest is of readable version.
        if backup_manifest_file.readline() != "00\n":
            backup_manifest_file.close()
            raise RuntimeError(
                f"Backup manifest file {source_manifest_path} is of unreadable version."
            )

        # Begin restoring files from manifest.
        for file_hash_and_path in backup_manifest_file:
            hash_and_local_path: list[str] = file_hash_and_path.split(":")
            file_hash: bytes = CryptoHelper.b64_to_bytes(hash_and_local_path[0])
            recovered_file_path: Path = Path(
                destination_path,
                CryptoHelper.b64_to_str(input_b64=hash_and_local_path[1]),
            ).resolve()

            # Recover file
            try:
                # Check for traversal of maliciously created backup manifest file.
                # Ensure that the file we are writing is in the recovery target path.
                Helpers.validate_traversal(destination_path, recovered_file_path)
                self.file_helper.read_file(
                    file_hash, recovered_file_path, backup_repository_path
                )
            except (RuntimeError, ValueError) as why:
                backup_manifest_file.close()
                raise RuntimeError(f"Unable to recover file {file_hash}.") from why

        # Restore complete, close backup manifest file.
        backup_manifest_file.close()
