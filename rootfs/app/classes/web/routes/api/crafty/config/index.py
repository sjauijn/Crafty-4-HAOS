import os
import json
from jsonschema import ValidationError, validate
import orjson
from playhouse.shortcuts import model_to_dict
from app.classes.helpers.file_helpers import FileHelpers
from app.classes.web.base_api_handler import BaseApiHandler

config_json_schema = {
    "type": "object",
    "properties": {
        "http_port": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "language": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "cookie_expire": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "show_errors": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "history_max_age": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "stats_update_frequency_seconds": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "delete_default_json": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "show_contribute_link": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "virtual_terminal_lines": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "max_log_lines": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "max_audit_entries": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "disabled_language_files": {
            "type": "array",
            "error": "typeList",
            "fill": True,
        },
        "stream_size_GB": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "keywords": {
            "type": "array",
            "error": "typeList",
            "fill": True,
        },
        "allow_nsfw_profile_pictures": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "enable_user_self_delete": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "reset_secrets_on_next_boot": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "monitored_mounts": {
            "type": "array",
            "error": "typeList",
            "fill": True,
        },
        "dir_size_poll_freq_minutes": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "crafty_logs_delete_after_days": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "big_bucket_repo": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "enable_otp_skew": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "base_url": {
            "type": "string",
            "pattern": (
                r"^(?:(?:\d{1,3}\.){3}\d{1,3}"
                r"|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}"
                r"|localhost)(?::\d{1,5})?$"
            ),
            "error": "typeString",
            "fill": True,
        },
        "max_login_attempts": {"type": "integer", "error": "typeInt", "fill": True},
        "superMFA": {"type": "boolean", "error": "typeBool", "fill": True},
        "general_user_log_access": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "enable_passkey_auth": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "passkey_rp_name": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "experimental": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "silent_notif_fields": {
            "type": "array",
            "error": "typeList",
            "fill": True,
        },
        "time_range_presets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "minimum": 1},
                    "label": {"type": "string", "minLength": 1},
                },
                "required": ["hours", "label"],
                "additionalProperties": False,
            },
            "minItems": 1,
            "error": "typeList",
            "fill": True,
        },
        "sampling_tiers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "max_hours": {"type": "integer", "minimum": 1},
                    "sample_rate": {"type": "integer", "minimum": 1},
                },
                "required": ["max_hours", "sample_rate"],
                "additionalProperties": False,
            },
            "minItems": 1,
            "error": "typeList",
            "fill": True,
        },
        "sampling_fallback_divisor": {
            "type": "integer",
            "minimum": 1,
            "error": "typeInteger",
            "fill": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}
customize_json_schema = {
    "type": "object",
    "properties": {
        "photo": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "opacity": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}

photo_delete_schema = {
    "type": "object",
    "properties": {
        "photo": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}
DEFAULT_PHOTO = "login_1.jpg"


class ApiCraftyConfigIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            _,
            _,
        ) = auth_data

        # GET /api/v2/roles?ids=true
        get_only_ids = self.get_query_argument("ids", None) == "true"

        if not superuser:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": (
                    self.controller.roles.get_all_role_ids()
                    if get_only_ids
                    else [
                        model_to_dict(r) for r in self.controller.roles.get_all_roles()
                    ]
                ),
            },
        )

    def patch(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        _, _, _, superuser, user, _ = auth_data

        if not superuser:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        try:
            data = orjson.loads(self.request.body)
        except orjson.JSONDecodeError as why:
            return self.finish_json(
                400,
                {"status": "error", "error": "INVALID_JSON", "error_data": str(why)},
            )

        try:
            validate(data, config_json_schema)
        except ValidationError as why:
            offending_key = ""
            if why.schema.get("fill", None):
                offending_key = why.path[0] if why.path else None
            err = f"""{offending_key} {self.translator.translate(
                "validators",
                why.schema.get("error", "additionalProperties"),
                self.controller.users.get_user_lang_by_id(auth_data[4]["user_id"]),
            )} {why.schema.get("enum", "")}"""
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": f"{str(err)}",
                },
            )

        self.controller.set_config_json(data)

        self.controller.management.add_to_audit_log(
            user["user_id"],
            "edited config.json",
            server_id=None,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )


class ApiCraftyCustomizeIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            _,
            _,
        ) = auth_data

        # GET /api/v2/roles?ids=true
        get_only_ids = self.get_query_argument("ids", None) == "true"

        if not superuser:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": (
                    self.controller.roles.get_all_role_ids()
                    if get_only_ids
                    else [
                        model_to_dict(r) for r in self.controller.roles.get_all_roles()
                    ]
                ),
            },
        )

    def patch(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            user,
            _,
        ) = auth_data
        if not superuser:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        try:
            data = orjson.loads(self.request.body)
        except orjson.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, customize_json_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        if not self.helper.validate_traversal(
            os.path.join(
                self.controller.project_root,
                "app/frontend/static/assets/images/auth/",
            ),
            os.path.join(
                self.controller.project_root,
                f"app/frontend/static/assets/images/auth/{data['photo']}",
            ),
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": "TRIED TO REACH FILES THAT ARE"
                    " NOT SUPPOSED TO BE ACCESSIBLE",
                },
            )
        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"customized login photo: {data['photo']}/{data['opacity']}",
            server_id=None,
            source_ip=self.get_remote_ip(),
        )
        self.controller.management.set_login_opacity(int(data["opacity"]))
        if data["photo"] == DEFAULT_PHOTO:
            self.controller.management.set_login_image(DEFAULT_PHOTO)
            self.controller.cached_login = f"{data['photo']}"
        else:
            self.controller.management.set_login_image(f"custom/{data['photo']}")
            self.controller.cached_login = f"custom/{data['photo']}"
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {"photo": data["photo"], "opacity": data["opacity"]},
            },
        )

    def delete(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if not auth_data[4]["superuser"]:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
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
            validate(data, photo_delete_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        if not self.helper.validate_traversal(
            os.path.join(
                self.controller.project_root,
                "app",
                "frontend",
                "/static/assets/images/auth/",
            ),
            os.path.join(
                self.controller.project_root,
                "app",
                "frontend",
                "/static/assets/images/auth/",
                data["photo"],
            ),
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": "TRIED TO REACH FILES THAT ARE"
                    " NOT SUPPOSED TO BE ACCESSIBLE",
                },
            )
        if data["photo"] == DEFAULT_PHOTO:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID FILE",
                    "error_data": "CANNOT DELETE DEFAULT",
                },
            )
        FileHelpers.del_file(
            os.path.join(
                self.controller.project_root,
                f"app/frontend/static/assets/images/auth/custom/{data['photo']}",
            )
        )
        current = self.controller.cached_login
        split = current.split("/")
        if len(split) == 1:
            current_photo = current
        else:
            current_photo = split[1]
        if current_photo == data["photo"]:
            self.controller.management.set_login_image(DEFAULT_PHOTO)
            self.controller.cached_login = DEFAULT_PHOTO
        return self.finish_json(200, {"status": "ok"})
