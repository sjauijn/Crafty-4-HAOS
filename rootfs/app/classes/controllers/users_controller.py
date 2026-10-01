import logging
import typing as t
import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from app.classes.models.servers import HelperServers

from app.classes.models.users import HelperUsers
from app.classes.models.roles import HelperRoles
from app.classes.models.crafty_permissions import (
    PermissionsCrafty,
    EnumPermissionsCrafty,
)
from app.classes.shared.console import Console

logger = logging.getLogger(__name__)


class UsersController:
    class ApiPermissionDict(t.TypedDict):
        name: str
        quantity: int
        enabled: bool

    def __init__(self, helper, users_helper, authentication):
        self.helper = helper
        self.users_helper = users_helper
        self.authentication = authentication
        self.scheduler = BackgroundScheduler(timezone="Etc/UTC")
        self.scheduler.start()

        _permissions_props = {
            "name": {
                "type": "string",
                "enum": [
                    permission.name
                    for permission in PermissionsCrafty.get_permissions_list()
                ],
                "error": "enumErr",
                "fill": True,
            },
            "quantity": {
                "type": "number",
                "minimum": -1,
                "error": "typeInteger",
                "fill": True,
            },
            "enabled": {"type": "boolean", "error": "typeBool", "fill": True},
        }
        self.user_jsonschema_props: t.Final = {
            "username": {
                "type": "string",
                "maxLength": 20,
                "minLength": 3,
                "pattern": "^[a-z0-9_]+$",
                "examples": ["admin"],
                "title": "Username",
                "error": "userName",
                "fill": True,
            },
            "password": {
                "type": "string",
                "minLength": self.helper.minimum_password_length,
                "pattern": "^.{8,}$",
                "examples": ["crafty"],
                "title": "Password",
                "error": "passProp",
            },
            "email": {
                "type": "string",
                "format": "email",
                "examples": ["default@example.com"],
                "title": "E-Mail",
                "error": "typeEmail",
                "fill": True,
            },
            "enabled": {
                "type": "boolean",
                "examples": [True],
                "title": "Enabled",
                "error": "typeBool",
                "fill": True,
            },
            "lang": {
                "type": "string",
                "maxLength": 10,
                "minLength": 2,
                "examples": ["en"],
                "title": "Language",
                "error": "typeString",
                "fill": True,
            },
            "superuser": {
                "type": "boolean",
                "examples": [False],
                "title": "Superuser",
                "error": "typeBool",
                "fill": True,
            },
            "manager": {
                "type": ["integer", "null"],
                "error": "typeInteger",
                "fill": True,
            },
            "theme": {
                "type": "string",
                "error": "typeString",
                "fill": True,
            },
            "permissions": {
                "type": "array",
                "error": "typeList",
                "fill": True,
                "items": {
                    "type": "object",
                    "properties": _permissions_props,
                    "required": ["name", "quantity", "enabled"],
                },
            },
            "roles": {
                "type": "array",
                "error": "typeList",
                "fill": True,
                "items": {
                    "type": "integer",
                    "minLength": 1,
                    "error": "typeInteger",
                    "fill": True,
                },
            },
            "hints": {
                "type": "boolean",
                "error": "typeBool",
                "fill": True,
            },
            "server_order": {
                "type": "string",
                "error": "typeString",
                "fill": True,
            },
            "dashboard_columns": {
                "type": "string",
                "error": "typeString",
                "fill": True,
            },
            "disable_password_auth": {
                "type": "boolean",
                "examples": [False],
                "title": "Disable Password Authentication",
                "error": "typeBool",
                "fill": True,
            },
        }

    # **********************************************************************************
    #                                   Users Methods
    # **********************************************************************************
    @staticmethod
    def get_all_users():
        return HelperUsers.get_all_users()

    @staticmethod
    def get_all_user_ids() -> t.List[int]:
        return HelperUsers.get_all_user_ids()

    @staticmethod
    def get_all_usernames():
        return HelperUsers.get_all_usernames()

    @staticmethod
    def get_id_by_name(username):
        return HelperUsers.get_user_id_by_name(username)

    @staticmethod
    def get_user_lang_by_id(user_id):
        return HelperUsers.get_user_lang_by_id(user_id)

    @staticmethod
    def get_user_by_id(user_id):
        return HelperUsers.get_user(user_id)

    @staticmethod
    def get_user_object(user_id) -> object:
        return HelperUsers.get_by_id(user_id)

    @staticmethod
    def update_server_order(user_id, user_server_order):
        HelperUsers.update_server_order(user_id, user_server_order)

    @staticmethod
    def get_server_order(user_id):
        return HelperUsers.get_server_order(user_id)

    @staticmethod
    def user_query(user_id):
        return HelperUsers.user_query(user_id)

    @staticmethod
    def get_managed_users(exec_user_id):
        return HelperUsers.get_managed_users(exec_user_id)

    @staticmethod
    def get_managed_users_ids(exec_user_id) -> list[int]:
        return HelperUsers.get_managed_users_ids(exec_user_id)

    @staticmethod
    def get_managed_roles(exec_user_id):
        return HelperUsers.get_managed_roles(exec_user_id)

    @staticmethod
    def get_created_servers(exec_user_id):
        return HelperServers.get_total_owned_servers(exec_user_id)

    def update_user(self, user_id: str, user_data=None, user_crafty_data=None):
        # check if user crafty perms were updated
        if user_crafty_data is None:
            user_crafty_data = {}
        # check if general user data was updated
        if user_data is None:
            user_data = {}
        # get current user data
        base_data = HelperUsers.get_user(user_id)
        up_data = {}
        # check if we updated user email. If so we update gravatar
        try:
            if user_data["email"] != base_data["email"]:
                pfp = self.helper.get_gravatar_image(user_data["email"])
                up_data["pfp"] = pfp
        except KeyError:
            logger.debug("Email not updated")
            # email not updated
        # create sets to store role data
        added_roles = set()
        removed_roles = set()
        if user_data.get("username", None) == "anti-lockout-user":
            raise ValueError("Invalid Username")
        # search for changes in user data
        for key in user_data:
            if key == "user_id":
                continue
            if key == "roles":
                added_roles = set(user_data["roles"]).difference(
                    set(base_data["roles"])
                )
                removed_roles = set(base_data["roles"]).difference(
                    set(user_data["roles"])
                )
            elif key == "password":
                if user_data["password"] is not None and user_data["password"] != "":
                    up_data["password"] = self.helper.encode_pass(user_data["password"])
            elif key == "lang":
                up_data["lang"] = user_data["lang"]
            elif key == "hints":
                up_data["hints"] = user_data["hints"]
            elif base_data[key] != user_data[key]:
                up_data[key] = user_data[key]
        # change last update for user
        up_data["last_update"] = self.helper.get_time_as_string()
        logger.debug(f"user: {user_data} +role:{added_roles} -role:{removed_roles}")

        for role in added_roles:
            HelperUsers.get_or_create(user_id=user_id, role_id=role)
        permissions_mask = user_crafty_data.get("permissions_mask", "000")

        if "server_quantity" in user_crafty_data:
            limit_server_creation = user_crafty_data["server_quantity"].get(
                EnumPermissionsCrafty.SERVER_CREATION.name, 0
            )

            limit_user_creation = user_crafty_data["server_quantity"].get(
                EnumPermissionsCrafty.USER_CONFIG.name, 0
            )
            limit_role_creation = user_crafty_data["server_quantity"].get(
                EnumPermissionsCrafty.ROLES_CONFIG.name, 0
            )
        else:
            limit_server_creation = 0
            limit_user_creation = 0
            limit_role_creation = 0
        if user_crafty_data:
            PermissionsCrafty.add_or_update_user(
                user_id,
                permissions_mask,
                limit_server_creation,
                limit_user_creation,
                limit_role_creation,
            )

        self.users_helper.delete_user_roles(user_id, removed_roles)

        self.users_helper.update_user(user_id, up_data)

    def raw_update_user(self, user_id: int, up_data: t.Optional[t.Dict[str, t.Any]]):
        """Directly passes the data to the model helper.

        Args:
            user_id (int): The id of the user to update.
            up_data (t.Optional[t.Dict[str, t.Any]]): Update data.
        """
        self.users_helper.update_user(user_id, up_data)

    def add_user(
        self,
        username,
        manager,
        password,
        email="default@example.com",
        enabled: bool = True,
        superuser: bool = False,
        theme="default",
    ):
        if username == "anti-lockout-user":
            raise ValueError("Username is not valid")
        return self.users_helper.add_user(
            username,
            manager,
            password=password,
            email=email,
            enabled=enabled,
            superuser=superuser,
            theme=theme,
        )

    @staticmethod
    def add_rawpass_user(
        username,
        password,
        email="default@example.com",
        enabled: bool = True,
        superuser: bool = False,
    ):
        return HelperUsers.add_rawpass_user(
            username,
            password=password,
            email=email,
            enabled=enabled,
            superuser=superuser,
        )

    def remove_user(self, user_id):
        for user in self.get_managed_users(user_id):
            self.update_user(user.user_id, {"manager": None})
        for role in HelperUsers.get_managed_roles(user_id):
            HelperRoles.update_role(role.role_id, {"manager": None})
        return self.users_helper.remove_user(user_id)

    @staticmethod
    def user_id_exists(user_id):
        return HelperUsers.user_id_exists(user_id)

    @staticmethod
    def set_prepare(user_id):
        return HelperUsers.set_prepare(user_id)

    @staticmethod
    def stop_prepare(user_id):
        return HelperUsers.stop_prepare(user_id)

    def get_user_id_by_api_token(self, token: str) -> str:
        token_data = self.authentication.check_no_iat(token)
        return token_data["user_id"]

    def get_user_by_api_token(self, token: str):
        _, _, user = self.authentication.check_err(token)
        return user

    def get_api_key_by_token(self, token: str):
        key, _, _ = self.authentication.check(token)
        return key

    # **********************************************************************************
    #                                   User Roles Methods
    # **********************************************************************************

    @staticmethod
    def get_user_roles_id(user_id):
        return HelperUsers.get_user_roles_id(user_id)

    @staticmethod
    def get_user_roles_names(user_id):
        return HelperUsers.get_user_roles_names(user_id)

    def add_role_to_user(self, user_id, role_id):
        return self.users_helper.add_role_to_user(user_id, role_id)

    def add_user_roles(self, user):
        return self.users_helper.add_user_roles(user)

    @staticmethod
    def user_role_query(user_id):
        return HelperUsers.user_role_query(user_id)

    # **********************************************************************************
    #                                   Api Keys Methods
    # **********************************************************************************

    @staticmethod
    def get_user_api_keys(user_id: str):
        return HelperUsers.get_user_api_keys(user_id)

    @staticmethod
    def get_user_api_key(key_id: str):
        return HelperUsers.get_user_api_key(key_id)

    def add_user_api_key(
        self,
        name: str,
        user_id: str,
        superuser: bool = False,
        server_permissions_mask: t.Optional[str] = None,
        crafty_permissions_mask: t.Optional[str] = None,
    ):
        return self.users_helper.add_user_api_key(
            name, user_id, superuser, server_permissions_mask, crafty_permissions_mask
        )

    def delete_user_api_keys(self, user_id: str):
        return self.users_helper.delete_user_api_keys(user_id)

    def delete_user_api_key(self, key_id: str):
        return self.users_helper.delete_user_api_key(key_id)

    # **********************************************************************************
    #                                   Lockout Methods
    # **********************************************************************************
    def start_anti_lockout(self):
        lockout_pass = self.helper.create_pass()
        self.users_helper.add_user(
            "anti-lockout-user",
            None,
            password=lockout_pass,
            email="",
            enabled=True,
            superuser=True,
            theme="anti-lockout",
        )

        Console.yellow(f"""
            Anti-lockout recovery account enabled!
            {'/' * 74}
            Username: anti-lockout-user
            Password: {lockout_pass}
            {'/' * 74}""")
        self.scheduler.add_job(
            self.stop_anti_lockout,
            "date",
            id="anti-lockout-watcher",
            run_date=datetime.datetime.now(ZoneInfo("Etc/UTC")) + timedelta(hours=1),
        )

    def stop_anti_lockout(self):
        self.scheduler.remove_all_jobs()
        self.users_helper.remove_user(self.get_id_by_name("anti-lockout-user"))
