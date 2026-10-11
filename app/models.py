from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, Text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    devices: Mapped[list[Device]] = relationship(back_populates="owner")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner: Mapped[User | None] = relationship(back_populates="devices")
    readings: Mapped[list[Reading]] = relationship(back_populates="device")


class Reading(Base):
    __tablename__ = "app_data"
    __table_args__ = (Index("ix_app_data_device_time", "device_id", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", name="fk_app_data_device"), nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    x: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    y: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    z: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    device: Mapped[Device] = relationship(back_populates="readings")
