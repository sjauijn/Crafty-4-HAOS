import peewee
import datetime
from peewee import (
    AutoField,
    DateTimeField,
    CharField,
    IntegerField,
    ForeignKeyField,
    TextField,
)

from app.classes.shared.server import Servers


def migrate(migrator, db):
    migrator.drop_table("audit_log")


def rollback(migrator, db):
    class AuditLog(peewee.Model):
        audit_id = AutoField()
        created = DateTimeField(default=datetime.datetime.now)
        user_name = CharField(default="")
        user_id = IntegerField(default=0, index=True)
        source_ip = CharField(default="127.0.0.1")
        server_id = ForeignKeyField(
            Servers, backref="audit_server", null=True
        )  # When auditing global events, use server ID null
        log_msg = TextField(default="")

        class Meta:
            table_name = "audit_log"

    migrator.create_table(AuditLog)
