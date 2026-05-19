from __future__ import annotations

import io
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest.mock import Mock

from server import Handler


class HandlerCharacterImageRouteTests(unittest.TestCase):
    def make_handler(self) -> Handler:
        handler = Handler.__new__(Handler)
        handler.path = "/"
        handler.command = "GET"
        handler.request_version = "HTTP/1.1"
        handler.wfile = io.BytesIO()
        handler.store = Mock()
        handler._status: int | None = None
        handler._headers: list[tuple[str, str]] = []
        handler._error: tuple[int, str | None] | None = None

        def send_response(code: int, message: str | None = None) -> None:
            handler._status = code

        def send_header(name: str, value: str) -> None:
            handler._headers.append((name, value))

        def end_headers() -> None:
            return None

        def send_error(code: int, message: str | None = None, explain: str | None = None) -> None:
            handler._status = code
            handler._error = (code, message)

        handler.send_response = send_response  # type: ignore[method-assign]
        handler.send_header = send_header  # type: ignore[method-assign]
        handler.end_headers = end_headers  # type: ignore[method-assign]
        handler.send_error = send_error  # type: ignore[method-assign]
        return handler

    def test_character_image_route_returns_400_when_source_missing(self) -> None:
        handler = self.make_handler()

        handler.path = "/api/character-image"
        handler.do_GET()

        self.assertEqual(handler._status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(handler._error, (HTTPStatus.BAD_REQUEST, "Missing source parameter"))
        handler.store.character_image_png.assert_not_called()

    def test_character_image_route_returns_404_when_source_missing_on_disk(self) -> None:
        handler = self.make_handler()
        handler.store.character_image_png.side_effect = FileNotFoundError("missing image")

        handler.path = "/api/character-image?source=data/character/0001/entry.xml"
        handler.do_GET()

        self.assertEqual(handler._status, HTTPStatus.NOT_FOUND)
        self.assertEqual(handler._error, (HTTPStatus.NOT_FOUND, "missing image"))

    def test_character_image_route_returns_501_for_decoder_error(self) -> None:
        handler = self.make_handler()
        handler.store.character_image_png.side_effect = RuntimeError("decoder unavailable")

        handler.path = "/api/character-image?source=data/character/0001/entry.xml"
        handler.do_GET()

        self.assertEqual(handler._status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(handler._error, (HTTPStatus.NOT_IMPLEMENTED, "decoder unavailable"))

    def test_character_image_route_returns_png_bytes_on_success(self) -> None:
        handler = self.make_handler()
        handler.store.character_image_png.return_value = b"png-bytes"

        handler.path = "/api/character-image?source=data/character/0001/entry.xml"
        handler.do_GET()

        self.assertEqual(handler._status, HTTPStatus.OK)
        self.assertEqual(
            handler._headers,
            [
                ("Content-Type", "image/png"),
                ("Cache-Control", "public, max-age=3600"),
                ("Content-Length", str(len(b"png-bytes"))),
            ],
        )
        self.assertEqual(handler.wfile.getvalue(), b"png-bytes")
        handler.store.character_image_png.assert_called_once_with("data/character/0001/entry.xml")

    def test_character_image_route_uses_thumbnail_variant_when_requested(self) -> None:
        handler = self.make_handler()
        handler.store.character_image_thumbnail_png.return_value = b"thumb-bytes"

        handler.path = "/api/character-image?source=data/character/0001/entry.xml&variant=thumb"
        handler.do_GET()

        self.assertEqual(handler._status, HTTPStatus.OK)
        self.assertEqual(
            handler._headers,
            [
                ("Content-Type", "image/png"),
                ("Cache-Control", "public, max-age=3600"),
                ("Content-Length", str(len(b"thumb-bytes"))),
            ],
        )
        self.assertEqual(handler.wfile.getvalue(), b"thumb-bytes")
        handler.store.character_image_thumbnail_png.assert_called_once_with("data/character/0001/entry.xml")
        handler.store.character_image_png.assert_not_called()


if __name__ == "__main__":
    unittest.main()
