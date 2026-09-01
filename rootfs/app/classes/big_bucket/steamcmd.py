import logging
from enum import Enum

logger = logging.Logger(__name__)


class OS(Enum):
    LINUX = "linux"
    WINDOWS = "windows"


class SteamGame:
    def __init__(self, input_dict: dict[str, str | bool | list[str]]):
        try:
            self.name: str = input_dict["name"]
            self.id: str = str(input_dict["id"])
            self.anonymous: bool = input_dict["anonymous"]
            os_list: list[str] = input_dict["os"]
            self.windows_startup_command: str = input_dict["windows_startup_command"]
            self.unix_startup_command: str = input_dict["unix_startup_command"]

        except KeyError as why:
            logger.exception(f"error reading steamcmd config: {why}")

        self.os: list[OS] = []

        for os in os_list:
            if os == "linux":
                self.os.append(OS.LINUX)
            if os == "windows":
                self.os.append(OS.WINDOWS)


class SteamCMD:
    def __init__(self, input_dict: dict[str, int | dict[str, str | bool | list[str]]]):
        self.version: int = input_dict["version"]
        self.games: list[SteamGame] = [SteamGame(g) for g in input_dict["games"]]

    def get_game_by_id(self, game_id: int) -> SteamGame:
        try:
            return next(g for g in self.games if g.id == game_id)
        except StopIteration as exc:
            raise KeyError(f"Game with id {id} not found") from exc

    def get_list_of_games_by_os(self, os: OS | None) -> list[SteamGame]:
        if os is None:
            return self.games
        return [g for g in self.games if os in g.os]
