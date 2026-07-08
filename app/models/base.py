from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""

    repr_cols_num = 3
    repr_cols = ()

    def __repr__(self) -> str:
        cols = []

        if self.repr_cols:
            for col in self.repr_cols:
                cols.append(f"{col}={getattr(self, col)!r}")
        else:
            for column in self.__table__.columns[: self.repr_cols_num]:
                cols.append(f"{column.name}={getattr(self, column.name)!r}")

        return f"<{self.__class__.__name__} {' '.join(cols)}>"
