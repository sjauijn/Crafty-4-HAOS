import base64
import json
import logging
from datetime import datetime, timedelta, timezone


from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

from app.classes.helpers.helpers import Helpers
from app.classes.models.users import HelperUsers
from app.classes.models.passkey import HelperPasskey, PasskeyData

logger = logging.getLogger(__name__)

CHALLENGE_TIMEOUT_MINUTES = 5


def _utc_now():
    """Return current UTC time as a naive datetime (for database compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PasskeyController:
    def __init__(self, passkey_helper, helper):
        self.passkey_helper: HelperPasskey = passkey_helper
        self.helper = helper

    def get_rp_id(self):
        base_url = self.helper.get_setting("base_url", "localhost:8443")
        return base_url.split(":")[0]

    def get_rp_name(self):
        return self.helper.get_setting("passkey_rp_name", "Crafty Controller")

    def get_origin(self):
        base_url = self.helper.get_setting("base_url", "localhost:8443")
        return f"https://{base_url}"

    def is_enabled(self):
        return self.helper.get_setting("enable_passkey_auth", False)

    def generate_registration_options(self, user_id):
        user = HelperUsers.get_user(user_id)

        existing_passkeys = list(self.passkey_helper.get_user_passkeys(user_id))
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=pk.credential_id)
            for pk in existing_passkeys
        ]

        options = generate_registration_options(
            rp_id=self.get_rp_id(),
            rp_name=self.get_rp_name(),
            user_id=str(user_id).encode(),
            user_name=user["username"],
            user_display_name=user["username"],
            exclude_credentials=exclude_credentials if exclude_credentials else None,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
            timeout=CHALLENGE_TIMEOUT_MINUTES * 60 * 1000,
        )

        challenge_id = Helpers.create_uuid()
        expires_at = _utc_now() + timedelta(minutes=CHALLENGE_TIMEOUT_MINUTES)

        user_obj = HelperUsers.get_by_id(user_id)
        self.passkey_helper.store_challenge(
            challenge_id=challenge_id,
            user=user_obj,
            challenge_bytes=options.challenge,
            challenge_type="registration",
            expires_at=expires_at,
        )

        logger.info("Generated passkey registration options for user %s", user_id)

        return {
            "options": json.loads(options_to_json(options)),
            "challenge_id": challenge_id,
        }

    def verify_registration(self, user_id, challenge_id, credential_name, response):
        challenge_record = self.passkey_helper.get_challenge(challenge_id)
        if not challenge_record:
            logger.warning("Invalid or expired challenge ID: %s", challenge_id)
            return False

        if challenge_record.challenge_type != "registration":
            logger.warning("Wrong challenge type for registration: %s", challenge_id)
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        if challenge_record.user.user_id != user_id:
            logger.warning("Challenge user mismatch for %s", challenge_id)
            return False

        if challenge_record.expires_at <= _utc_now():
            logger.warning("Expired challenge: %s", challenge_id)
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        try:
            verification = verify_registration_response(
                credential=response,
                expected_challenge=challenge_record.challenge,
                expected_rp_id=self.get_rp_id(),
                expected_origin=self.get_origin(),
            )
        except Exception as e:
            logger.exception("Registration verification failed: %s", e)
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        self.passkey_helper.delete_challenge(challenge_id)

        user_obj = HelperUsers.get_by_id(user_id)
        passkey_id = Helpers.create_uuid()

        # Get transports from input credential, not verification output
        transports = response.get("response", {}).get("transports", [])
        transports_json = json.dumps(transports)

        passkey = self.passkey_helper.create_passkey(
            passkey_id=passkey_id,
            name=credential_name or "Passkey",
            user=user_obj,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            transports=transports_json,
            device_type=verification.credential_device_type.value,
            backed_up=verification.credential_backed_up,
        )

        logger.info(
            "Successfully registered passkey %s for user %s", passkey_id, user_id
        )
        return passkey

    def generate_authentication_options(self, username=None):
        allow_credentials = []
        user_obj = None

        if username:
            user_id = HelperUsers.get_user_id_by_name(username)
            if user_id:
                user_obj = HelperUsers.get_by_id(user_id)
                existing_passkeys = list(self.passkey_helper.get_user_passkeys(user_id))

                # Don't return early if no passkeys -
                # proceed with empty allow_credentials
                # to prevent user enumeration. Auth will fail at verify step.
                allow_credentials = [
                    PublicKeyCredentialDescriptor(
                        id=pk.credential_id,
                        transports=(
                            json.loads(pk.transports)
                            if pk.transports and pk.transports not in ("", "[]")
                            else None
                        ),
                    )
                    for pk in existing_passkeys
                ]

        options = generate_authentication_options(
            rp_id=self.get_rp_id(),
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=CHALLENGE_TIMEOUT_MINUTES * 60 * 1000,
        )

        challenge_id = Helpers.create_uuid()
        expires_at = _utc_now() + timedelta(minutes=CHALLENGE_TIMEOUT_MINUTES)

        self.passkey_helper.store_challenge(
            challenge_id=challenge_id,
            user=user_obj,
            challenge_bytes=options.challenge,
            challenge_type="authentication",
            expires_at=expires_at,
        )

        logger.info("Generated passkey authentication options")

        return {
            "options": json.loads(options_to_json(options)),
            "challenge_id": challenge_id,
        }

    def verify_authentication(self, challenge_id, response):
        challenge_record = self.passkey_helper.get_challenge(challenge_id)
        if not challenge_record:
            logger.warning("Invalid challenge ID: %s", challenge_id)
            return False

        if challenge_record.challenge_type != "authentication":
            logger.warning("Wrong challenge type for authentication: %s", challenge_id)
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        if challenge_record.expires_at <= _utc_now():
            logger.warning("Expired challenge: %s", challenge_id)
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        credential_id = response.get("rawId")

        try:
            # Proper base64url padding calculation
            padding = 4 - (len(credential_id) % 4)
            if padding != 4:
                credential_id += "=" * padding
            credential_id_bytes = base64.urlsafe_b64decode(credential_id)
        except Exception:
            logger.warning("Invalid credential ID encoding")
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        passkey = self.passkey_helper.get_passkey_by_credential_id(credential_id_bytes)
        if not passkey:
            logger.warning("Unknown credential ID")
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        if (
            challenge_record.user
            and challenge_record.user.user_id != passkey.user.user_id
        ):
            logger.warning("Credential user mismatch")
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        try:
            verification = verify_authentication_response(
                credential=response,
                expected_challenge=challenge_record.challenge,
                expected_rp_id=self.get_rp_id(),
                expected_origin=self.get_origin(),
                credential_public_key=passkey.public_key,
                credential_current_sign_count=passkey.sign_count,
            )
        except Exception as e:
            logger.exception("Authentication verification failed: %s", e)
            self.passkey_helper.delete_challenge(challenge_id)
            return False

        self.passkey_helper.delete_challenge(challenge_id)

        # Always update last_used_at on successful authentication
        self.passkey_helper.update_last_used(passkey.id)

        if verification.new_sign_count > passkey.sign_count:
            self.passkey_helper.update_sign_count(
                passkey.id, verification.new_sign_count
            )
        elif (
            verification.new_sign_count > 0
            and verification.new_sign_count <= passkey.sign_count
        ):
            logger.warning(
                "Possible cloned authenticator detected for passkey %s", passkey.id
            )

        logger.info(
            "Successfully authenticated user %s via passkey", passkey.user.user_id
        )
        return passkey.user.user_id

    def delete_passkey(self, passkey_id, user_id):
        passkey = PasskeyData.get_or_none(PasskeyData.id == passkey_id)
        if not passkey or passkey.user.user_id != user_id:
            return False
        return self.passkey_helper.delete_passkey(passkey_id)

    def purge_expired_challenges(self):
        logger.info("Purging expired passkey challenges")
        self.passkey_helper.cleanup_expired_challenges()
