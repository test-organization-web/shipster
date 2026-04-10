"""Broker wiring: dependencies, Redis adapter, factory for future backends."""

from apps.messaging.factory import create_message_publisher, create_message_receiver

__all__ = [
    "create_message_publisher",
    "create_message_receiver",
]
