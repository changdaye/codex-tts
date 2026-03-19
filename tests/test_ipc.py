from pathlib import Path
import socket
import threading

import pytest

from codex_tts.ipc import JsonSocketServer, _read_json_line, _socket_bind_path, call_daemon


def test_ipc_round_trip_returns_json_response(tmp_path):
    socket_path = tmp_path / "daemon.sock"
    server = JsonSocketServer(
        socket_path,
        handler=lambda request: {
            "ok": True,
            "echo": request["message"],
        },
    )
    server.start()

    def handle_request() -> None:
        server.handle_next_request(timeout=1.0)

    worker = threading.Thread(target=handle_request)
    worker.start()
    try:
        response = call_daemon(socket_path, {"message": "hello"})
    finally:
        worker.join(timeout=2.0)
        server.close()

    assert response == {"ok": True, "echo": "hello"}


def test_json_socket_server_replaces_stale_socket_file(tmp_path):
    socket_path = tmp_path / "daemon.sock"
    socket_path.write_text("stale", encoding="utf-8")

    server = JsonSocketServer(socket_path, handler=lambda request: {"ok": True})
    try:
        server.start()
        assert socket_path.exists()
        assert socket_path.is_socket()
    finally:
        server.close()


def test_json_socket_server_requires_start_before_handling_requests(tmp_path):
    server = JsonSocketServer(tmp_path / "daemon.sock", handler=lambda request: {"ok": True})

    with pytest.raises(RuntimeError, match="socket server is not running"):
        server.handle_next_request()


def test_read_json_line_raises_when_socket_closes_before_newline():
    left, right = socket.socketpair()
    try:
        right.sendall(b'{"partial":true}')
        right.close()

        with pytest.raises(RuntimeError, match="socket closed before newline-delimited JSON message completed"):
            _read_json_line(left)
    finally:
        left.close()


def test_json_socket_server_replaces_stale_shortened_socket_file(tmp_path):
    long_dir = tmp_path / ("nested-" * 20)
    socket_path = long_dir / "daemon.sock"
    bound_path = _socket_bind_path(socket_path)
    bound_path.parent.mkdir(parents=True, exist_ok=True)
    bound_path.write_text("stale", encoding="utf-8")

    server = JsonSocketServer(socket_path, handler=lambda request: {"ok": True})
    try:
        server.start()
        assert socket_path.is_symlink()
        assert bound_path.exists()
        assert bound_path.is_socket()
    finally:
        server.close()
