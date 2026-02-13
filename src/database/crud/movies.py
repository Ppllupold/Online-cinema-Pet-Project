from __future__ import annotations

import math
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import Select, distinct, func, select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.movies import (
    MovieModel,
    Genre,
    Star,
    Director,
    MovieGenresTable,
    MovieStarsTable,
    MovieDirectorsTable,
)
from src.schemas.movies import (
    MovieFilterSchema,
    MovieListResponse,
    MoviesListItem,
    PaginationSchema,
    MovieDetailResponse,
)

DEFAULT_PER_PAGE = 10
DEFAULT_PAGE = 1
MOVIE_LIST_URL = "/api/v1/movies"

SortField = Literal["year", "imdb", "price"]
SortOrder = Literal["asc", "desc"]


# ---------------------------------------------------------------------------
# Маппінг поля сортування → колонка моделі.
# Виноситимо в константу щоб не будувати dict при кожному виклику функції.
# ---------------------------------------------------------------------------
SORT_COLUMNS = {
    "year": MovieModel.year,
    "imdb": MovieModel.imdb,
    "price": MovieModel.price,
}


def _get_sort_column(sort: SortField):
    return SORT_COLUMNS[sort]


def _build_filtered_stmt(filters: MovieFilterSchema) -> Select:
    stmt: Select = select(MovieModel)

    if filters.q is not None:
        search_term = f"%{filters.q}%"
        stmt = stmt.where(
            or_(
                MovieModel.name.ilike(search_term),
                MovieModel.description.ilike(search_term),
            )
        )

    # --- Прості фільтри по полях самої таблиці movies ---

    if filters.year_gte is not None:
        stmt = stmt.where(MovieModel.year >= filters.year_gte)

    if filters.imdb_gte is not None:
        stmt = stmt.where(MovieModel.imdb >= filters.imdb_gte)

    if filters.price_lte is not None:
        stmt = stmt.where(MovieModel.price <= filters.price_lte)

    # --- Фільтр по режисеру (AND — фільм має мати САМЕ цього режисера) ---
    # JOIN з bridge-таблицею MovieDirectorsTable → Director,
    # потім WHERE по імені (регістр ігнорується через lower()).
    if filters.director is not None:
        stmt = (
            stmt.join(
                MovieDirectorsTable, MovieDirectorsTable.c.movie_id == MovieModel.id
            )
            .join(Director, Director.id == MovieDirectorsTable.c.director_id)
            .where(func.lower(Director.name) == filters.director)
        )

    # --- Фільтр по акторах (OR — фільм має мати ХОЧА Б ОДНОГО з переліку) ---
    # JOIN з bridge-таблицею MovieStarsTable → Star,
    # IN(...) — достатньо одного збігу.
    if filters.stars:
        stmt = (
            stmt.join(MovieStarsTable, MovieStarsTable.c.movie_id == MovieModel.id)
            .join(Star, Star.id == MovieStarsTable.c.star_id)
            .where(func.lower(Star.name).in_(filters.stars))
        )

    # --- Фільтр по жанрах (AND — фільм має мати ВСІ запитані жанри) ---
    #
    # Тут не можна просто написати WHERE genre IN (...) —
    # це дало б OR-логіку (хоча б один жанр).
    #
    # Трюк: групуємо по movie_id і перевіряємо
    # HAVING count(distinct genre) = кількість запитаних жанрів.
    # Тобто: у фільму мають бути присутні ВСІ жанри зі списку.
    #
    # Робимо це через subquery щоб уникнути конфлікту з іншими JOIN вище.
    if filters.genres:
        genres_subq = (
            select(MovieGenresTable.c.movie_id.label("movie_id"))
            .join(Genre, Genre.id == MovieGenresTable.c.genre_id)
            .where(func.lower(Genre.name).in_(filters.genres))
            .group_by(MovieGenresTable.c.movie_id)
            .having(func.count(distinct(func.lower(Genre.name))) == len(filters.genres))
            .subquery()
        )
        stmt = stmt.where(MovieModel.id.in_(select(genres_subq.c.movie_id)))

    return stmt


# ---------------------------------------------------------------------------
# Побудова базового SELECT з усіма фільтрами.
# Повертає SQLAlchemy Select — ще не виконаний запит, просто об'єкт.
def _build_ids_subquery(stmt: Select, sort_col):
    return (
        stmt.with_only_columns(
            MovieModel.id.label("id"),
            sort_col.label("sort_key"),
        )
        .distinct()
        .subquery()
    )


