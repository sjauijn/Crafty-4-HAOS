import json
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)
# Temp type var until sjars restores generic fetchTypes0


class BigBucket:
    def __init__(self, helper):
        self.helper = helper
        # remove any trailing slash from config.json
        # url since we add it on all the calls
        self.base_url = str(
            self.helper.get_setting("big_bucket_repo", "https://jars.arcadiatech.org")
        ).rstrip("/")

    def _read_cache(self, cache_file: str | None = None) -> dict:
        if not cache_file:
            cache_file = self.helper.big_bucket_minecraft_cache
        cache = {}
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)

        except Exception as e:
            logger.exception(f"Unable to read big_bucket cache file: {e}")

        return cache

    def get_bucket_data(self, cache_file: str | None = None) -> dict | None:
        data = self._read_cache(cache_file)
        return data.get("categories")

    def _check_bucket_alive(self) -> bool:
        logger.info("Checking Big Bucket status")

        check_url = f"{self.base_url}/healthcheck"
        try:
            response = requests.get(check_url, timeout=2)
            response_json = response.json()
            if (
                response.status_code in [200, 201]
                and response_json.get("status") == "ok"
            ):
                logger.info("Big bucket is alive and responding as expected")
                return True
        except Exception as e:
            logger.exception(f"Unable to connect to big bucket due to error: {e}")
            return False

        logger.error(
            "Big bucket manifest is not available as expected or unable to contact"
        )
        return False

    def _get_big_bucket(self, remote_file: str = "manifest.json") -> dict:
        logger.debug("Calling for big bucket manifest.")
        try:
            response = requests.get(f"{self.base_url}/{remote_file}", timeout=5)
            if response.status_code in [200, 201]:
                data = response.json()
                try:
                    del data["manifest_version"]
                except KeyError:
                    logger.debug("No manifest version found")
                return data
            return {}
        except (
            TimeoutError,
            ConnectionError,
            requests.exceptions.ConnectionError,
        ) as e:
            logger.exception(f"Unable to get jars from remote with error {e}")
            return {}

    def _refresh_cache(
        self,
        out_file: str,
        remote_file: str = "manifest.json",
    ):
        """
        Contains the shared logic for refreshing the cache.
        This method is called by both manual_refresh_cache and refresh_cache methods.
        """
        if not self._check_bucket_alive():
            logger.error("big bucket API is not available.")
            return False

        cache_data = {
            "last_refreshed": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            "categories": self._get_big_bucket(remote_file),
        }
        try:
            with open(out_file, "w", encoding="utf-8") as cache_file:
                json.dump(cache_data, cache_file, indent=4)
                logger.info("Cache file successfully refreshed manually.")
        except Exception as e:
            logger.exception(f"Failed to update cache file manually: {e}")

    def manual_refresh_cache(self):
        """
        Manually triggers the cache refresh process.
        """
        logger.info("Manual bucket cache refresh initiated.")
        self._refresh_cache(self.helper.big_bucket_minecraft_cache)
        logger.info("Manual refresh completed.")

    def refresh_cache(self):
        """
        Automatically trigger cache refresh process based age.

        This method checks if the cache file is older than a specified number of days
        before deciding to refresh.
        """

        cache_log_message = "Automatic cache refresh initiated on %s due to old cache."
        cache_file_path = self.helper.big_bucket_minecraft_cache

        # Determine if the cache is old and needs refreshing
        cache_old = self.helper.is_file_older_than_x_days(cache_file_path)

        # debug override
        # cache_old = True

        if self._check_bucket_alive() and cache_old:
            logger.info(
                cache_log_message,
                cache_file_path,
            )
            self._refresh_cache(cache_file_path)

        cache_file_path = self.helper.big_bucket_hytale_cache

        # Determine if the cache is old and needs refreshing
        cache_old = self.helper.is_file_older_than_x_days(cache_file_path)

        # debug override
        # cache_old = True

        if self._check_bucket_alive() and cache_old:
            logger.info(cache_log_message, cache_file_path)
            self._refresh_cache(cache_file_path, "hytale.json")

        cache_file_path = self.helper.big_bucket_steamapps_cache

        # Determine if the cache is old and needs refreshing
        cache_old = self.helper.is_file_older_than_x_days(cache_file_path)

        # debug override
        # cache_old = True

        if self._check_bucket_alive() and cache_old:
            logger.info(cache_log_message, cache_file_path)
            self._refresh_cache(cache_file_path, "steamcmd.json")

    def get_fetch_url(self, jar, server, version) -> str | None:
        """
        Constructs the URL for downloading a server JAR file based on the server type.
        Parameters:
            jar (str): The category of the JAR file to download.
            server (str): Server software name (e.g., "paper").
            version (str): Server version.

        Returns:
            str or None: URL for downloading the JAR file, or None if URL cannot be
                        constructed or an error occurs.
        """
        try:
            # Read cache file for URL that is in a list of one item
            return self.get_bucket_data()[jar]["types"][server]["versions"][version][
                "url"
            ][0]
        except Exception as e:
            logger.exception(f"An error occurred while constructing fetch URL: {e}")
            return None
