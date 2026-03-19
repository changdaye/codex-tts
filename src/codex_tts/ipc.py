from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import socket


JsonDict = dict[str, object]
UNIX_PATH_LIMIT = 103


class JsonSocketServer:
    def __init__(self, path: Path, *, handler: Callable[[JsonDict], JsonDict]) -> None:
        self.path = path
        self.handler = handler
        self._server: socket.socket | None = None
        self._bound_path: Path | None = None

    def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.path.unlink()

        bound_path = _socket_bind_path(self.path)
        bound_path.parent.mkdir(parents=True, exist_ok=True)
        if bound_path.exists():
            bound_path.unlink()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(bound_path))
        server.listen()
        self._server = server
        self._bound_path = bound_path
        if bound_path != self.path:
            self.path.symlink_to(bound_path)

    def handle_next_request(self, *, timeout: float = 0.1) -> bool:
        if self._server is None:
            raise RuntimeError("socket server is not running")

        self._server.settimeout(timeout)
        try:
            connection, _ = self._server.accept()
        except TimeoutError:
            return False

        with connection:
            request = _read_json_line(connection)
            response = self.handler(request)
            try:
                _write_json_line(connection, response)
            except (BrokenPipeError, ConnectionResetError):
                return True
        return True

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
        if self.path.exists():
            self.path.unlink()
        if self._bound_path is not None and self._bound_path.exists():
            self._bound_path.unlink()
        self._bound_path = None


def call_daemon(path: Path, request: JsonDict, *, timeout: float = 1.0) -> JsonDict:
    connect_path = _socket_bind_path(path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(str(connect_path))
        _write_json_line(client, request)
        return _read_json_line(client)


def _read_json_line(sock: socket.socket) -> JsonDict:
    payload = bytearray()
    while not payload.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("socket closed before newline-delimited JSON message completed")
        payload.extend(chunk)
    return json.loads(payload.decode("utf-8"))


def _write_json_line(sock: socket.socket, payload: JsonDict) -> None:
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
    sock.sendall(encoded)


def _socket_bind_path(path: Path) -> Path:
    if len(str(path)) <= UNIX_PATH_LIMIT:
        return path
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]
    return Path("/tmp") / f"codex-tts-{digest}.sock"
