import datetime
import uuid
import peewee
import logging

from app.classes.shared.console import Console
from app.classes.shared.migration import Migrator, MigrateHistory
from app.classes.models.roles import Roles

logger = logging.getLogger(__name__)


def migrate(migrator: Migrator, database, **kwargs):
    """
    Write your migrations here.
    """
    db = database

    # **********************************************************************************
    #          Servers New Model from Old (easier to migrate without dunmping Database)
    # **********************************************************************************
    class Servers(peewee.Model):
        server_id = peewee.CharField(primary_key=True, default=str(uuid.uuid4()))
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_uuid = peewee.CharField(default="", index=True)
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

    # **********************************************************************************
    #                                  Role Servers Class
    # **********************************************************************************
    class RoleServers(peewee.Model):
        role_id = peewee.ForeignKeyField(Roles, backref="role_server")
        server_id = peewee.ForeignKeyField(Servers, backref="role_server")
        permissions = peewee.CharField(default="00000000")

        class Meta:
            table_name = "role_servers"
            primary_key = peewee.CompositeKey("role_id", "server_id")
            database = db

    # **********************************************************************************
    #                                   Webhooks Class
    # **********************************************************************************
    class Webhooks(peewee.Model):
        id = peewee.AutoField()
        server_id = peewee.ForeignKeyField(Servers, backref="webhook_server", null=True)
        name = peewee.CharField(default="Custom Webhook", max_length=64)
        url = peewee.CharField(default="")
        webhook_type = peewee.CharField(default="Custom")
        bot_name = peewee.CharField(default="Crafty Controller")
        trigger = peewee.CharField(default="server_start,server_stop")
        body = peewee.CharField(default="")
        color = peewee.CharField(default="#005cd1")
        enabled = peewee.BooleanField(default=True)

        class Meta:
            table_name = "webhooks"
            database = db

    # **********************************************************************************
    #                                   Schedules Class
    # **********************************************************************************
    class Schedules(peewee.Model):
        schedule_id = peewee.IntegerField(unique=True, primary_key=True)
        server_id = peewee.ForeignKeyField(Servers, backref="schedule_server")
        enabled = peewee.BooleanField()
        action = peewee.CharField()
        interval = peewee.IntegerField()
        interval_type = peewee.CharField()
        start_time = peewee.CharField(null=True)
        command = peewee.CharField(null=True)
        name = peewee.CharField()
        one_time = peewee.BooleanField(default=False)
        cron_string = peewee.CharField(default="")
        parent = peewee.IntegerField(null=True)
        delay = peewee.IntegerField(default=0)
        next_run = peewee.CharField(default="")

        class Meta:
            table_name = "schedules"
            database = db

    # **********************************************************************************
    #                                   Backups Class
    # **********************************************************************************
    class Backups(peewee.Model):
        excluded_dirs = peewee.CharField(null=True)
        max_backups = peewee.IntegerField()
        max_backups = peewee.IntegerField()
        server_id = peewee.ForeignKeyField(Servers, backref="backups_server")
        compress = peewee.BooleanField(default=False)
        shutdown = peewee.BooleanField(default=False)
        before = peewee.CharField(default="")
        after = peewee.CharField(default="")

        class Meta:
            table_name = "backups"
            database = db

    this_migration = MigrateHistory.get_or_none(
        MigrateHistory.name == "20240217_rework_servers_uuid_part2"
    )
    if this_migration is not None:
        Console.debug("Update database already done, skipping this part")
        return
    else:
        servers_columns = db.get_columns("servers")
        if not any(
            column_data.name == "server_uuid" for column_data in servers_columns
        ):
            Console.debug(
                "Servers.server_uuid already deleted in Crafty version 4.3.0, skipping this part"
            )
            return

    try:
        logger.debug("Migrating Data from Int to UUID (Foreign Keys)")
        Console.debug("Migrating Data from Int to UUID (Foreign Keys)")

        # Changes on Webhooks Log Table
        for webhook in Webhooks.select():
            old_server_id = webhook.server_id_id
            try:
                server = Servers.get_by_id(old_server_id)
                server_uuid = server.server_uuid
            except:
                server_uuid = old_server_id
            Webhooks.update(server_id=server_uuid).where(
                Webhooks.id == webhook.id
            ).execute()

        # Changes on Schedules Log Table
        for schedule in Schedules.select():
            old_server_id = schedule.server_id_id
            try:
                server = Servers.get_by_id(old_server_id)
                server_uuid = server.server_uuid
            except:
                server_uuid = old_server_id
            Schedules.update(server_id=server_uuid).where(
                Schedules.schedule_id == schedule.schedule_id
            ).execute()

        # Changes on Backups Log Table
        for backup in Backups.select():
            old_server_id = backup.server_id_id
            try:
                server = Servers.get_by_id(old_server_id)
                server_uuid = server.server_uuid
            except:
                server_uuid = old_server_id
            Backups.update(server_id=server_uuid).where(
                Backups.server_id == old_server_id
            ).execute()

        # Changes on RoleServers Log Table
        for role_servers in RoleServers.select():
            old_server_id = role_servers.server_id_id
            try:
                server = Servers.get_by_id(old_server_id)
                server_uuid = server.server_uuid
            except:
                server_uuid = old_server_id
            RoleServers.update(server_id=server_uuid).where(
                RoleServers.role_id == role_servers.id
                and RoleServers.server_id == old_server_id
            ).execute()

        logger.debug("Migrating Data from Int to UUID (Foreign Keys) : SUCCESS")
        Console.debug("Migrating Data from Int to UUID (Foreign Keys) : SUCCESS")

    except Exception as ex:
        logger.error("Error while migrating Data from Int to UUID (Foreign Keys)")
        logger.error(ex)
        Console.error("Error while migrating Data from Int to UUID (Foreign Keys)")
        Console.error(ex)
        last_migration = MigrateHistory.get_by_id(MigrateHistory.select().count())
        last_migration.delete()
        return

    try:
        logger.debug("Migrating Data from Int to UUID (Primary Keys)")
        Console.debug("Migrating Data from Int to UUID (Primary Keys)")
        # Migrating servers from the old id type to the new one
        for server in Servers.select():
            Servers.update(server_id=server.server_uuid).where(
                Servers.server_id == server.server_id
            ).execute()

        logger.debug("Migrating Data from Int to UUID (Primary Keys) : SUCCESS")
        Console.debug("Migrating Data from Int to UUID (Primary Keys) : SUCCESS")

    except Exception as ex:
        logger.error("Error while migrating Data from Int to UUID (Primary Keys)")
        logger.error(ex)
        Console.error("Error while migrating Data from Int to UUID (Primary Keys)")
        Console.error(ex)
        last_migration = MigrateHistory.get_by_id(MigrateHistory.select().count())
        last_migration.delete()
        return

    return


