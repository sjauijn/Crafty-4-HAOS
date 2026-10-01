import json
import logging

import httpx

logger = logging.getLogger(__name__)


class NitradoPing:

    @staticmethod
    def ping(ip: str, port: int) -> dict:
        """Pings server query URL and port looking for Nitrado stats plugin on hytale
        server https://github.com/nitrado/hytale-plugin-query

        Args:
            ip (str): IP of server instance
            port (int): Port of server instance

        Returns:
            dict: returns dict response with structure defined in nitrado query docs
        """
        url = f"https://{ip}:{port}/Nitrado/Query"
        try:
            response = httpx.get(url, verify=False, timeout=1)  # Local query to server
            if response.status_code == 200:
                return response.json()
            raise httpx.ConnectError(
                f"Invalid response status code of {response.status_code}"
            )
        except (
            httpx.ConnectTimeout,
            httpx.ConnectError,
            json.decoder.JSONDecodeError,
        ) as why:
            logger.debug("Failed to get stats from Hytale server with error %s", why)
            return {}

    @staticmethod
    def parse_ping_response(response: dict) -> dict:
        """Parses dict object with response from ping

        Args:
            response (dict): Dict object from ping method call

        Returns:
            tuple: length of three tuple server data, universe data, player data
        """
        server = response.get("Server", {})
        universe = response.get("Universe", {})
        players = response.get("Players", [])
        return {
            "online": universe.get("CurrentPlayers", 0),
            "max": server.get("MaxPlayers", 0),
            "players": players,
            "server_description": server.get("Name", False),
            "server_version": server.get("Version", False),
            "server_icon": None,
        }
