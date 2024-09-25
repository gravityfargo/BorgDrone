# type: ignore
# pylint: disable=E1102

from typing import Optional, Type, TypeVar

from sqlalchemy import func, select

from borgdrone.extensions import db

T = TypeVar("T")


def count(model) -> int:
    stmt = select(func.count()).select_from(model)
    res = db.session.execute(stmt)
    if not (num := res.scalar()):
        return 0

    return num


def get_latest(model: Type[T]) -> Optional[T]:
    stmt = select(model).order_by(model.id.desc())
    instance = db.session.scalars(stmt).first()
    return instance
