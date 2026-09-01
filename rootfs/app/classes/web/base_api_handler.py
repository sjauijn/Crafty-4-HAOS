import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, Optional
import aiofiles
from tornado.iostream import StreamClosedError
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)


class BaseApiHandler(BaseHandler):
    # {{{ Disable XSRF protection on API routes
    def check_xsrf_cookie(self) -> None:
        pass

    # }}}

    # {{{ 405 Method Not Allowed as JSON
    def _unimplemented_method(self, *_args: str, **_kwargs: str) -> None:
        self.finish_json(
            405,
            {
                "status": "error",
                "error": "METHOD_NOT_ALLOWED",
                "error_data": "METHOD NOT ALLOWED",
            },
        )

    head = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    get = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    post = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    delete = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    patch = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    put = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    # }}}

    def options(self, *_, **__):
        """
        Fix CORS
        """
        # no body
        self.set_status(204)
        self.finish()

    async def download_file(self, file_path: Path):
        """THIS METHOD HAS NO TRAVERSAL DETECTION OR PERMISSION CHECKS! MAKE SURE TO
        CHECK FOR TRAVERSAL AND PERMISSION BEFORE CALLING THIS FUNCTION.

        Downloads file async in chunks

        Args:
            file_path (Path): pathlib Path object pointing to the intended file to
            download

        Returns:
            _type_: _description_
        """
        chunk_size = 4 * 1024 * 1024  # 4 MiB
        try:
            self.set_header("Content-Type", "application/octet-stream")
            self.set_header(
                "Content-Disposition", f'attachment; filename="{file_path.name}"'
            )

            async with aiofiles.open(file_path, "rb") as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        self.write(chunk)
                        await self.flush()
                    except StreamClosedError:
                        break
                    finally:
                        del chunk

        except Exception as e:
            print("Download error:", e)
            return self.finish_json(
                500,
                {
                    "status": "error",
                    "error": "Download error",
                    "error_data": f"ERROR: {e}",
                },
            )

    def can_modify_user(
        self, exec_user_crafty_permissions: list, auth_data: tuple, user_id: int | str
    ) -> bool:
        """Checks if exec user has permissions to modify target user

        Args:
            exec_user_crafty_permissions (list): Permissions of exec user returned
            from auth check
            auth_data (dict): Authenticated user information from auth check
            user_id (int): Target user ID

        Returns:
            bool: Returns true if user can edit target user
        """
        if int(auth_data[4]["user_id"]) == int(user_id) or str(user_id) == "@me":
            return True
        if auth_data[4]["superuser"]:
            return True
        if EnumPermissionsCrafty.USER_CONFIG in exec_user_crafty_permissions and int(
            user_id
        ) in self.controller.users.get_managed_users_ids(auth_data[4]["user_id"]):
            return True
        return False
