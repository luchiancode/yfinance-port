from typing import Annotated

from pydantic import StringConstraints

TickerSymbol = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=500, pattern=r"^[A-Za-z0-9.^=_&+-]+$",
)]