def rollback(migrator: Migrator, database, **kwargs):
    """
    Write your rollback migrations here.
    """
    db = database

    # Condition to prevent running rollback each time we've got a rollback to do
    this_migration = MigrateHistory.get_or_none(
        MigrateHistory.name == "20240217_rework_servers_uuid_part2"
    )
    if this_migration is None:
        Console.debug("Update database already done, skipping this part")
        return

    # **********************************************************************************
    #          Servers New Model from Old (easier to migrate without dunmping Database)
    # **********************************************************************************
    class Servers(peewee.Model):
        server_id = peewee.CharField(primary_key=True, default=str(uuid.uuid4()))
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_uuid = peewee.CharField(default="", index=True)
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

    # **********************************************************************************
    #                                  Role Servers Class
    # **********************************************************************************
    class RoleServers(peewee.Model):
        role_id = peewee.ForeignKeyField(Roles, backref="role_server")
        server_id = peewee.ForeignKeyField(Servers, backref="role_server")
        permissions = peewee.CharField(default="00000000")

        class Meta:
            table_name = "role_servers"
            primary_key = peewee.CompositeKey("role_id", "server_id")
            database = db

    # **********************************************************************************
    #                                   Webhooks Class
    # **********************************************************************************
    class Webhooks(peewee.Model):
        id = peewee.AutoField()
        server_id = peewee.ForeignKeyField(Servers, backref="webhook_server", null=True)
        name = peewee.CharField(default="Custom Webhook", max_length=64)
        url = peewee.CharField(default="")
        webhook_type = peewee.CharField(default="Custom")
        bot_name = peewee.CharField(default="Crafty Controller")
        trigger = peewee.CharField(default="server_start,server_stop")
        body = peewee.CharField(default="")
        color = peewee.CharField(default="#005cd1")
        enabled = peewee.BooleanField(default=True)

        class Meta:
            table_name = "webhooks"
            database = db

    # **********************************************************************************
    #                                   Schedules Class
    # **********************************************************************************
    class Schedules(peewee.Model):
        schedule_id = peewee.IntegerField(unique=True, primary_key=True)
        server_id = peewee.ForeignKeyField(Servers, backref="schedule_server")
        enabled = peewee.BooleanField()
        action = peewee.CharField()
        interval = peewee.IntegerField()
        interval_type = peewee.CharField()
        start_time = peewee.CharField(null=True)
        command = peewee.CharField(null=True)
        name = peewee.CharField()
        one_time = peewee.BooleanField(default=False)
        cron_string = peewee.CharField(default="")
        parent = peewee.IntegerField(null=True)
        delay = peewee.IntegerField(default=0)
        next_run = peewee.CharField(default="")

        class Meta:
            table_name = "schedules"
            database = db

    # **********************************************************************************
    #                                   Backups Class
    # **********************************************************************************
    class Backups(peewee.Model):
        excluded_dirs = peewee.CharField(null=True)
        max_backups = peewee.IntegerField()
        max_backups = peewee.IntegerField()
        server_id = peewee.ForeignKeyField(Servers, backref="backups_server")
        compress = peewee.BooleanField(default=False)
        shutdown = peewee.BooleanField(default=False)
        before = peewee.CharField(default="")
        after = peewee.CharField(default="")

        class Meta:
            table_name = "backups"
            database = db

    try:
        logger.debug("Migrating Data from UUID to Int (Primary Keys)")
        Console.debug("Migrating Data from UUID to Int (Primary Keys)")
        # Migrating servers from the old id type to the new one
        new_id = 0
        for server in Servers.select():
            new_id += 1
            Servers.update(server_uuid=server.server_id).where(
                Servers.server_id == server.server_id
            ).execute()
            Servers.update(server_id=new_id).where(
                Servers.server_id == server.server_id
            ).execute()

        logger.debug("Migrating Data from UUID to Int (Primary Keys) : SUCCESS")
        Console.debug("Migrating Data from UUID to Int (Primary Keys) : SUCCESS")

    except Exception as ex:
        logger.error("Error while migrating Data from UUID to Int (Primary Keys)")
        logger.error(ex)
        Console.error("Error while migrating Data from UUID to Int (Primary Keys)")
        Console.error(ex)
        last_migration = MigrateHistory.get_by_id(MigrateHistory.select().count())
        last_migration.delete()
        return

    try:
        logger.debug("Migrating Data from UUID to Int (Foreign Keys)")
        Console.debug("Migrating Data from UUID to Int (Foreign Keys)")
        # Changes on Webhooks Log Table
        for webhook in Webhooks.select():
            old_server_id = webhook.server_id_id
            try:
                server = Servers.get_or_none(Servers.server_uuid == old_server_id)
                new_server_id = server.server_id
            except:
                new_server_id = old_server_id
            Webhooks.update(server_id=new_server_id).where(
                Webhooks.id == webhook.id
            ).execute()

        # Changes on Schedules Log Table
        for schedule in Schedules.select():
            old_server_id = schedule.server_id_id
            try:
                server = Servers.get_or_none(Servers.server_uuid == old_server_id)
                new_server_id = server.server_id
            except:
                new_server_id = old_server_id
            Schedules.update(server_id=new_server_id).where(
                Schedules.schedule_id == schedule.schedule_id
            ).execute()

        # Changes on Backups Log Table
        for backup in Backups.select():
            old_server_id = backup.server_id_id
            try:
                server = Servers.get_or_none(Servers.server_uuid == old_server_id)
                new_server_id = server.server_id
            except:
                new_server_id = old_server_id
            Backups.update(server_id=new_server_id).where(
                Backups.server_id == old_server_id
            ).execute()

        # Changes on RoleServers Log Table
        for role_servers in RoleServers.select():
            old_server_id = role_servers.server_id_id
            try:
                server = Servers.get_or_none(Servers.server_uuid == old_server_id)
                new_server_id = server.server_id
            except:
                new_server_id = old_server_id
            RoleServers.update(server_id=new_server_id).where(
                RoleServers.role_id == role_servers.id
                and RoleServers.server_id == old_server_id
            ).execute()

        logger.debug("Migrating Data from UUID to Int (Foreign Keys) : SUCCESS")
        Console.debug("Migrating Data from UUID to Int (Foreign Keys) : SUCCESS")

    except Exception as ex:
        logger.error("Error while migrating Data from UUID to Int (Foreign Keys)")
        logger.error(ex)
        Console.error("Error while migrating Data from UUID to Int (Foreign Keys)")
        Console.error(ex)
        last_migration = MigrateHistory.get_by_id(MigrateHistory.select().count())
        last_migration.delete()
        return

    return
