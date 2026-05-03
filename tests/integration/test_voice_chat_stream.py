"""Integration tests for voice chat streaming endpoint."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.api.routes import speech


class _FakeGraph:
    async def astream_events(self, _payload, version="v2"):
        del version
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": SimpleNamespace(content="Hello")},
        }
        yield {
            "event": "on_chain_end",
            "data": {
                "output": {
                    "messages": [AIMessage(content="Hello world")],
                    "action": "None",
                    "action_data": None,
                }
            },
        }


class VoiceChatStreamIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(speech.router)
        self.client = TestClient(self.app)

    def test_voice_chat_stream_returns_progress_and_final(self):
        with (
            patch("src.api.routes.speech.get_graph", return_value=_FakeGraph()),
            patch(
                "src.api.routes.speech.transcribe_audio",
                new=AsyncMock(return_value="xin chao"),
            ),
            patch(
                "src.api.routes.speech.correct_text",
                new=AsyncMock(return_value="Xin chao"),
            ),
        ):
            with self.client.stream(
                "POST",
                "/api/voice-chat/stream?session_id=v-1",
                files={"audio": ("audio.wav", b"123", "audio/wav")},
            ) as response:
                content = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: progress", content)
        self.assertIn('"stage": "asr"', content)
        self.assertIn("event: token", content)
        self.assertIn("event: final", content)
        self.assertIn("event: done", content)
