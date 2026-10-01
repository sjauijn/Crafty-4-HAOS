import logging
from app.classes.controllers.servers_controller import ServersController

from app.classes.models.server_permissions import (
    PermissionsServers,
    EnumPermissionsServer,
)
from app.classes.models.users import HelperUsers, ApiKeys
from app.classes.models.roles import HelperRoles
from app.classes.models.servers import HelperServers

logger = logging.getLogger(__name__)


class ServerPermsController:
    @staticmethod
    def get_server_user_list(server_id):
        return PermissionsServers.get_server_user_list(server_id)

    @staticmethod
    def get_permissions(permissions_mask):
        return PermissionsServers.get_permissions(permissions_mask)

    @staticmethod
    def list_defined_permissions():
        permissions_list = PermissionsServers.get_permissions_list()
        return permissions_list

    @staticmethod
    def get_mask_permissions(role_id, server_id):
        permissions_mask = PermissionsServers.get_permissions_mask(role_id, server_id)
        return permissions_mask

    @staticmethod
    def get_role_permissions_dict(role_id):
        return PermissionsServers.get_role_permissions_dict(role_id)

    @staticmethod
    def add_role_server(server_id, role_id, rs_permissions="00000000"):
        return PermissionsServers.add_role_server(server_id, role_id, rs_permissions)

    @staticmethod
    def get_server_roles(server_id):
        return PermissionsServers.get_server_roles(server_id)

    @staticmethod
    def backup_role_swap(old_server_id, new_server_id):
        role_list = PermissionsServers.get_server_roles(old_server_id)
        for role in role_list:
            PermissionsServers.add_role_server(
                new_server_id,
                role.role_id,
                PermissionsServers.get_permissions_mask(
                    int(role.role_id), old_server_id
                ),
            )
            # Permissions_Servers.add_role_server(
            #     new_server_id, role.role_id, "00001000"
            # )

    # **********************************************************************************
    #                                   Servers Permissions Methods
    # **********************************************************************************
    @staticmethod
    def get_permissions_mask(role_id, server_id):
        return PermissionsServers.get_permissions_mask(role_id, server_id)

    @staticmethod
    def get_lowest_api_perm_mask(user_server_permissions_mask, api_key_permssions_mask):
        mask = ""
        # If this isn't an API key we'll know the request came from basic
        # authentication and ignore the API key permissions mask.
        if not api_key_permssions_mask:
            return user_server_permissions_mask
        for _index, (user_perm, api_perm) in enumerate(
            zip(user_server_permissions_mask, api_key_permssions_mask)
        ):
            if user_perm == "1" and api_perm == "1":
                mask += "1"
            else:
                mask += "0"
        return mask

    @staticmethod
    def set_permission(
        permission_mask, permission_tested: EnumPermissionsServer, value
    ):
        return PermissionsServers.set_permission(
            permission_mask, permission_tested, value
        )

    @staticmethod
    def get_user_id_permissions_list(user_id: str, server_id: str):
        return PermissionsServers.get_user_id_permissions_list(user_id, server_id)

    @staticmethod
    def get_api_key_id_permissions_list(key_id: str, server_id: str):
        key = HelperUsers.get_user_api_key(key_id)
        return PermissionsServers.get_api_key_permissions_list(key, server_id)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys, server_id: str):
        return PermissionsServers.get_api_key_permissions_list(key, server_id)

    @staticmethod
    def get_user_permissions_mask(user_id: str, server_id: str):
        user = HelperUsers.get_user_model(user_id)
        return PermissionsServers.get_user_permissions_mask(user, server_id)

    @staticmethod
    def get_authorized_servers_stats_from_roles(user_id):
        user_roles = HelperUsers.get_user_roles_id(user_id)
        roles_list = []
        role_server = []
        authorized_servers = []
        server_data = []

        for user in user_roles:
            roles_list.append(HelperRoles.get_role(user.role_id))

        for role in roles_list:
            role_test = PermissionsServers.get_role_servers_from_role_id(
                role.get("role_id")
            )
            for test in role_test:
                role_server.append(test)

        for server in role_server:
            authorized_servers.append(
                HelperServers.get_server_data_by_id(server.server_id)
            )

        for server in authorized_servers:
            srv = ServersController().get_server_instance_by_id(server.get("server_id"))
            latest = srv.stats_helper.get_latest_server_stats()
            server_data.append(
                {
                    "server_data": server,
                    "stats": latest,
                }
            )
        return server_data
