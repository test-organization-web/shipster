"""Wrap callables that need a DB :class:`~shipster.platform.persistence.uow.ShipsterUnitOfWork`."""

from collections.abc import Callable

from shipster.platform.persistence.database import get_session_factory
from shipster.platform.persistence.uow import ShipsterUnitOfWork


def uow_interval_job(fn: Callable[[ShipsterUnitOfWork], None]) -> Callable[[], None]:
    """Return a no-arg job that opens one session, builds UoW, commits on success."""

    def _run() -> None:
        factory = get_session_factory()
        session = factory()
        try:
            uow = ShipsterUnitOfWork(session)
            fn(uow)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _run
