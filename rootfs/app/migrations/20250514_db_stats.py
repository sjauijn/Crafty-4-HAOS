import os

from app.classes.helpers.helpers import Helpers
from app.classes.helpers.file_helpers import FileHelpers
from app.classes.shared.console import Console

console = Console()
helper = Helpers()


def migrate(_migrator, _database, **kwargs):
    # Skip migration if servers dir does not exist
    if not os.path.exists(helper.servers_dir):
        return

    servers = os.listdir(helper.servers_dir)
    for server in servers:
        if os.path.exists(os.path.join(helper.servers_dir, server, "db_stats")):

            helper.ensure_dir_exists(
                os.path.join(helper.root_dir, "app", "config", "db", "servers", server)
            )
            console.debug(
                f"Found db_stats directory in server with ID {server}. Moving it"
            )
            for file in os.listdir(
                os.path.join(helper.servers_dir, server, "db_stats")
            ):
                FileHelpers.move_file(
                    os.path.join(helper.servers_dir, server, "db_stats", file),
                    os.path.join(
                        helper.root_dir, "app", "config", "db", "servers", server, file
                    ),
                )
            console.debug(f"Successfully moved stats DB for server with ID {server}")
