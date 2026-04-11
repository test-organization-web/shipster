from enum import StrEnum


class MessagingBackendType(StrEnum):
    RABBIT_MQ = "rabbitmq"
    REDIS = "redis"
