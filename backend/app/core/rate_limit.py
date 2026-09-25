from typing import Protocol


class RateLimiter(Protocol):
    async def check(self, identity: str, route: str) -> None: ...


# Introduce a shared Redis or gateway-backed implementation before write routes go live.
# An in-memory limiter would give misleading guarantees across API workers.
