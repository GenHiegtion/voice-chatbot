"""Integration tests for chat endpoints focused on data-team flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.api.session_history import clear_all_session_histories
from src.api.routes import chat


class _FakeGraph:
    async def ainvoke(self, _payload):
        return {
            "messages": [AIMessage(content="Kết quả data team test")],
            "next_agent": "FINISH",
        }

    async def astream_events(self, _payload, version="v2"):
        del version
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": SimpleNamespace(content="Xin")},
        }
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": SimpleNamespace(content=" chào")},
        }


class _TrackingGraph(_FakeGraph):
    def __init__(self):
        self.calls = []

    async def ainvoke(self, payload):
        self.calls.append(payload)
        return await super().ainvoke(payload)


class ChatDataTeamIntegrationTest(unittest.TestCase):
    def setUp(self):
        clear_all_session_histories()
        self.app = FastAPI()
        self.app.include_router(chat.router)
        self.client = TestClient(self.app)

    def test_chat_returns_ai_response(self):
        with patch("src.api.routes.chat.get_graph", return_value=_FakeGraph()):
            response = self.client.post(
                "/api/chat",
                json={"message": "Cho tôi xem menu", "session_id": "s-1"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["response"], "Kết quả data team test")
        self.assertEqual(body["session_id"], "s-1")

    def test_chat_stream_returns_sse_data(self):
        with patch("src.api.routes.chat.get_graph", return_value=_FakeGraph()):
            with self.client.stream(
                "POST",
                "/api/chat/stream",
                json={"message": "Cho tôi xem ưu đãi", "session_id": "s-2"},
            ) as response:
                content = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn("data: Xin", content)
        self.assertIn("event: done", content)

    def test_chat_reuses_session_context(self):
        graph = _TrackingGraph()
        with patch("src.api.routes.chat.get_graph", return_value=graph):
            response_1 = self.client.post(
                "/api/chat",
                json={"message": "Món nào đang bán chạy?", "session_id": "ctx-1"},
            )
            response_2 = self.client.post(
                "/api/chat",
                json={"message": "Món đó giá bao nhiêu?", "session_id": "ctx-1"},
            )

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(len(graph.calls), 2)

        first_call_messages = graph.calls[0]["messages"]
        second_call_messages = graph.calls[1]["messages"]
        self.assertEqual(len(first_call_messages), 1)
        self.assertGreaterEqual(len(second_call_messages), 3)
