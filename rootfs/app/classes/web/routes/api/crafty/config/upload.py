import os
from pathlib import Path

from app.classes.web.routes.api.crafty.upload.index import ApiFilesUploadHandler

IMAGE_MIME_TYPES = [
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/pipeg",
    "image/tiff",
    "image/x-icon",
    "image/png",
    "image/webp",
]

CUSTOM_GRAPHICS = "app/frontend/static/assets/images/auth/custom"


class APICraftyCustomizeUpload(ApiFilesUploadHandler):
    async def post(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        try:
            # 1. Authorize user and resolve types
            accepted_types = self._authorize_upload(auth_data)
        except PermissionError:
            return self._finish_unauthorized(auth_data)

        # 2. Extract and validate headers/paths
        if not self._parse_and_validate_request(accepted_types):
            return
        try:
            self._check_traversal()
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

        return await self._process_chunked(self.upload_dir, total_chunks, auth_data)

    def _authorize_upload(self, auth_data: tuple) -> list[str]:
        if auth_data[4]["superuser"]:
            return IMAGE_MIME_TYPES
        raise PermissionError()

    def _check_traversal(self):
        self.upload_dir = Path(self.controller.project_root, CUSTOM_GRAPHICS)
        self.helper.validate_traversal(
            Path(self.controller.project_root, CUSTOM_GRAPHICS).resolve(),
            Path(self.upload_dir, self.filename).resolve(),
        )
