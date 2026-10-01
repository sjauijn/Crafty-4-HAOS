import logging
import datetime
from peewee import (
    ForeignKeyField,
    CharField,
    IntegerField,
    DateTimeField,
    FloatField,
    TextField,
    AutoField,
    BooleanField,
)
from playhouse.shortcuts import model_to_dict

from app.classes.models.base_model import BaseModel
from app.classes.models.users import HelperUsers
from app.classes.models.servers import Servers
from app.classes.helpers.helpers import Helpers
from app.classes.shared.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("audit_log")


# **********************************************************************************
#                                Crafty Settings Class
# **********************************************************************************
class CraftySettings(BaseModel):
    id = AutoField()
    secret_api_key = CharField(default="")
    cookie_secret = CharField(default="")
    login_photo = CharField(default="login_1.jpg")
    login_opacity = IntegerField(default=100)
    master_server_dir = CharField(default="")

    class Meta:
        table_name = "crafty_settings"


# **********************************************************************************
#                                   Host_Stats Class
# **********************************************************************************
class HostStats(BaseModel):
    time = DateTimeField(default=datetime.datetime.now, index=True)
    boot_time = CharField(default="")
    cpu_usage = FloatField(default=0)
    cpu_cores = IntegerField(default=0)
    cpu_cur_freq = FloatField(default=0)
    cpu_max_freq = FloatField(default=0)
    mem_percent = FloatField(default=0)
    mem_usage = CharField(default="")
    mem_total = CharField(default="")
    disk_json = TextField(default="")

    class Meta:
        table_name = "host_stats"


# **********************************************************************************
#                                   Webhooks Class
# **********************************************************************************
class Webhooks(BaseModel):
    id = AutoField()
    server_id = ForeignKeyField(Servers, backref="webhook_server", null=True)
    name = CharField(default="Custom Webhook", max_length=64)
    url = CharField(default="")
    webhook_type = CharField(default="Custom")
    bot_name = CharField(default="Crafty Controller")
    trigger = CharField(default="server_start,server_stop")
    body = CharField(default="")
    color = CharField(default="#005cd1")
    enabled = BooleanField(default=True)

    class Meta:
        table_name = "webhooks"


# **********************************************************************************
#                                   Schedules Class
# **********************************************************************************
class Schedules(BaseModel):
    schedule_id = IntegerField(unique=True, primary_key=True)
    server_id = ForeignKeyField(Servers, backref="schedule_server")
    enabled = BooleanField()
    action = CharField()
    interval = IntegerField()
    interval_type = CharField()
    start_time = CharField(null=True)
    command = CharField(null=True)
    action_id = CharField(null=True)
    name = CharField()
    one_time = BooleanField(default=False)
    cron_string = CharField(default="")
    parent = IntegerField(null=True)
    delay = IntegerField(default=0)
    next_run = CharField(default="")

    class Meta:
        table_name = "schedules"


# **********************************************************************************
#                                   Backups Class
# **********************************************************************************
class Backups(BaseModel):
    backup_id = CharField(primary_key=True, default=Helpers.create_uuid)
    backup_name = CharField(default="New Backup")
    backup_location = CharField(default="")
    excluded_dirs = CharField(null=True)
    max_backups = IntegerField(default=0)
    server_id = ForeignKeyField(Servers, backref="backups_server")
    compress = BooleanField(default=False)
    shutdown = BooleanField(default=False)
    before = CharField(default="")
    after = CharField(default="")
    default = BooleanField(default=False)
    status = CharField(default='{"status": "Standby", "message": ""}')
    enabled = BooleanField(default=True)
    backup_type = CharField(default="zip_vault")

    class Meta:
        table_name = "backups"


