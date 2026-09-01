import logging
from datetime import datetime

from peewee import (
    ForeignKeyField,
    CharField,
    BlobField,
    IntegerField,
    BooleanField,
    DateTimeField,
)

from app.classes.helpers.helpers import Helpers
from app.classes.models.users import Users
from app.classes.models.base_model import BaseModel

logger = logging.getLogger(__name__)


class PasskeyData(BaseModel):
    """Model for user WebAuthn passkey credentials."""

    id = CharField(primary_key=True, default=Helpers.create_uuid)
    name = CharField(default="Passkey")
    user = ForeignKeyField(Users, backref="passkey_user")
    credential_id = BlobField()
    public_key = BlobField()
    sign_count = IntegerField(default=0)
    transports = CharField(default="")
    device_type = CharField(default="")
    backed_up = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)
    last_used_at = DateTimeField(null=True)

    class Meta:
        table_name = "passkey_data"


class PasskeyChallenge(BaseModel):
    """Temporary storage for WebAuthn challenges."""

    id = CharField(primary_key=True, default=Helpers.create_uuid)
    user = ForeignKeyField(Users, backref="passkey_challenge", null=True)
    challenge = BlobField()
    challenge_type = CharField()
    created_at = DateTimeField(default=datetime.now)
    expires_at = DateTimeField()

    class Meta:
        table_name = "passkey_challenges"


class HelperPasskey:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def create_passkey(
        passkey_id,
        name,
        user,
        credential_id,
        public_key,
        sign_count,
        transports,
        device_type,
        backed_up,
    ):
        return PasskeyData.create(
            id=passkey_id,
            name=name,
            user=user,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            transports=transports,
            device_type=device_type,
            backed_up=backed_up,
        )

    @staticmethod
    def get_passkey_by_id(passkey_id):
        return PasskeyData.get_or_none(PasskeyData.id == passkey_id)

    @staticmethod
    def get_passkey_by_credential_id(credential_id):
        return PasskeyData.get_or_none(PasskeyData.credential_id == credential_id)

    @staticmethod
    def get_user_passkeys(user_id):
        return PasskeyData.select().where(PasskeyData.user == user_id)

    def delete_passkey(self, passkey_id):
        with self.database.atomic():
            return PasskeyData.delete().where(PasskeyData.id == passkey_id).execute()

    @staticmethod
    def update_sign_count(passkey_id, new_sign_count):
        PasskeyData.update(
            sign_count=new_sign_count, last_used_at=datetime.now()
        ).where(PasskeyData.id == passkey_id).execute()

    @staticmethod
    def update_last_used(passkey_id):
        PasskeyData.update(last_used_at=datetime.now()).where(
            PasskeyData.id == passkey_id
        ).execute()

    @staticmethod
    def store_challenge(
        challenge_id, user, challenge_bytes, challenge_type, expires_at
    ):
        return PasskeyChallenge.create(
            id=challenge_id,
            user=user,
            challenge=challenge_bytes,
            challenge_type=challenge_type,
            expires_at=expires_at,
        )

    @staticmethod
    def get_challenge(challenge_id):
        return PasskeyChallenge.get_or_none(PasskeyChallenge.id == challenge_id)

    def delete_challenge(self, challenge_id):
        with self.database.atomic():
            PasskeyChallenge.delete().where(
                PasskeyChallenge.id == challenge_id
            ).execute()

    def cleanup_expired_challenges(self):
        with self.database.atomic():
            PasskeyChallenge.delete().where(
                PasskeyChallenge.expires_at < datetime.now()
            ).execute()
