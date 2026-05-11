import logging
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models import User, UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    """Create initial admin user if not exists."""
    with Session(engine) as session:
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)

        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()

        if not user:
            logger.info(f"Creating initial admin user: {settings.FIRST_SUPERUSER}")
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                full_name="Admin",
                is_superuser=True,
                is_active=True,
            )
            user = crud.create_user(session=session, user_create=user_in)
            logger.info(f"Admin user created: {user.email}")
        else:
            logger.info(f"Admin user already exists: {user.email}")


def main() -> None:
    logger.info("Initializing database and creating initial data...")
    init()
    logger.info("Initial data ready")


if __name__ == "__main__":
    main()