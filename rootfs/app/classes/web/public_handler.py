import logging
import nh3

from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)
auth_log = logging.getLogger("auth")


class PublicHandler(BaseHandler):
    def get(self, page=None):
        # pylint: disable=no-member
        error = nh3.clean(self.get_argument("error", "Invalid Login!"))
        error_msg = nh3.clean(self.get_argument("error_msg", ""))
        # pylint: enable=no-member

        page_data = {
            "version": self.helper.get_version_string(),
            "error": error,
            "lang": self.helper.get_setting("language"),
            "lang_page": self.helper.get_lang_page(self.helper.get_setting("language")),
            "query": "",
            "background": self.controller.cached_login,
            "login_opacity": self.controller.management.get_login_opacity(),
            "themes": self.helper.get_themes(),
        }

        if self.request.query:
            request_query = self.request.query_arguments.get("next")
            if not request_query:
                self.redirect("/login")
            page_data["query"] = request_query[0].decode()

        # sensible defaults
        template = "public/404.html"

        if page == "login":
            template = "public/login.html"

        elif page == "404":
            template = "public/404.html"

        elif page == "error":
            template = "public/error.html"

        elif page == "offline":
            template = "public/offline.html"

        elif page == "logout":
            exec_user = self.get_current_user()
            self.clear_cookie("token")
            # Delete anti-lockout-user on lockout...it's one time use
            if exec_user[2]["username"] == "anti-lockout-user":
                self.controller.users.stop_anti_lockout()
            # self.clear_cookie("user")
            # self.clear_cookie("user_data")
            self.redirect("/login")
            return

        # if we have no page, let's go to login
        else:
            return self.redirect("/login")

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
            error_msg=error_msg,
        )

    def post(self, _page=None):
        self.redirect("/login?")
