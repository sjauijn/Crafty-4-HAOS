import logging
from datetime import datetime
from typing import Final, Iterable, List, Optional, TypedDict, cast

from app.classes.models.roles import HelperRoles
from app.classes.models.server_permissions import PermissionsServers, RoleServers

ServerId = str | int

logger = logging.getLogger(__name__)


class RolesController:
    class RoleData(TypedDict):
        role_id: int
        created: datetime | str
        last_update: datetime | str
        role_name: str
        manager: int | None
        mfa_required: bool

    class RoleWithServers(RoleData):
        servers: list[int]

    def __init__(self, users_helper, roles_helper):
        self.users_helper = users_helper
        self.roles_helper = roles_helper

    @staticmethod
    def get_all_roles():
        return HelperRoles.get_all_roles()

    @staticmethod
    def get_all_role_ids():
        return HelperRoles.get_all_role_ids()

    @staticmethod
    def get_roleid_by_name(role_name):
        return HelperRoles.get_roleid_by_name(role_name)

    @staticmethod
    def get_role(role_id):
        return HelperRoles.get_role(role_id)

    @staticmethod
    def add_role(role_name, manager, mfa_required):
        return HelperRoles.add_role(role_name, manager, mfa_required)

    class RoleServerJsonType(TypedDict):
        server_id: ServerId
        permissions: str

    @staticmethod
    def get_server_ids_and_perms_from_role(
        role_id: str | int,
    ) -> List[RoleServerJsonType]:
        """Return the server IDs and permission masks associated with a role.

        Args:
            role_id: The ID of the role whose server permissions should be retrieved.

        Returns:
            A list of dicts containing the server ID and permission mask for each server
            associated with the role.
        """
        query = (
            RoleServers.select(RoleServers.server_id, RoleServers.permissions)
            .where(RoleServers.role_id == role_id)
            .tuples()
        )

        result: List[RolesController.RoleServerJsonType] = []
        for server_id, permissions in query:
            result.append(
                RolesController.RoleServerJsonType(
                    server_id=cast(ServerId, server_id),
                    permissions=cast(str, permissions),
                )
            )

        return result

    @staticmethod
    def add_role_advanced(
        name: str,
        servers: Iterable[RoleServerJsonType],
        manager: int,
        mfa_required: bool,
    ) -> int:
        """Add a role with a name and a list of servers

        Args:
            name: The new role's name
            servers: The new role's servers
            manager: The new role's manager
            mfa_required: The new role's mfa required status

        Returns:
            int: The new role's ID
        """
        role_id: Final[int] = HelperRoles.add_role(name, manager, mfa_required)
        for server in servers:
            PermissionsServers.get_or_create(
                role_id, server["server_id"], server["permissions"]
            )
        return role_id

    @staticmethod
    def update_role(
        role_id: str | int,
        role_name: Optional[str],
        servers: Optional[Iterable[RoleServerJsonType]],
        manager: int,
        mfa_required: bool,
    ) -> None:
        """Update a role with a name and a list of servers

        Args:
            role_id: The ID of the role to be modified
            role_name: An optional new name for the role
            servers: An optional list of servers for the role
            manager: The manager ID to update with
            mfa_required: MFA required value to update with
        """
        logger.debug(f"updating role {role_id} with advanced options")

        if servers is not None:
            base_data = RolesController.get_role_with_servers(role_id)

            server_ids = {server["server_id"] for server in servers}
            server_permissions_map = {
                server["server_id"]: server["permissions"] for server in servers
            }

            added_servers = server_ids.difference(set(base_data["servers"]))
            removed_servers = set(base_data["servers"]).difference(server_ids)
            same_servers = server_ids.intersection(set(base_data["servers"]))
            logger.debug(
                f"role: {role_id} +server:{added_servers} -server{removed_servers}"
            )
            for server_id in added_servers:
                PermissionsServers.get_or_create(
                    role_id, server_id, server_permissions_map[server_id]
                )
            if len(removed_servers) != 0:
                PermissionsServers.delete_roles_permissions(role_id, removed_servers)
            for server_id in same_servers:
                PermissionsServers.update_role_permission(
                    role_id, server_id, server_permissions_map[server_id]
                )
        if role_name is not None:
            up_data = {
                "role_name": role_name,
                "manager": manager,
                "mfa_required": mfa_required,
            }
            HelperRoles.update_role(role_id, up_data)

    def remove_role(self, role_id):
        role_data = RolesController.get_role_with_servers(role_id)
        PermissionsServers.delete_roles_permissions(role_id, role_data["servers"])
        self.users_helper.remove_roles_from_role_id(role_id)
        return self.roles_helper.remove_role(role_id)

    @staticmethod
    def role_id_exists(role_id):
        return HelperRoles.role_id_exists(role_id)

    @staticmethod
    def get_role_with_servers(role_id):
        role = HelperRoles.get_role(role_id)

        if role:
            server_ids = PermissionsServers.get_server_ids_from_role(role_id)
            role["servers"] = server_ids
            # logger.debug("role: ({}) {}".format(role_id, role))
            return role
        # logger.debug("role: ({}) {}".format(role_id, {}))
        return {}
