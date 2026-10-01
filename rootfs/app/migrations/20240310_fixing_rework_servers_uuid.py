import datetime
import uuid
import peewee
import logging

from app.classes.shared.console import Console
from app.classes.shared.migration import Migrator, MigrateHistory
from app.classes.models.management import Schedules, Backups
from app.classes.models.server_permissions import RoleServers
from app.classes.models.servers import Servers

logger = logging.getLogger(__name__)


def migrate(migrator: Migrator, database, **kwargs):
    """
    Write your migrations here.
    """
    db = database

    try:
        # Changes on Servers Roles Table
        migrator.alter_column_type(
            RoleServers,
            "server_id",
            peewee.ForeignKeyField(
                Servers,
                backref="role_server",
                null=True,
                field=peewee.CharField(primary_key=True, default=str(uuid.uuid4())),
            ),
        )

        # Changes on Backups Table
        migrator.alter_column_type(
            Backups,
            "server_id",
            peewee.ForeignKeyField(
                Servers,
                backref="backup_server",
                null=True,
                field=peewee.CharField(primary_key=True, default=str(uuid.uuid4())),
            ),
        )

        # Changes on SChedule Table
        migrator.alter_column_type(
            Schedules,
            "server_id",
            peewee.ForeignKeyField(
                Servers,
                backref="schedule_server",
                null=True,
                field=peewee.CharField(primary_key=True, default=str(uuid.uuid4())),
            ),
        )

        # Drop Column after migration
        servers_columns = db.get_columns("servers")
        if any(column_data.name == "server_uuid" for column_data in servers_columns):
            Console.debug(
                "Servers.server_uuid not deleted before Crafty version 4.3.2, skipping this part"
            )
            migrator.drop_columns("servers", ["server_uuid"])

    except Exception as ex:
        logger.error("Error while migrating Data from Int to UUID (Fixing Issue)")
        logger.error(ex)
        Console.error("Error while migrating Data from Int to UUID (Fixing Issue)")
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

    # Changes on Webhook Table
    migrator.alter_column_type(
        RoleServers,
        "server_id",
        peewee.IntegerField(null=True),
    )

    # Changes on Webhook Table
    migrator.alter_column_type(
        Backups,
        "server_id",
        peewee.IntegerField(null=True),
    )

    # Changes on Webhook Table
    migrator.alter_column_type(
        Schedules,
        "server_id",
        peewee.IntegerField(null=True),
    )

    migrator.add_columns(
        "servers", server_uuid=peewee.CharField(default="", index=True)
    )  # Recreating the column for roll back
