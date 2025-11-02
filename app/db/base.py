"""Database base class and model imports."""
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here for Alembic to detect them
from app.db.models.meeting import Meeting  # noqa: F401, E402
from app.db.models.poll import Poll  # noqa: F401, E402
from app.db.models.checkin import Checkin  # noqa: F401, E402
from app.db.models.poll_vote import PollVote  # noqa: F401, E402