# ---------------------------------------------------------------------------
# Будуємо "ids subquery" — серце всієї пагінації.
#
# Ця subquery вибирає пари (id, sort_key) для відфільтрованих фільмів.
# DISTINCT тут критичний: якщо фільм має кількох акторів/жанрів,
# JOIN-и можуть продублювати рядки. DISTINCT прибирає дублі.
#
# Повертаємо subquery об'єкт — він буде використаний двічі:
#   1) для підрахунку total_items (COUNT)
#   2) для вибірки конкретної сторінки (OFFSET/LIMIT)
# ---------------------------------------------------------------------------
def _build_page_url(
    page: int,
    per_page: int,
    sort: SortField,
    order: SortOrder,
    filters: MovieFilterSchema,
) -> str:
    params = [
        f"page={page}",
        f"per_page={per_page}",
        f"sort={sort}",
        f"order={order}",
    ]

    if filters.q is not None:
        params.append(f"q={filters.q}")
    if filters.year_gte is not None:
        params.append(f"year_gte={filters.year_gte}")
    if filters.imdb_gte is not None:
        params.append(f"imdb_gte={filters.imdb_gte}")
    if filters.price_lte is not None:
        params.append(f"price_lte={filters.price_lte}")
    if filters.director is not None:
        params.append(f"director={filters.director}")
    for star in filters.stars or []:
        params.append(f"stars={star}")
    for genre in filters.genres or []:
        params.append(f"genres={genre}")

    return f"{MOVIE_LIST_URL}?" + "&".join(params)


# ---------------------------------------------------------------------------
# Серіалізуємо фільтри у query-string параметри для URL пагінації.
#
# БУЛО: next_page не включав фільтри → при переході на стор. 2
#       всі фільтри (жанр, актор тощо) губились.
#
# СТАЛО: всі активні фільтри додаються до URL.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def _validate_pagination(page: int, per_page: int) -> None:
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="page must be >= 1",
        )
    if per_page < 1 or per_page > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="per_page must be between 1 and 100",
        )


# ---------------------------------------------------------------------------
# Головна функція — оркеструє все вище.
# ---------------------------------------------------------------------------
async def get_movies_list(
    db: AsyncSession,
    *,
    page: int = DEFAULT_PAGE,
    per_page: int = DEFAULT_PER_PAGE,
    filters: MovieFilterSchema | None = None,
    sort: SortField = "imdb",
    order: SortOrder = "desc",
) -> MovieListResponse:

    # 1. Перевіряємо коректність параметрів пагінації
    _validate_pagination(page, per_page)

    filters = filters or MovieFilterSchema()

    # 2. Отримуємо колонку сортування один раз —
    #    далі передаємо її як аргумент, не шукаємо знову
    sort_col = _get_sort_column(sort)

    # 3. Будуємо відфільтрований SELECT (ще не виконуємо)
    base_stmt = _build_filtered_stmt(filters)

    # 4. Будуємо ids_subquery — використовується двічі нижче.
    #    Це ключова оптимізація: раніше subquery будувалась окремо
    #    в _count_total_items і окремо в _fetch_movies_page.
    ids_subq = _build_ids_subquery(base_stmt, sort_col)

    # 5. Підраховуємо загальну кількість фільмів (без OFFSET/LIMIT).
    #    SELECT COUNT(*) FROM (SELECT DISTINCT id, sort_key FROM ...) AS subq
    total_items = int(await db.scalar(select(func.count()).select_from(ids_subq)))
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 0

    # 6. Перевіряємо що запитана сторінка існує
    if total_pages > 0 and page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page number out of total pages range",
        )

    # 7. Вибираємо ids для конкретної сторінки (з сортуванням і OFFSET/LIMIT).
    #    Спочатку визначаємо напрямок сортування для sort_key і id.
    if order == "desc":
        sort_key_col = ids_subq.c.sort_key.desc()
        id_col = ids_subq.c.id.desc()
    else:
        sort_key_col = ids_subq.c.sort_key.asc()
        id_col = ids_subq.c.id.asc()

    # SELECT id, sort_key FROM ids_subq ORDER BY ... OFFSET ... LIMIT ...
    page_subq = (
        select(ids_subq)
        .order_by(sort_key_col, id_col)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .subquery()
    )

    # 8. Завантажуємо повні об'єкти MovieModel для ids зі сторінки.
    #    JOIN гарантує що порядок збережеться (ORDER BY по page_subq).
    movies: list[MovieModel] = []
    if total_items > 0:
        result = await db.scalars(
            select(MovieModel)
            .join(page_subq, MovieModel.id == page_subq.c.id)
            .order_by(sort_key_col, id_col)
        )
        movies = list(result.all())

    # 9. Будуємо URL наступної/попередньої сторінки з усіма фільтрами.
    #    БУЛО: фільтри губились в URL. СТАЛО: всі параметри зберігаються.
    next_page = (
        _build_page_url(page + 1, per_page, sort, order, filters)
        if total_pages > 0 and page < total_pages
        else None
    )
    previous_page = (
        _build_page_url(page - 1, per_page, sort, order, filters)
        if total_pages > 0 and page > 1
        else None
    )

    pagination = PaginationSchema(
        page=page,
        per_page=per_page,
        next_page=next_page,
        previous_page=previous_page,
        total_pages=total_pages,
        total_items=total_items,
    )

    items = [MoviesListItem.model_validate(m) for m in movies]

    return MovieListResponse(items=items, pagination=pagination)
