from contextlib import redirect_stderr
import logging
import os
import socket
import time

from app.classes.shared.null_writer import NullWriter

with redirect_stderr(NullWriter()):
    import psutil

logger = logging.getLogger(__name__)


class RaknetPing:
    magic = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"
    field_sizes = {  # (len, signed)
        "byte": (1, False),
        "long": (8, True),
        "ulong": (8, False),
        "magic": (16, False),
        "short": (2, True),
        "ushort": (2, False),  # unsigned short
        "string": (2, False),  # strlen is ushort
        "bool": (1, False),
        "address": (7, False),
        "uint24le": (3, False),
    }
    byte_order = "big"
    pingpong_string_fields = [
        "server_edition",
        "server_motd",
        "server_protocol_version",
        "server_version_name",
        "server_player_count",
        "server_player_max",
        "server_uuid",
        "server_motd_2",
        "server_game_mode",
        "server_game_mode_num",
        "server_port_ipv4",
        "server_port_ipv6",
        "unknown_number_field_1",
        None,  # The Bedrock ping string response ends with a terminator, eat it
    ]

    def __init__(
        self, server_addr, server_port: int, client_guid: int = 0, timeout: int = 5
    ):
        self.addr = server_addr
        self.port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.proc = psutil.Process(os.getpid())
        self.guid = client_guid
        self.guid_bytes = self.guid.to_bytes(8, RaknetPing.byte_order)

    @staticmethod
    def __byter(in_val: str | int | bool, to_type: str) -> bytes:
        f = RaknetPing.field_sizes[to_type]
        return in_val.to_bytes(f[0], RaknetPing.byte_order, signed=f[1])

    @staticmethod
    def __slice(in_bytes: bytes, pattern: list) -> list:
        ret = []
        bytes_index = 0
        pattern_index = 0
        while bytes_index < len(in_bytes):
            try:
                field = RaknetPing.field_sizes[pattern[pattern_index]]
            except IndexError as index_error:
                raise IndexError(
                    "Ran out of pattern with additional bytes remaining"
                ) from index_error
            if pattern[pattern_index] == "string":
                string_header_length = field[0]
                string_length = int.from_bytes(
                    in_bytes[bytes_index : bytes_index + string_header_length],
                    RaknetPing.byte_order,
                    signed=field[1],
                )
                length = string_header_length + string_length
                string_bytes = in_bytes[
                    bytes_index
                    + string_header_length : bytes_index
                    + string_header_length
                    + string_length
                ]
                try:
                    ret.append(string_bytes.decode("utf-8"))
                except ValueError:
                    logger.exception(
                        "Could not decode text while processing RakNet packet"
                        " - faulting bstring is %s",
                        string_bytes,
                    )
                    ret.append("")
            elif pattern[pattern_index] == "magic":
                length = field[0]
                ret.append(in_bytes[bytes_index : bytes_index + length])
            else:
                length = field[0]
                ret.append(
                    int.from_bytes(
                        in_bytes[bytes_index : bytes_index + length],
                        RaknetPing.byte_order,
                        signed=field[1],
                    )
                )
            bytes_index += length
            pattern_index += 1
        return ret

    @staticmethod
    def __get_time() -> int:
        return time.perf_counter_ns() // 1000000

    def __sendping(self) -> None:
        pack_id = RaknetPing.__byter(0x01, "byte")
        now = RaknetPing.__byter(RaknetPing.__get_time(), "ulong")
        guid = self.guid_bytes
        d2s = pack_id + now + RaknetPing.magic + guid
        # print("S:", d2s)
        self.sock.sendto(d2s, (self.addr, self.port))

    def __recvpong(self) -> dict:
        try:
            data = self.sock.recv(4096)
        except TimeoutError:
            logger.warning(
                "Got timeout while issuing bedrock ping to %s:%i", self.addr, self.port
            )
            return {}
        if data[0] == 0x1C:
            ret = {}
            sliced = RaknetPing.__slice(
                data, ["byte", "ulong", "ulong", "magic", "string"]
            )
            if sliced[3] != RaknetPing.magic:
                raise ValueError(f"Incorrect magic received ({sliced[3]})")
            ret["server_guid"] = sliced[2]
            ret["server_string_raw"] = sliced[4]
            ret.update(self.__unpack_bedrock_pong_str(sliced[4]))
            return ret
        raise ValueError(f"Incorrect packet type ({data[0]} detected")

    @staticmethod
    def __unpack_bedrock_pong_str(server_info_str: str) -> dict:
        server_info = server_info_str.split(";")
        logger.debug("Parsing server info: %s", server_info)
        last_enumeration = 0
        unpacked_values = {}
        for i in enumerate(server_info):
            # Enumerate the server fields, look up the field name by index,
            #  store it in the return dictionary
            try:
                field_name = RaknetPing.pingpong_string_fields[i[0]]
                if field_name:
                    unpacked_values[field_name] = i[1]
                    last_enumeration = i[0]
                elif i[1] != "":
                    # The last field should be empty, if it is not, log the error
                    logger.debug(
                        "Found non-empty field at the end of Bedrock ping: '%s'",
                        i[1],
                    )
                else:
                    last_enumeration = i[0]
            except IndexError:
                logger.debug(
                    "Bedrock ping had too many fields while parsing, found '%s'",
                    i,
                )
        if last_enumeration < len(RaknetPing.pingpong_string_fields) - 1:
            missing_keys = RaknetPing.pingpong_string_fields[last_enumeration + 1 :]
            logger.warning(
                "Bedrock ping returned a string with too few fields"
                " - missing values %s",
                missing_keys,
            )
            for m in missing_keys:
                unpacked_values[m] = None
        return unpacked_values

    def ping(self, retries: int = 3):
        rtr = retries
        while rtr > 0:
            try:
                self.__sendping()
                return self.__recvpong()
            except ValueError as e:
                print(
                    f"E: {e}, checking next packet. Retries remaining: {rtr}/{retries}"
                )
            rtr -= 1
