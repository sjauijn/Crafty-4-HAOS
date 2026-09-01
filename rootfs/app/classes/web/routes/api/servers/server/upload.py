import os
from pathlib import Path

from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.routes.api.crafty.upload.index import ApiFilesUploadHandler


class ApiServerFilesUpload(ApiFilesUploadHandler):
    async def post(self, server_id=None):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        # 1. Authorize user and resolve types
        try:
            auth_result = self._authorize_upload(auth_data, server_id)
        except PermissionError:
            return self._finish_unauthorized(auth_data)
        accepted_types = auth_result

        # 2. Extract and validate headers/paths
        if not self._parse_and_validate_request(accepted_types):
            return self._finish_unauthorized(auth_data)
        try:
            self._check_traversal(server_id)
        except ValueError:
            return self._finish_unauthorized(auth_data)
        # 3. Check disk space
        file_size = int(self.request.headers.get("fileSize", 0))
        total_chunks = int(self.request.headers.get("totalChunks", 0))
        if not self._has_enough_space(self.upload_dir, file_size):
            return self.finish_json(
                507,
                {
                    "status": "error",
                    "error": "NO STORAGE SPACE",
                    "data": {"message": "Out Of Space!"},
                },
            )

        # 4. Handle early chunked initiation or structure prep
        if self.chunked and not self.chunk_index:
            return self.finish_json(
                200, {"status": "ok", "data": {"file-id": self.file_id}}
            )

        os.makedirs(self.upload_dir, exist_ok=True)

        # 5. Route to specific processor
        if not self.chunked:
            return await self._process_non_chunked(self.upload_dir)

        return await self._process_chunked(
            self.upload_dir, total_chunks, auth_data, server_id
        )

    def _authorize_upload(self, auth_data: tuple, server_id: str) -> list[str]:
        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            raise PermissionError("Unauthorized Access")
        mask = self.controller.server_perms.get_lowest_api_perm_mask(
            self.controller.server_perms.get_user_permissions_mask(
                auth_data[4]["user_id"], server_id
            ),
            auth_data[5],
        )
        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_permissions(mask)
        ):
            raise PermissionError("Unauthorized Access")
        return []

    def _check_traversal(self, server_id: str):
        server_path = Path(
            self.controller.management.get_master_server_dir(),
            server_id,
        )
        self.upload_dir = Path(
            self.file_helper.get_absolute_path(
                str(server_path), str(Path(server_path, self.location))
            )
        ).resolve()
        base_dir = Path(
            self.controller.management.get_master_server_dir(),
            server_id,
        ).resolve()
        self.helper.validate_traversal(
            base_dir, Path(self.upload_dir, self.filename).resolve()
        )
