import os
import json
import datetime
import uuid
import peewee
import logging


from app.classes.helpers.helpers import Helpers
from app.classes.shared.console import Console
from app.classes.helpers.file_helpers import FileHelpers
from app.classes.shared.migration import Migrator, MigrateHistory

logger = logging.getLogger(__name__)


def is_valid_entry(entry, all_servers):
    try:
        return str(entry.server_id) in all_servers
    except (TypeError, peewee.DoesNotExist):
        return False


def migrate(migrator: Migrator, database, **kwargs):
    """
    Write your migrations here.
    """
    this_migration = MigrateHistory.get_or_none(
        MigrateHistory.name == "20240308_multi-backup"
    )
    if this_migration is not None:
        Console.debug("Update database already done, skipping this part")
        return
    backup_migration_status = True
    schedule_migration_status = True
    db = database
    Console.info("Starting Backups migrations")
    Console.info(
        "Migrations: Adding columns [backup_id, "
        "backup_name, backup_location, enabled, default, action_id, backup_status]"
    )
    migrator.add_columns(
        "backups",
        backup_id=peewee.CharField(default=Helpers.create_uuid),
    )
    migrator.add_columns("backups", backup_name=peewee.CharField(default="Default"))
    migrator.add_columns("backups", backup_location=peewee.CharField(default=""))
    migrator.add_columns("backups", enabled=peewee.BooleanField(default=True))
    migrator.add_columns("backups", default=peewee.BooleanField(default=False))
    migrator.add_columns(
        "backups",
        status=peewee.CharField(default='{"status": "Standby", "message": ""}'),
    )
    migrator.add_columns(
        "schedules", action_id=peewee.CharField(null=True, default=None)
    )

    class Servers(peewee.Model):
        server_id = peewee.CharField(primary_key=True, default=str(uuid.uuid4()))
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_name = peewee.CharField(default="Server", index=True)
        path = peewee.CharField(default="")
        backup_path = peewee.CharField(default="")
        executable = peewee.CharField(default="")
        log_path = peewee.CharField(default="")
        execution_command = peewee.CharField(default="")
        auto_start = peewee.BooleanField(default=0)
        auto_start_delay = peewee.IntegerField(default=10)
        crash_detection = peewee.BooleanField(default=0)
        stop_command = peewee.CharField(default="stop")
        executable_update_url = peewee.CharField(default="")
        server_ip = peewee.CharField(default="127.0.0.1")
        server_port = peewee.IntegerField(default=25565)
        logs_delete_after = peewee.IntegerField(default=0)
        type = peewee.CharField(default="minecraft-java")
        show_status = peewee.BooleanField(default=1)
        created_by = peewee.IntegerField(default=-100)
        shutdown_timeout = peewee.IntegerField(default=60)
        ignored_exits = peewee.CharField(default="0")

        class Meta:
            table_name = "servers"
            database = db

    class Backups(peewee.Model):
        backup_id = peewee.CharField(primary_key=True, default=Helpers.create_uuid)
        backup_name = peewee.CharField(default="New Backup")
        backup_location = peewee.CharField(default="")
        excluded_dirs = peewee.CharField(null=True)
        max_backups = peewee.IntegerField()
        server_id = peewee.ForeignKeyField(Servers, backref="backups_server")
        compress = peewee.BooleanField(default=False)
        shutdown = peewee.BooleanField(default=False)
        before = peewee.CharField(default="")
        after = peewee.CharField(default="")
        default = peewee.BooleanField(default=False)
        status = peewee.CharField(default='{"status": "Standby", "message": ""}')
        enabled = peewee.BooleanField(default=True)

        class Meta:
            table_name = "backups"
            database = db

    class NewBackups(peewee.Model):
        backup_id = peewee.CharField(primary_key=True, default=Helpers.create_uuid)
        backup_name = peewee.CharField(default="New Backup")
        backup_location = peewee.CharField(default="")
        excluded_dirs = peewee.CharField(null=True)
        max_backups = peewee.IntegerField()
        server_id = peewee.ForeignKeyField(Servers, backref="backups_server")
        compress = peewee.BooleanField(default=False)
        shutdown = peewee.BooleanField(default=False)
        before = peewee.CharField(default="")
        after = peewee.CharField(default="")
        default = peewee.BooleanField(default=False)
        status = peewee.CharField(default='{"status": "Standby", "message": ""}')
        enabled = peewee.BooleanField(default=True)

        class Meta:
            table_name = "new_backups"
            database = db

    class Schedules(peewee.Model):
        schedule_id = peewee.IntegerField(unique=True, primary_key=True)
        server_id = peewee.ForeignKeyField(Servers, backref="schedule_server")
        enabled = peewee.BooleanField()
        action = peewee.CharField()
        interval = peewee.IntegerField()
        interval_type = peewee.CharField()
        start_time = peewee.CharField(null=True)
        command = peewee.CharField(null=True)
        action_id = peewee.CharField(null=True)
        name = peewee.CharField()
        one_time = peewee.BooleanField(default=False)
        cron_string = peewee.CharField(default="")
        parent = peewee.IntegerField(null=True)
        delay = peewee.IntegerField(default=0)
        next_run = peewee.CharField(default="")

        class Meta:
            table_name = "schedules"
            database = db

    class NewSchedules(peewee.Model):
        schedule_id = peewee.IntegerField(unique=True, primary_key=True)
        server_id = peewee.ForeignKeyField(Servers, backref="schedule_server")
        enabled = peewee.BooleanField()
        action = peewee.CharField()
        interval = peewee.IntegerField()
        interval_type = peewee.CharField()
        start_time = peewee.CharField(null=True)
        command = peewee.CharField(null=True)
        action_id = peewee.CharField(null=True)
        name = peewee.CharField()
        one_time = peewee.BooleanField(default=False)
        cron_string = peewee.CharField(default="")
        parent = peewee.IntegerField(null=True)
        delay = peewee.IntegerField(default=0)
        next_run = peewee.CharField(default="")

        class Meta:
            table_name = "new_schedules"
            database = db

    migrator.create_table(NewBackups)
    migrator.create_table(NewSchedules)

    migrator.run()
    all_servers = [
        row.server_id for row in Servers.select(Servers.server_id).distinct()
    ]
    all_backups = Backups.select()
    all_schedules = Schedules.select()
    Console.info("Cleaning up orphan backups for all servers")
    valid_backups = [
        backup for backup in all_backups if is_valid_entry(backup, all_servers)
    ]
    if len(valid_backups) < len(all_backups):
        backup_migration_status = False
        print("Orphan backup found")
    Console.info("Cleaning up orphan schedules for all servers")
    valid_schedules = [
        schedule for schedule in all_schedules if is_valid_entry(schedule, all_servers)
    ]
    if len(valid_schedules) < len(all_schedules):
        schedule_migration_status = False
    # Copy data from the existing backups table to the new one
    for backup in valid_backups:
        Console.info(f"Trying to get server for backup migration {backup.server_id}")
        # Fetch the related server entry from the Servers table
        server = Servers.get(Servers.server_id == backup.server_id)
        Console.info(f"Migrations: Migrating backup for server {server.server_name}")
        # Create a new backup entry with data from the
        # old backup entry and related server
        new_backup = NewBackups.create(
            backup_name=f"{server.server_name} Backup",
            # Set backup_location equal to backup_path
            backup_location=server.backup_path,
            excluded_dirs=backup.excluded_dirs,
            max_backups=backup.max_backups,
            server_id=server.server_id,
            compress=backup.compress,
            shutdown=backup.shutdown,
            before=backup.before,
            after=backup.after,
            default=True,
            enabled=True,
        )
        Console.info(
            f"New backup table created for {server.server_name} with id {new_backup.backup_id}"
        )
        Helpers.ensure_dir_exists(
            os.path.join(server.backup_path, new_backup.backup_id)
        )
        try:
            Console.info(
                f"Moving old backups to new backup dir for {server.server_name}"
            )
            for file in os.listdir(server.backup_path):
                if not os.path.isdir(
                    os.path.join(os.path.join(server.backup_path, file))
                ):
                    FileHelpers.move_file(
                        os.path.join(server.backup_path, file),
                        os.path.join(server.backup_path, new_backup.backup_id, file),
                    )
        except FileNotFoundError as why:
            logger.error(
                f"Could not move backups for {server.server_name} to new location with error {why}"
            )

    Console.debug("Migrations: Dropping old backup table")
    # Drop the existing backups table
    migrator.drop_table("backups")

    Console.debug("Migrations: Renaming new_backups to backups")
    # Rename the new table to backups
    migrator.rename_table("new_backups", "backups")

    Console.debug("Migrations: Dropping backup_path from servers table")
    migrator.drop_columns("servers", ["backup_path"])

    for schedule in valid_schedules:
        action_id = None
        if schedule.command == "backup_server":
            Console.info(
                f"Migrations: Adding backup ID to task with name {schedule.name}"
            )
            try:
                backup = NewBackups.get(NewBackups.server_id == schedule.server_id)
            except:
                schedule_migration_status = False
                Console.error(
                    "Could not find backup with selected server ID. Omitting from register."
                )
                continue
            action_id = backup.backup_id
        NewSchedules.create(
            schedule_id=schedule.schedule_id,
            server_id=schedule.server_id,
            enabled=schedule.enabled,
            action=schedule.action,
            interval=schedule.interval,
            interval_type=schedule.interval_type,
            start_time=schedule.start_time,
            command=schedule.command,
            action_id=action_id,
            name=schedule.name,
            one_time=schedule.one_time,
            cron_string=schedule.cron_string,
            parent=schedule.parent,
            delay=schedule.delay,
            next_run=schedule.next_run,
        )

    Console.debug("Migrations: dropping old schedules table")
    # Drop the existing backups table
    migrator.drop_table("schedules")

    Console.debug("Migrations: renaming new_schedules to schedules")
    # Rename the new table to backups
    migrator.rename_table("new_schedules", "schedules")

    with open(
        os.path.join(
            os.path.abspath(os.path.curdir),
            "app",
            "migrations",
            "status",
            "20240308_multi-backup.json",
        ),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                {
                    "backup_migration": {
                        "type": "backup",
                        "status": backup_migration_status,
                        "pid": str(uuid.uuid4()),
                    },
                    "schedule_migration": {
                        "type": "schedule",
                        "status": schedule_migration_status,
                        "pid": str(uuid.uuid4()),
                    },
                }
            )
        )


def rollback(migrator: Migrator, database, **kwargs):
    """
    Write your rollback migrations here.
    """
    db = database

    migrator.drop_columns("backups", ["name", "backup_id", "backup_location"])
    migrator.add_columns("servers", backup_path=peewee.CharField(default=""))