class HelpersManagement:
    def __init__(self, database, helper):
        self.database = database
        self.helper = helper

    # **********************************************************************************
    #                                   Host_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_latest_hosts_stats():
        # pylint: disable=no-member
        query = HostStats.select().order_by(HostStats.id.desc()).get()
        return model_to_dict(query)

    # **********************************************************************************
    #                                   Audit_Log Methods
    # **********************************************************************************

    def add_to_audit_log(
        self, user_id, log_msg, server_id=None, source_ip=None, notify=True
    ):
        logger.debug(f"Adding to audit log User:{user_id} - Message: {log_msg} ")
        user_data = HelperUsers.get_user(user_id)

        audit_msg = f"{str(user_data['username']).capitalize()} {log_msg}"

        if notify:
            try:
                WebSocketManager().broadcast_to_server_users(
                    server_id, "notification", audit_msg
                )
            except Exception as e:
                logger.exception(f"Error broadcasting to server users - {e}")
        auth_logger.info(
            str(log_msg),
            extra={
                "user_name": user_data["username"],
                "user_id": user_id,
                "server_id": server_id,
                "source_ip": source_ip,
            },
        )

    def add_to_audit_log_raw(self, user_name, user_id, server_id, log_msg, source_ip):
        if isinstance(server_id, Servers) and server_id is not None:
            server_id = server_id.server_id
        auth_logger.info(
            str(log_msg),
            extra={
                "user_name": user_name,
                "user_id": user_id,
                "server_id": server_id,
                "source_ip": source_ip,
            },
        )

    @staticmethod
    def create_crafty_row():
        CraftySettings.insert(
            {
                CraftySettings.secret_api_key: "",
                CraftySettings.cookie_secret: "",
                CraftySettings.login_photo: "login_1.jpg",
                CraftySettings.login_opacity: 100,
            }
        ).execute()

    @staticmethod
    def set_secret_api_key(key):
        CraftySettings.update({CraftySettings.secret_api_key: key}).where(
            CraftySettings.id == 1
        ).execute()

    @staticmethod
    def get_secret_api_key():
        settings = (
            CraftySettings.select(CraftySettings.secret_api_key)
            .where(CraftySettings.id == 1)
            .first()
        )
        return settings.secret_api_key

    @staticmethod
    def get_cookie_secret():
        settings = (
            CraftySettings.select(CraftySettings.cookie_secret)
            .where(CraftySettings.id == 1)
            .first()
        )
        return settings.cookie_secret

    @staticmethod
    def set_cookie_secret(key):
        CraftySettings.update({CraftySettings.cookie_secret: key}).where(
            CraftySettings.id == 1
        ).execute()

    # **********************************************************************************
    #                                  Config Methods
    # **********************************************************************************
    @staticmethod
    def get_login_image():
        settings = CraftySettings.select(CraftySettings.login_photo).where(
            CraftySettings.id == 1
        )
        settings = settings.first()
        return settings.login_photo

    @staticmethod
    def set_login_image(photo):
        CraftySettings.update({CraftySettings.login_photo: photo}).where(
            CraftySettings.id == 1
        ).execute()

    @staticmethod
    def get_login_opacity():
        settings = CraftySettings.select(CraftySettings.login_opacity).where(
            CraftySettings.id == 1
        )
        settings = settings.first()
        return settings.login_opacity

    @staticmethod
    def set_login_opacity(opacity):
        CraftySettings.update({CraftySettings.login_opacity: opacity}).where(
            CraftySettings.id == 1
        ).execute()

    @staticmethod
    def get_master_server_dir():
        settings = CraftySettings.select(CraftySettings.master_server_dir).where(
            CraftySettings.id == 1
        )
        settings = settings.first()
        return settings.master_server_dir

    @staticmethod
    def set_master_server_dir(server_dir):
        CraftySettings.update({CraftySettings.master_server_dir: server_dir}).where(
            CraftySettings.id == 1
        ).execute()

    # **********************************************************************************
    #                                  Schedules Methods
    # **********************************************************************************
    @staticmethod
    def create_scheduled_task(
        server_id,
        action,
        interval,
        interval_type,
        start_time,
        command,
        name,
        enabled=True,
        one_time=False,
        cron_string="* * * * *",
        parent=None,
        delay=0,
        action_id=None,
    ):
        sch_id = Schedules.insert(
            {
                Schedules.server_id: server_id,
                Schedules.action: action,
                Schedules.enabled: enabled,
                Schedules.interval: interval,
                Schedules.interval_type: interval_type,
                Schedules.start_time: start_time,
                Schedules.command: command,
                Schedules.action_id: action_id,
                Schedules.name: name,
                Schedules.one_time: one_time,
                Schedules.cron_string: cron_string,
                Schedules.parent: parent,
                Schedules.delay: delay,
                Schedules.next_run: "",
            }
        ).execute()
        return sch_id

    @staticmethod
    def delete_scheduled_task(schedule_id):
        return Schedules.delete().where(Schedules.schedule_id == schedule_id).execute()

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        Schedules.update(updates).where(Schedules.schedule_id == schedule_id).execute()

    @staticmethod
    def delete_scheduled_task_by_server(server_id):
        Schedules.delete().where(Schedules.server_id == server_id).execute()

    @staticmethod
    def get_scheduled_task(schedule_id):
        return model_to_dict(Schedules.get(Schedules.schedule_id == schedule_id))

    @staticmethod
    def get_scheduled_task_model(schedule_id):
        return Schedules.select().where(Schedules.schedule_id == schedule_id).get()

    @staticmethod
    def get_schedules_by_server(server_id):
        return Schedules.select().where(Schedules.server_id == server_id).execute()

    @staticmethod
    def get_child_schedules_by_server(schedule_id, server_id):
        return (
            Schedules.select()
            .where(Schedules.server_id == server_id, Schedules.parent == schedule_id)
            .execute()
        )

    @staticmethod
    def get_child_schedules(schedule_id):
        return Schedules.select().where(Schedules.parent == schedule_id)

    @staticmethod
    def get_schedules_all():
        return Schedules.select().execute()

    @staticmethod
    def get_schedules_enabled():
        return (
            Schedules.select()
            .where(Schedules.enabled == True)  # pylint: disable=singleton-comparison
            .execute()
        )

    # **********************************************************************************
    #                                   Backups Methods
    # **********************************************************************************
    @staticmethod
    def get_backup_config(backup_id):
        return model_to_dict(Backups.get(Backups.backup_id == backup_id))

    @staticmethod
    def get_backups_by_server(server_id, model=False):
        if not model:
            data = {}
            for backup in (
                Backups.select().where(Backups.server_id == server_id).execute()
            ):
                data[str(backup.backup_id)] = {
                    "backup_id": backup.backup_id,
                    "backup_name": backup.backup_name,
                    "backup_location": backup.backup_location,
                    "excluded_dirs": backup.excluded_dirs,
                    "max_backups": backup.max_backups,
                    "server_id": backup.server_id_id,
                    "compress": backup.compress,
                    "shutdown": backup.shutdown,
                    "before": backup.before,
                    "after": backup.after,
                    "default": backup.default,
                    "enabled": backup.enabled,
                    "backup_type": backup.backup_type,
                }
        else:
            data = Backups.select().where(Backups.server_id == server_id).execute()
        return data

    @staticmethod
    def get_default_server_backup(server_id: str) -> dict:
        bu_query = Backups.select().where(
            Backups.server_id == server_id,
            Backups.default == True,  # pylint: disable=singleton-comparison
        )
        backup_model = bu_query.first()

        if backup_model:
            return model_to_dict(backup_model)
        raise IndexError

    @staticmethod
    def remove_all_server_backups(server_id):
        Backups.delete().where(Backups.server_id == server_id).execute()

    @staticmethod
    def remove_backup_config(backup_id):
        Backups.delete().where(Backups.backup_id == backup_id).execute()
        # Delete associated task when deleting backup config
        Schedules.delete().where(Schedules.action_id == backup_id).execute()

    def add_backup_config(self, conf) -> str:
        if "excluded_dirs" in conf:
            dirs_to_exclude = ",".join(conf["excluded_dirs"])
            conf["excluded_dirs"] = dirs_to_exclude
        if len(self.get_backups_by_server(conf["server_id"], True)) <= 0:
            conf["default"] = True
        backup = Backups.create(**conf)
        logger.debug("Creating new backup record.")
        return backup.backup_id

    @staticmethod
    def update_backup_config(backup_id, data):
        if "excluded_dirs" in data:
            dirs_to_exclude = ",".join(data["excluded_dirs"])
            data["excluded_dirs"] = dirs_to_exclude
        Backups.update(**data).where(Backups.backup_id == backup_id).execute()

    @staticmethod
    def get_excluded_backup_dirs(backup_id: int):
        excluded_dirs = HelpersManagement.get_backup_config(backup_id)["excluded_dirs"]
        if excluded_dirs is not None and excluded_dirs != "":
            dir_list = excluded_dirs.split(",")
        else:
            dir_list = []
        return dir_list


