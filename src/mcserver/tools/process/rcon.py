"""Small Minecraft RCON client used for graceful process control."""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass


AUTH_PACKET = 3
COMMAND_PACKET = 2
AUTH_FAILED_ID = -1


class RconError(RuntimeError):
    """Raised when RCON auth or command execution fails."""


@dataclass(frozen=True)
class RconResponse:
    request_id: int
    packet_type: int
    payload: str


class RconClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        password: str,
        timeout: float,
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._request_id = 0

    def __enter__(self) -> RconClient:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def connect(self) -> None:
        self._sock = socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout,
        )
        self._sock.settimeout(self.timeout)
        self._authenticate()

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def command(self, command: str) -> str:
        response = self._request(COMMAND_PACKET, command)
        return response.payload

    def _authenticate(self) -> None:
        response = self._request(AUTH_PACKET, self.password)
        if response.request_id == AUTH_FAILED_ID:
            raise RconError("RCON authentication failed.")

    def _request(self, packet_type: int, payload: str) -> RconResponse:
        self._request_id += 1
        request_id = self._request_id
        body = (
            struct.pack("<ii", request_id, packet_type)
            + payload.encode("utf-8")
            + b"\x00\x00"
        )
        packet = struct.pack("<i", len(body)) + body
        sock = self._require_socket()
        sock.sendall(packet)
        return self._read_response()

    def _read_response(self) -> RconResponse:
        sock = self._require_socket()
        header = _recv_exact(sock, 4)
        (length,) = struct.unpack("<i", header)
        if length < 10:
            raise RconError(f"Invalid RCON packet length: {length}")
        data = _recv_exact(sock, length)
        request_id, packet_type = struct.unpack("<ii", data[:8])
        payload = data[8:-2].decode("utf-8", errors="replace")
        return RconResponse(
            request_id=request_id,
            packet_type=packet_type,
            payload=payload,
        )

    def _require_socket(self) -> socket.socket:
        if self._sock is None:
            raise RconError("RCON client is not connected.")
        return self._sock


def run_command(
    *,
    host: str,
    port: int,
    password: str,
    timeout: float,
    command: str,
) -> str:
    with RconClient(host=host, port=port, password=password, timeout=timeout) as client:
        return client.command(command)


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RconError("RCON connection closed while reading response.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
