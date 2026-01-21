from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    DateTime,
    func,
    Numeric,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

# --- Association tables (M2M) ---
MovieGenresTable = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

MovieStarsTable = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("star_id", ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True),
)

MovieDirectorsTable = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "director_id", ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True
    ),
)


# --- Lookup tables ---
class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "Movie",
        secondary=MovieGenresTable,
        back_populates="genres",
        lazy="selectin",
    )


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "Movie",
        secondary=MovieStarsTable,
        back_populates="stars",
        lazy="selectin",
    )


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "Movie",
        secondary=MovieDirectorsTable,
        back_populates="directors",
        lazy="selectin",
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "Movie",
        back_populates="certification",
        lazy="selectin",
    )


# --- Main table ---
class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)

    uuid: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    time: Mapped[int] = mapped_column(Integer, nullable=False)

    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)

    meta_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    certification: Mapped["Certification"] = relationship(
        "Certification",
        back_populates="movies",
        lazy="selectin",
    )

    # M2M relations
    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary=MovieGenresTable,
        back_populates="movies",
        lazy="selectin",
    )
    stars: Mapped[list["Star"]] = relationship(
        "Star",
        secondary=MovieStarsTable,
        back_populates="movies",
        lazy="selectin",
    )
    directors: Mapped[list["Director"]] = relationship(
        "Director",
        secondary=MovieDirectorsTable,
        back_populates="movies",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uq_movies_name_year_time"),
        CheckConstraint("year >= 1888", name="ck_movies_year_min"),
        CheckConstraint("time > 0", name="ck_movies_time_positive"),
        CheckConstraint("imdb >= 0 AND imdb <= 10", name="ck_movies_imdb_range"),
        CheckConstraint("votes >= 0", name="ck_movies_votes_nonneg"),
        CheckConstraint("price >= 0", name="ck_movies_price_nonneg"),
        Index("ix_movies_name_year", "name", "year"),
    )
