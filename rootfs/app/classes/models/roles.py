import logging
import datetime
import typing as t
from peewee import (
    CharField,
    DoesNotExist,
    AutoField,
    DateTimeField,
    IntegerField,
    BooleanField,
    SQL,
)
from playhouse.shortcuts import model_to_dict

from app.classes.models.base_model import BaseModel
from app.classes.helpers.helpers import Helpers

logger = logging.getLogger(__name__)


# **********************************************************************************
#                                   Roles Class
# **********************************************************************************
class Roles(BaseModel):
    role_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    role_name = CharField(default="", unique=True, index=True)
    manager = IntegerField(null=True)
    mfa_required = BooleanField(default=False)

    class Meta:
        table_name = "roles"


# **********************************************************************************
#                                   Roles Helpers
# **********************************************************************************
class HelperRoles:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def get_all_roles():
        return Roles.select()

    @staticmethod
    def get_all_role_ids() -> t.List[int]:
        return [role.role_id for role in Roles.select(Roles.role_id).execute()]

    @staticmethod
    def get_roleid_by_name(role_name):
        try:
            return (Roles.get(Roles.role_name == role_name)).role_id
        except DoesNotExist:
            return None

    @staticmethod
    def get_role(role_id):
        return model_to_dict(Roles.get(Roles.role_id == role_id))

    @staticmethod
    def get_role_columns(
        role_id: t.Union[str, int], column_names: t.List[str]
    ) -> t.List[t.Any]:
        columns = [getattr(Roles, column) for column in column_names]
        return model_to_dict(
            Roles.select(*columns).where(Roles.role_id == role_id).get(),
            only=columns,
        )

    @staticmethod
    def get_role_column(role_id: t.Union[str, int], column_name: str) -> t.Any:
        column = getattr(Roles, column_name)
        return getattr(
            Roles.select(column).where(Roles.role_id == role_id).get(), column_name
        )

    @staticmethod
    def add_role(role_name, manager, mfa_required):
        role_id = Roles.insert(
            {
                Roles.role_name: role_name.lower(),
                Roles.created: Helpers.get_time_as_string(),
                Roles.manager: manager,
                Roles.mfa_required: mfa_required,
            }
        ).execute()
        return role_id

    @staticmethod
    def update_role(role_id: str | int, up_data: t.Mapping[str, t.Any]) -> int:
        """Update a role and refresh last_update in SQLite.

        Args:
            role_id: The ID of the role to update.
            up_data: Column values to update on the role row. Any provided last_update
                value is ignored so the timestamp is always computed in the database.

        Returns:
            The number of updated rows.
        """
        update_data = dict(up_data)
        update_data["last_update"] = SQL(
            "strftime('%m/%d/%Y, %H:%M:%S', 'now', 'localtime')"
        )
        return Roles.update(update_data).where(Roles.role_id == role_id).execute()

    def remove_role(self, role_id):
        return Roles.delete().where(Roles.role_id == role_id).execute()

    @staticmethod
    def role_id_exists(role_id) -> bool:
        return Roles.select().where(Roles.role_id == role_id).exists()
