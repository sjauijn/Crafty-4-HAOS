import logging

from peewee import ForeignKeyField, CharField

from app.classes.helpers.helpers import Helpers
from app.classes.models.users import Users
from app.classes.models.base_model import BaseModel

logger = logging.getLogger(__name__)


class TOTPData(BaseModel):
    """Model for user TOTP methods.

    Consists of:
    UUID PK
    Foreign key user ID
    totp secret

    Args:
        BaseModel (_type_): _description_
    """

    id = CharField(primary_key=True, default=Helpers.create_uuid)
    name = CharField(default="TOTP")
    user = ForeignKeyField(Users, backref="totp_user")
    totp_secret = CharField()

    class Meta:
        table_name = "totp_data"


class TOTPRecovery(BaseModel):
    """Model for user TOTP recovery.
    Consists of:
    UUID PK
    user_id foreign key field
    the recovery secret

    We will try to limit users to only 6 backup codes.

    Args:
        BaseModel (_type_): _description_
    """

    id = CharField(primary_key=True, default=Helpers.create_uuid)
    user = ForeignKeyField(Users, backref="recovery_user")
    recovery_secret = CharField()

    class Meta:
        table_name = "totp_recovery"


class HelperTOTP:
    def __init__(self, database):
        self.database = database

    ####################################################################################
    # TOTP OPTERATIONAL METHODS
    ####################################################################################

    @staticmethod
    def create_user_totp(totp_id: str, name: str, user: Users, user_secret: str) -> str:
        totp_id = TOTPData.create(
            id=totp_id, name=name, user=user, totp_secret=user_secret
        )
        return totp_id

    def delete_totp_entry(self, totp_id: str) -> bool:
        with self.database.atomic():
            return TOTPData.delete().where(TOTPData.id == totp_id).execute()

    ####################################################################################
    # TOTP REOVERY METHODS
    ####################################################################################

    def add_recovery_codes(self, user: object, codes: list):
        data = []
        for code in codes:
            data.append({"user": user, "recovery_secret": f"{code}"})
        with self.database.atomic():
            TOTPRecovery.insert_many(data).execute()

    def remove_recovery_code(self, secret):
        with self.database.atomic():
            TOTPRecovery.delete().where(TOTPRecovery.id == secret).execute()

    def remove_all_recovery_codes(self, user_id):
        with self.database.atomic():
            TOTPRecovery.delete().where(TOTPRecovery.user == int(user_id)).execute()
