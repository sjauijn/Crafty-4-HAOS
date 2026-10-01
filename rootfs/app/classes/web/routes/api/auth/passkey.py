import logging
import json

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from app.classes.models.users import Users
from app.classes.helpers.helpers import Helpers
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)
auth_log = logging.getLogger("auth")

passkey_login_options_schema = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "maxLength": 20,
            "minLength": 3,
            "pattern": "^[a-zA-Z0-9_-]+$",
        },
    },
    "additionalProperties": False,
}

passkey_login_verify_schema = {
    "type": "object",
    "properties": {
        "challenge_id": {"type": "string"},
        "credential": {"type": "object"},
    },
    "required": ["challenge_id", "credential"],
    "additionalProperties": False,
}


class ApiAuthPasskeyLoginOptionsHandler(BaseApiHandler):
    def post(self):
        if not self.controller.passkey.is_enabled():
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "PASSKEY_DISABLED",
                    "error_data": self.helper.translation.translate(
                        "passkey",
                        "disabled",
                        self.helper.get_setting("language"),
                    ),
                },
            )

        try:
            data = json.loads(self.request.body) if self.request.body else {}
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, passkey_login_options_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        username = data.get("username")

        result = self.controller.passkey.generate_authentication_options(username)

        # Always return options - don't reveal if user has passkeys or not
        # to prevent user enumeration. Auth will fail at verify step.
        return self.finish_json(
            200,
            {
                "status": "ok",
                "data": result,
            },
        )


class ApiAuthPasskeyLoginVerifyHandler(BaseApiHandler):
    def post(self):
        if not self.controller.passkey.is_enabled():
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "PASSKEY_DISABLED",
                    "error_data": self.helper.translation.translate(
                        "passkey",
                        "disabled",
                        self.helper.get_setting("language"),
                    ),
                },
            )

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, passkey_login_verify_schema)
        except ValidationError:
            return self.finish_json(
                401,
                {
                    "status": "error",
                    "error": "INCORRECT_CREDENTIALS",
                    "error_data": self.helper.translation.translate(
                        "login", "incorrect", self.helper.get_setting("language")
                    ),
                },
            )

        user_id = self.controller.passkey.verify_authentication(
            data["challenge_id"],
            data["credential"],
        )

        if not user_id:
            auth_log.error(f"Passkey authentication failed from {self.get_remote_ip()}")
            return self.finish_json(
                401,
                {
                    "status": "error",
                    "error": "INCORRECT_CREDENTIALS",
                    "error_data": self.helper.translation.translate(
                        "login", "incorrect", self.helper.get_setting("language")
                    ),
                },
            )

        user_data = Users.get_by_id(user_id)

        if not user_data.enabled:
            auth_log.error(
                f"Passkey login attempted for disabled user {user_id} "
                f"from {self.get_remote_ip()}"
            )
            return self.finish_json(
                403,
                {
                    "status": "error",
                    "error": "ACCOUNT_DISABLED",
                    "error_data": self.helper.translation.translate(
                        "login",
                        "accountDisabled",
                        self.helper.get_setting("language"),
                    ),
                },
            )

        token = self.controller.authentication.generate(
            user_id, {"mfa": True, "passkey": True}
        )

        user_data.last_ip = self.get_remote_ip()
        user_data.last_login = Helpers.get_time_as_string()
        user_data.save()

        self.controller.management.add_to_audit_log(
            user_id, "logged in via passkey", None, self.get_remote_ip()
        )

        auth_log.info(
            f"{user_data.username} authenticated via passkey "
            f"from {self.get_remote_ip()}"
        )

        expire_days = self.helper.get_setting("cookie_expire")
        if not expire_days:
            expire_days = "30"

        self.set_cookie("token", token, expires_days=int(expire_days))

        return self.finish_json(
            200,
            {
                "status": "ok",
                "data": {
                    "token": token,
                    "user_id": str(user_id),
                    "page": self.build_url("/panel/dashboard"),
                },
            },
        )
