from app.classes.web.base_api_handler import BaseApiHandler

DOCS_API_LINK = "https://docs.craftycontrol.com/pages/developer-guide/api-reference/v2/"


class ApiIndexHandler(BaseApiHandler):
    def get(self):
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {
                    "version": self.controller.helper.get_version_string(),
                    "message": f"Please see the API documentation at {DOCS_API_LINK}",
                },
            },
        )
