import logging
import queue

from prometheus_client import CollectorRegistry, Gauge

from app.classes.models.management import HelpersManagement, HelpersWebhooks
from app.classes.models.servers import HelperServers
from app.classes.helpers.helpers import Helpers

logger = logging.getLogger(__name__)


class ManagementController:
    def __init__(self, management_helper):
        self.management_helper = management_helper
        self.command_queue = queue.Queue()
        self.host_registry = CollectorRegistry()
        self.init_host_registries()

    # **********************************************************************************
    #                                   Config Methods
    # **********************************************************************************
    @staticmethod
    def set_login_image(path):
        HelpersManagement.set_login_image(path)

    @staticmethod
    def get_login_image():
        return HelpersManagement.get_login_image()

    @staticmethod
    def set_login_opacity(opacity):
        return HelpersManagement.set_login_opacity(opacity)

    @staticmethod
    def get_login_opacity():
        return HelpersManagement.get_login_opacity()

    # **********************************************************************************
    #                                   Host_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_latest_hosts_stats():
        return HelpersManagement.get_latest_hosts_stats()

    @staticmethod
    def set_crafty_api_key(key):
        HelpersManagement.set_secret_api_key(key)

    @staticmethod
    def get_crafty_api_key():
        return HelpersManagement.get_secret_api_key()

    @staticmethod
    def set_cookie_secret(key):
        HelpersManagement.set_cookie_secret(key)

    @staticmethod
    def add_crafty_row():
        HelpersManagement.create_crafty_row()

    def init_host_registries(self):
        # REGISTRY Entries for Server Stats functions
        self.cpu_usage = Gauge(
            name="CPU_Usage",
            documentation="The CPU usage of the server",
            registry=self.host_registry,
        )
        self.mem_usage_percent = Gauge(
            name="Mem_Usage",
            documentation="The Memory usage of the server",
            registry=self.host_registry,
        )

    # **********************************************************************************
    #                                   Commands Methods
    # **********************************************************************************

    def send_command(self, user_id, server_id, remote_ip, command, action_id=None):
        server_name = HelperServers.get_server_friendly_name(server_id)

        # Example: Admin issued command start_server for server Survival
        self.management_helper.add_to_audit_log(
            user_id,
            f"issued command {command} for server {server_name}",
            server_id,
            remote_ip,
        )
        self.queue_command(
            {
                "server_id": server_id,
                "user_id": user_id,
                "command": command,
                "action_id": action_id,
            }
        )

    def queue_command(self, command_data):
        self.command_queue.put(command_data)

    # **********************************************************************************
    #                                   Audit_Log Methods
    # **********************************************************************************

    def add_to_audit_log(
        self, user_id, log_msg, server_id=None, source_ip=None, notify=True
    ):
        return self.management_helper.add_to_audit_log(
            user_id, log_msg, server_id, source_ip, notify
        )

    def add_to_audit_log_raw(self, user_name, user_id, server_id, log_msg, source_ip):
        return self.management_helper.add_to_audit_log_raw(
            user_name, user_id, server_id, log_msg, source_ip
        )

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
        return HelpersManagement.create_scheduled_task(
            server_id,
            action,
            interval,
            interval_type,
            start_time,
            command,
            name,
            enabled,
            one_time,
            cron_string,
            parent,
            delay,
            action_id,
        )

    @staticmethod
    def delete_scheduled_task(schedule_id):
        return HelpersManagement.delete_scheduled_task(schedule_id)

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        return HelpersManagement.update_scheduled_task(schedule_id, updates)

    @staticmethod
    def get_scheduled_task(schedule_id):
        return HelpersManagement.get_scheduled_task(schedule_id)

    @staticmethod
    def get_scheduled_task_model(schedule_id):
        return HelpersManagement.get_scheduled_task_model(schedule_id)

    @staticmethod
    def get_child_schedules(sch_id):
        return HelpersManagement.get_child_schedules(sch_id)

    @staticmethod
    def get_schedules_by_server(server_id):
        return HelpersManagement.get_schedules_by_server(server_id)

    @staticmethod
    def get_schedules_all():
        return HelpersManagement.get_schedules_all()

    @staticmethod
    def get_schedules_enabled():
        return HelpersManagement.get_schedules_enabled()

    # **********************************************************************************
    #                                   Backups Methods
    # **********************************************************************************
    @staticmethod
    def get_backup_config(backup_id):
        return HelpersManagement.get_backup_config(backup_id)

    @staticmethod
    def get_backups_by_server(server_id, model=False):
        return HelpersManagement.get_backups_by_server(server_id, model)

    @staticmethod
    def delete_backup_config(backup_id):
        HelpersManagement.remove_backup_config(backup_id)

    @staticmethod
    def update_backup_config(backup_id, updates):
        if "backup_location" in updates:
            updates["backup_location"] = Helpers.wtol_path(updates["backup_location"])
        return HelpersManagement.update_backup_config(backup_id, updates)

    def add_backup_config(self, data) -> str:
        if "backup_location" in data:
            data["backup_location"] = Helpers.wtol_path(data["backup_location"])
        return self.management_helper.add_backup_config(data)

    def add_default_backup_config(self, server_id, backup_path):
        return self.management_helper.add_backup_config(
            {
                "backup_name": "Default Backup",
                "backup_location": Helpers.wtol_path(backup_path),
                "max_backups": 0,
                "before": "",
                "after": "",
                "compress": False,
                "shutdown": False,
                "server_id": server_id,
                "excluded_dirs": [],
                "default": True,
            }
        )

    @staticmethod
    def get_excluded_backup_dirs(backup_id: int):
        return HelpersManagement.get_excluded_backup_dirs(backup_id)

    def add_excluded_backup_dir(self, server_id: int, dir_to_add: str):
        self.management_helper.add_excluded_backup_dir(server_id, dir_to_add)

    def del_excluded_backup_dir(self, server_id: int, dir_to_del: str):
        self.management_helper.del_excluded_backup_dir(server_id, dir_to_del)

    # **********************************************************************************
    #                                   Crafty Methods
    # **********************************************************************************
    @staticmethod
    def get_master_server_dir():
        return HelpersManagement.get_master_server_dir()

    @staticmethod
    def set_master_server_dir(server_dir):
        HelpersManagement.set_master_server_dir(server_dir)

    # **********************************************************************************
    #                                   Webhooks Methods
    # **********************************************************************************
    @staticmethod
    def create_webhook(data):
        return HelpersWebhooks.create_webhook(data)

    @staticmethod
    def modify_webhook(webhook_id, data):
        HelpersWebhooks.modify_webhook(webhook_id, data)

    @staticmethod
    def get_webhook_by_id(webhook_id):
        return HelpersWebhooks.get_webhook_by_id(webhook_id)

    @staticmethod
    def get_webhooks_by_server(server_id, model=False):
        return HelpersWebhooks.get_webhooks_by_server(server_id, model)

    @staticmethod
    def delete_webhook(webhook_id):
        HelpersWebhooks.delete_webhook(webhook_id)

    @staticmethod
    def delete_webhook_by_server(server_id):
        HelpersWebhooks.delete_webhooks_by_server(server_id)