# **********************************************************************************
#                                   Webhooks Class
# **********************************************************************************
class HelpersWebhooks:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def create_webhook(create_data) -> int:
        """Create a webhook in the database

        Args:
            server_id: ID of a server this webhook will be married to
            name: The name of the webhook
            url: URL to the webhook
            webhook_type: The provider this webhook will be sent to
            bot name: The name that will appear when the webhook is sent
            triggers: Server actions that will trigger this webhook
            body: The message body of the webhook
            enabled: Should Crafty trigger the webhook

        Returns:
            int: The new webhooks's id

        Raises:
            PeeweeException: If the webhook already exists
        """
        return Webhooks.insert(
            {
                Webhooks.server_id: create_data["server_id"],
                Webhooks.name: create_data["name"],
                Webhooks.webhook_type: create_data["webhook_type"],
                Webhooks.url: create_data["url"],
                Webhooks.bot_name: create_data["bot_name"],
                Webhooks.body: create_data["body"],
                Webhooks.color: create_data["color"],
                Webhooks.trigger: create_data["trigger"],
                Webhooks.enabled: create_data["enabled"],
            }
        ).execute()

    @staticmethod
    def modify_webhook(webhook_id, updata):
        Webhooks.update(updata).where(Webhooks.id == webhook_id).execute()

    @staticmethod
    def get_webhook_by_id(webhook_id):
        return model_to_dict(Webhooks.get(Webhooks.id == webhook_id))

    @staticmethod
    def get_webhooks_by_server(server_id, model):
        if not model:
            data = {}
            for webhook in (
                Webhooks.select().where(Webhooks.server_id == server_id).execute()
            ):
                data[str(webhook.id)] = {
                    "webhook_type": webhook.webhook_type,
                    "name": webhook.name,
                    "url": webhook.url,
                    "bot_name": webhook.bot_name,
                    "trigger": webhook.trigger,
                    "body": webhook.body,
                    "color": webhook.color,
                    "enabled": webhook.enabled,
                }
        else:
            data = Webhooks.select().where(Webhooks.server_id == server_id).execute()
        return data

    @staticmethod
    def delete_webhook(webhook_id):
        Webhooks.delete().where(Webhooks.id == webhook_id).execute()

    @staticmethod
    def delete_webhooks_by_server(server_id):
        Webhooks.delete().where(Webhooks.server_id == server_id).execute()
