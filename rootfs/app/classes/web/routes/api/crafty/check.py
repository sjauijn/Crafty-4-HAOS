from app.classes.web.base_api_handler import BaseApiHandler


class ApiCraftyCheck(BaseApiHandler):
    def get(self):
        return self.finish_json(
            200,
            {
                "status": "ok",
            },
        )
