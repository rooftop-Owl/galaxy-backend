#!/usr/bin/env python3
"""Unit tests for Caduceus core components: MessageBus, InboundMessage, OutboundMessage."""

import asyncio
import sys
from pathlib import Path

import pytest

# Ensure caduceus is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from caduceus.bus import MessageBus, InboundMessage, OutboundMessage


class TestInboundMessage:
    """Test InboundMessage dataclass."""

    def test_create_message(self):
        msg = InboundMessage(
            channel="telegram", sender_id="123", chat_id="456",
            content="hello", media=[], metadata={}
        )
        assert msg.channel == "telegram"
        assert msg.sender_id == "123"
        assert msg.chat_id == "456"
        assert msg.content == "hello"
        assert msg.media == []
        assert msg.metadata == {}

    def test_session_key(self):
        msg = InboundMessage(
            channel="telegram", sender_id="123", chat_id="456",
            content="test", media=[], metadata={}
        )
        assert msg.session_key == "telegram:456"

    def test_session_key_web(self):
        msg = InboundMessage(
            channel="web", sender_id="user1", chat_id="web-42",
            content="test", media=[], metadata={}
        )
        assert msg.session_key == "web:web-42"

    def test_with_media(self):
        msg = InboundMessage(
            channel="telegram", sender_id="1", chat_id="2",
            content="", media=["file1.jpg"], metadata={"type": "photo"}
        )
        assert len(msg.media) == 1
        assert msg.metadata["type"] == "photo"


class TestOutboundMessage:
    """Test OutboundMessage dataclass."""

    def test_create_message(self):
        msg = OutboundMessage(channel="telegram", chat_id="456", content="response")
        assert msg.channel == "telegram"
        assert msg.chat_id == "456"
        assert msg.content == "response"


class TestMessageBus:
    """Test MessageBus async routing."""

    @pytest.mark.asyncio
    async def test_publish_consume_inbound(self):
        bus = MessageBus()
        msg = InboundMessage(
            channel="test", sender_id="1", chat_id="2",
            content="hello", media=[], metadata={}
        )
        await bus.publish_inbound(msg)
        consumed = await bus.consume_inbound()
        assert consumed.content == "hello"
        assert consumed.channel == "test"

    @pytest.mark.asyncio
    async def test_publish_consume_outbound(self):
        bus = MessageBus()
        msg = OutboundMessage(channel="test", chat_id="2", content="response")
        await bus.publish_outbound(msg)
        consumed = await bus.consume_outbound()
        assert consumed.content == "response"

    @pytest.mark.asyncio
    async def test_fifo_ordering(self):
        bus = MessageBus()
        for i in range(3):
            msg = InboundMessage(
                channel="test", sender_id="1", chat_id="2",
                content=f"msg-{i}", media=[], metadata={}
            )
            await bus.publish_inbound(msg)

        for i in range(3):
            consumed = await bus.consume_inbound()
            assert consumed.content == f"msg-{i}"

    @pytest.mark.asyncio
    async def test_independent_queues(self):
        """Inbound and outbound queues are independent."""
        bus = MessageBus()
        inbound = InboundMessage(
            channel="test", sender_id="1", chat_id="2",
            content="inbound", media=[], metadata={}
        )
        outbound = OutboundMessage(channel="test", chat_id="2", content="outbound")

        await bus.publish_inbound(inbound)
        await bus.publish_outbound(outbound)

        consumed_in = await bus.consume_inbound()
        consumed_out = await bus.consume_outbound()

        assert consumed_in.content == "inbound"
        assert consumed_out.content == "outbound"
