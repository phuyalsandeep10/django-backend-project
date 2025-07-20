from enum import Enum


class PriorityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class StatusEnum(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    CLOSED = "closed"


class WarningLevelEnum(str, Enum):
    WARNING_75 = 75
    WARNING_90 = 90
    WARNING_100 = 100


class TicketAlertTypeEnum(str, Enum):
    RESPONSE = "response"
    RESOLUTION = "resolution"
