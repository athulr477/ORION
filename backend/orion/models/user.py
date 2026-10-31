"""User model for Role-Based Access Control (RBAC)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from orion.database import Base


class UserRole(enum.StrEnum):
    """User roles determining access level in Orion."""

    QA_LEAD = "QA_LEAD"
    DEVELOPER = "DEVELOPER"


class User(Base):
    """System user with authentication credentials and RBAC role."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.DEVELOPER,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username!r}, role={self.role!r})>"
