"""FastAPI dependency that wraps `TokenBucket` and persists denials.

Usage:
    @router.post("/posts", dependencies=[Depends(rate_limit("posts:create", 5, 0.2))])
    def create_post(...): ...

Args to `rate_limit(prefix, capacity, refill_rate)`:
  prefix      — namespace for the bucket key (e.g. "posts:create")
  capacity    — max burst size
  refill_rate — tokens per second

On denial:
  - HTTP 429 with `Retry-After` header
  - Async write to Postgres `rate_limit_audit` so we can show denials in SigNoz
    and prove the limiter fired (R12 dashboards).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db_config import get_connection
from jwt import get_current_user
from models import RateLimitAudit

from .bucket import TokenBucket


def rate_limit(prefix: str, capacity: int, refill_rate: float):
    bucket = TokenBucket(prefix, capacity, refill_rate)

    def _dep(
        request: Request,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_connection),
    ):
        subject = current_user.get("sub", "anonymous")
        result = bucket.take(subject)
        if result.allowed:
            return

        try:
            user_id = UUID(subject) if subject != "anonymous" else None
        except ValueError:
            user_id = None

        db.add(RateLimitAudit(
            user_id=user_id,
            endpoint=f"{request.method} {request.url.path}",
        ))
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": f"{result.retry_after:.1f}"},
        )

    return _dep
