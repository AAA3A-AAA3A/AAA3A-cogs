import typing  # isort:skip


class Pagination(typing.List):
    """Pagination class for lists."""

    DEFAULT_PER_PAGE = 20

    def __init__(self, *args, **kwargs) -> None:
        self.total: int = kwargs.pop("total", None)
        self.per_page: int = kwargs.pop("per_page", None)
        self.pages: int = kwargs.pop("pages", None)
        self.page: int = kwargs.pop("page", None)
        super().__init__(*args, **kwargs)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "items": list(self),
            "total": self.total,
            "per_page": self.per_page,
            "pages": self.pages,
            "page": self.page,
        }

    def __repr__(self) -> str:
        return f"<Pagination page={self.page} of {self.pages}>"

    def has_prev(self) -> bool:
        return self.page > 1

    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def elements_numbers(self) -> typing.List[int]:
        return list(range(1, self.total + 1))

    @property
    def pages_numbers(self) -> typing.List[int]:
        return list(range(1, self.pages + 1))

    @classmethod
    def from_list(
        cls,
        items: typing.List[typing.Any],
        per_page: typing.Optional[typing.Union[int, str]] = None,
        page: typing.Optional[typing.Union[int, str]] = None,
        default_per_page: int = DEFAULT_PER_PAGE,
    ) -> typing.Any:
        per_page = (
            default_per_page
            if per_page is None
            else (
                int(per_page)
                if isinstance(per_page, str) and per_page.isdigit() and 1 <= int(per_page) <= default_per_page * 5
                else default_per_page
            )
        )
        page = (
            1
            if page is None
            else (int(page) if isinstance(page, str) and page.isdigit() and int(page) >= 1 else 1)
        )
        total = len(items)
        pages = (total // per_page) + (total % per_page > 0)
        page = min(page, pages)
        start = (page - 1) * per_page
        end = start + per_page
        return cls(
            items[start:end],
            total=total,
            per_page=per_page,
            pages=pages,
            page=page,
        )
