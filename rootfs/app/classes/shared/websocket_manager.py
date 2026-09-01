import json
import logging
from peewee import DoesNotExist

from app.classes.shared.singleton import Singleton
from app.classes.shared.console import Console
from app.classes.models.users import HelperUsers
from app.classes.models.server_permissions import (
    PermissionsServers,
)

logger = logging.getLogger(__name__)


class WebSocketManager(metaclass=Singleton):
    """Track active WebSocket clients and broadcast events to matching clients."""

    def __init__(self):
        """Initialize the shared client registry."""
        self.clients = set()

    def add_client(self, client):
        """Register a WebSocket client for future broadcasts.

        Args:
            client: WebSocket handler instance that implements the methods used
                by this manager, such as ``send_message`` and ``get_user_id``.
        """
        self.clients.add(client)

    def remove_client(self, client):
        """Remove a WebSocket client from the registry.

        Args:
            client: WebSocket handler instance to remove.
        """
        if client in self.clients:
            self.clients.remove(client)
        else:
            logger.exception("Error caught while removing unknown WebSocket client")

    def broadcast(self, event_type: str, data):
        """Send an event to every connected WebSocket client.

        Args:
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """
        logger.debug(
            f"Sending to {len(self.clients)} clients: "
            f"{json.dumps({'event': event_type, 'data': data})}"
        )
        for client in self.clients:
            try:
                client.send_message(event_type, data)
            except Exception as e:
                logger.exception(
                    f"Error caught while sending WebSocket message to "
                    f"{client.get_remote_ip()} {e}"
                )

    def broadcast_to_admins(self, event_type: str, data):
        """Send an event to connected clients whose users are super users.

        Args:
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """

        def filter_fn(client):
            if str(client.get_user_id()) in str(HelperUsers.get_super_user_list()):
                return True
            return False

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_to_non_admins(self, event_type: str, data):
        """Send an event to connected clients whose users are not super users.

        Args:
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """

        def filter_fn(client):
            if str(client.get_user_id()) not in str(HelperUsers.get_super_user_list()):
                return True
            return False

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_page(self, page: str, event_type: str, data):
        """Send an event to clients currently viewing a specific page.

        Args:
            page (str): Page path recorded on the WebSocket client.
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """

        def filter_fn(client):
            return client.page == page

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_user(self, user_id: str, event_type: str, data):
        """Send an event to all connected clients for a specific user.

        Args:
            user_id (str): User id returned by the WebSocket client.
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """

        def filter_fn(client):
            return client.get_user_id() == user_id

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_to_server_users(self, server_id: str, event_type: str, data):
        """Send an event to users with permission to access a server.

        Args:
            server_id (str): Server id used to look up permitted users.
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """
        server_users = PermissionsServers.get_server_user_list(server_id)
        for user in server_users:
            self.broadcast_user(user, event_type, data)

    def broadcast_user_page(self, page: str, user_id: str, event_type: str, data):
        """Send an event to a user's clients on a specific page.

        Args:
            page (str): Page path recorded on the WebSocket client.
            user_id (str): User id returned by the WebSocket client.
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """

        def filter_fn(client):
            if client.get_user_id() != user_id:
                return False
            if client.page != page:
                return False
            return True

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_page_params(
        self, page: str, params: dict, event_type: str, data, **kwargs
    ):
        """Send an event to clients on a page with matching query params.

        Args:
            page (str): Page path, for example ``"/panel/server_detail"``.
            params (dict): Query parameters that must match the client's page
                query parameters.
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
            **kwargs: Optional filters. Supports ``required_permission`` to
                require a server permission before sending to a client.
        """

        def filter_fn(client):
            kwarg_perms = kwargs.get("required_permission")
            try:
                user_perms = PermissionsServers.get_user_id_permissions_list(
                    client.get_user_id(), params.get("id", "")
                )
            except DoesNotExist as why:
                logger.exception(
                    "User perms not found for websocket filter terminal buffer: %s",
                    why,
                )
                user_perms = []
            if kwarg_perms and (kwarg_perms not in user_perms):
                # Only send data to users with proper permission
                return False
            if client.page != page:
                return False
            for key, param in params.items():
                if param != client.page_query_params.get(key, None):
                    return False
            return True

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_with_fn(self, filter_fn, event_type: str, data):
        """Send an event to clients accepted by a filter callback.

        Args:
            filter_fn: Callable that receives a client and returns ``True`` when
                the client should receive the event.
            event_type (str): Client-side event name to emit.
            data: JSON-serializable payload for the event.
        """
        # assign self.clients to a static variable here so hopefully
        # the set size won't change
        static_clients = self.clients
        clients = list(filter(filter_fn, static_clients.copy()))
        logger.debug(
            f"Sending to {len(clients)}  \
            out of {len(self.clients)} "
            f"clients: {json.dumps({'event': event_type, 'data': data})}"
        )

        for client in clients[:]:
            try:
                client.send_message(event_type, data)
            except Exception as e:
                logger.exception(
                    f"Error catched while sending WebSocket message to "
                    f"{client.get_remote_ip()} {e}"
                )

    def disconnect_all(self):
        """Close every connected WebSocket client."""
        Console.info("Disconnecting WebSocket clients")
        for client in self.clients:
            client.close()
        Console.info("Disconnected WebSocket clients")
