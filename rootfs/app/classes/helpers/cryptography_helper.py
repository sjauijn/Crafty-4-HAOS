import base64
import binascii
from hashlib import blake2b, sha256
from pathlib import Path
from typing import BinaryIO


class CryptoHelper:
    def __init__(self, helper):
        self.helper = helper
        self.test = "hello world"

    def say_hello_world(self):
        print(self.test)

    @staticmethod
    def calculate_buffer_hash(buffer: BinaryIO) -> str:
        """
        Takes one argument of a stream buffer. Will return a
        sha256 hash of the buffer
        """
        sha256_hash = sha256()
        sha256_hash.update(buffer)
        return sha256_hash.hexdigest()

    @staticmethod
    def calculate_file_hash_sha256(file_path: str) -> str:
        """
        Takes one parameter of file path.
        It will generate a SHA256 hash for the path and return it.
        """
        sha256_hash = sha256()
        file_path_resolved = Path(file_path).resolve()
        try:
            with open(file_path_resolved, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except OSError:
            # If file is not found we'll return an empty string
            return ""

    @staticmethod
    def blake2b_hash_bytes(bytes_to_hash: bytes) -> bytes:
        """
        Hashes given bytes with blake2b hash function, returns digest as bytes.

        Args:
            bytes_to_hash: Bytes to be hashed.

        Returns: Digest of bytes hashed
        """
        blake2 = blake2b()
        blake2.update(bytes_to_hash)
        return blake2.digest()

    @staticmethod
    def blake2_hash_file(path_to_file: Path) -> bytes:
        """
        Hashes given file at path with blake2b hash function, returns digest as bytes.

        Args:
            path_to_file: Path to file to hash.

        Returns: Digest of file.
        """
        blake2 = blake2b()
        try:
            with path_to_file.open("rb") as file_to_hash:
                while True:
                    # Reads file 20kb at a time.
                    data = file_to_hash.read(20_000)
                    # Stops reading if at end of file.
                    if not data:
                        break
                    blake2.update(data)
        # Activity can raise FileNotFound, PermissionError, or OSError.
        except OSError as why:
            raise RuntimeError(f"Error accessing file: {path_to_file}.") from why
        return blake2.digest()

    @staticmethod
    def bytes_to_b64(input_bytes: bytes) -> str:
        """
        Converts input bytes to base64 encoded string.

        Args:
            input_bytes: Input bytes for conversion.

        Returns: String of base64 encoded bytes.

        """
        # base64.b64encode(input_bytes).decode("UTF-8") appends a trailing new line.
        # That newline is getting pulled off of the string before returning it.
        return base64.b64encode(input_bytes).decode("UTF-8").rstrip("\n")

    @staticmethod
    def b64_to_bytes(input_str: str) -> bytes:
        """
        Converts base64 encoded string to bytes.

        Args:
            input_str: Base64 bytes encodes as a string.

        Returns: Bytes from base64 encoded string.

        """
        return base64.b64decode(input_str)

    @staticmethod
    def bytes_to_hex(input_bytes: bytes) -> str:
        """
        Converts input bytes to hex encoded string.

        Args:
            input_bytes: Bytes to be encoded as hex string.

        Returns: Bytes encoded as hex string.

        """
        return input_bytes.hex()

    @staticmethod
    def str_to_b64(input_str: str) -> str:
        """
        Given source string, converts to base64 encoded string.

        Args:
            input_str: String to convert.

        Returns: b64 encoded string.

        """
        return base64.b64encode(input_str.encode("UTF-8")).decode("UTF-8").rstrip("\n")

    @staticmethod
    def b64_to_str(input_b64: str) -> str:
        """
        Converts b64 encoded string to string. Can raise RuntimeError if code cannot be
        decoded.

        Args:
            input_b64: Base64 encoded string.

        Returns: Decoded string from b64.

        """
        try:
            return base64.b64decode(input_b64).decode("UTF-8")
        except (RuntimeError, UnicodeError, binascii.Error) as why:
            raise RuntimeError(f"Unable to decode {input_b64} to b64.") from why
