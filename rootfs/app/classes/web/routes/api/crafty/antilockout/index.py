import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)
auth_log = logging.getLogger("auth")


class ApiCraftyLockoutHandler(BaseApiHandler):
    def get(self):
        auth_log.warning(f"Anti-Lockout request from {self.get_remote_ip()}")
        self.controller.log_antilockout(self.get_remote_ip())

        if self.controller.users.get_id_by_name("anti-lockout-user"):
            return self.finish_json(
                425, {"status": "error", "data": "Lockout recovery already in progress"}
            )
        self.controller.users.start_anti_lockout()
        lockout_msg = (
            "Lockout account has been activated for 1 hour."
            " Please find temporary credentials in the terminal"
        )
        return self.finish_json(
            200,
            {
                "status": "ok",
                "data": lockout_msg,
            },
        )
