"""Integration tests for MCP server auth behavior."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from src.config import get_settings
from src.mcp.server import create_mcp_app


class McpServerAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env_token = os.environ.get("MCP_AUTH_TOKEN")
        self._env_transport = os.environ.get("MCP_TRANSPORT")

        os.environ["MCP_AUTH_TOKEN"] = "test-token"
        os.environ["MCP_TRANSPORT"] = "http"
        get_settings.cache_clear()

    def tearDown(self) -> None:
        if self._env_token is None:
            os.environ.pop("MCP_AUTH_TOKEN", None)
        else:
            os.environ["MCP_AUTH_TOKEN"] = self._env_token

        if self._env_transport is None:
            os.environ.pop("MCP_TRANSPORT", None)
        else:
            os.environ["MCP_TRANSPORT"] = self._env_transport

        get_settings.cache_clear()

    def test_mcp_requires_auth(self) -> None:
        with TestClient(create_mcp_app()) as client:
            response = client.get("/mcp")
        self.assertEqual(response.status_code, 401)

    def test_mcp_accepts_auth_header(self) -> None:
        with TestClient(create_mcp_app()) as client:
            response = client.get("/mcp", headers={"Authorization": "Bearer test-token"})
        self.assertNotEqual(response.status_code, 401)
