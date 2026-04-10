from apps.users.domain.entities import User
from apps.users.infrastructure.persistence.schema.user import UserORM


def user_row_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        email=row.email,
        username=row.username,
        password_hash=row.password_hash,
    )


def user_domain_to_row(user: User) -> UserORM:
    return UserORM(
        id=user.id,
        email=user.email,
        username=user.username,
        password_hash=user.password_hash,
    )
