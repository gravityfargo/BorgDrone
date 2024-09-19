from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db


class Settings(db.Model):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user = relationship("Users", back_populates="settings")

    secret_key: Mapped[str] = mapped_column(default="dev")
    sqlalchemy_database_uri: Mapped[str] = mapped_column(default="sqlite:///borgdrone.db")
    sqlalchemy_track_modifications: Mapped[bool] = mapped_column(default=False)
    instance_path: Mapped[str] = mapped_column(default="/var/lib/borgdrone")
    archive_name: Mapped[str] = mapped_column(default="borgdrone-{hostname}-{now:%Y-%m-%d_%H:%M:%S}")
    logs_path: Mapped[Optional[str]]

    # default_cron
    cron_minute: Mapped[str] = mapped_column(default="*")
    cron_hour: Mapped[str] = mapped_column(default="*")
    cron_day: Mapped[str] = mapped_column(default="*")
    cron_month: Mapped[str] = mapped_column(default="*")
    cron_weekday: Mapped[str] = mapped_column(default="*")
