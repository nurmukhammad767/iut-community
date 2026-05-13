"""Token-bucket rate limiter (R11 — from-scratch component).

Algorithm
---------
A bucket holds up to `capacity` tokens. Tokens refill continuously at
`refill_rate` tokens/second up to capacity. Each request takes one token;
when the bucket is empty, the request is denied.

Why token-bucket over the alternatives:
  * Fixed-window counters allow 2× burst at the window boundary.
  * Leaky-bucket smooths output rate but does not allow bursts at all.
  * Token-bucket allows controlled bursts up to `capacity` while still
    enforcing the long-run rate of `refill_rate`.

Why Redis (vs. in-process)
--------------------------
With multiple backend replicas behind the gateway (R8), an in-memory bucket
on one replica would let a malicious client multiply their quota by the
number of replicas. Redis gives us a single source of truth for the bucket
state across replicas. The take() operation must be atomic across the read
of (tokens, last_refill) and the write of the new state; we use a Lua script
that Redis runs server-side under the global execution lock.

Reference: Kleppmann, _Designing Data-Intensive Applications_, ch. 8
("The Trouble with Distributed Systems") — single-node coordination via a
shared store.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import redis as redis_lib


# Lua script: atomic check-and-decrement on a token-bucket stored in a hash.
# Keys: KEYS[1] = bucket key
# Args: ARGV[1] = capacity, ARGV[2] = refill_rate (tok/sec),
#       ARGV[3] = now (epoch seconds float), ARGV[4] = cost (int)
#
# Returns:
#   { allowed (0|1), tokens_remaining, retry_after_seconds }
_LUA = """
local key       = KEYS[1]
local capacity  = tonumber(ARGV[1])
local rate      = tonumber(ARGV[2])
local now       = tonumber(ARGV[3])
local cost      = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts     = tonumber(data[2])

if tokens == nil or ts == nil then
    tokens = capacity
    ts     = now
end

-- continuous refill since last update
local delta = math.max(0, now - ts)
tokens = math.min(capacity, tokens + delta * rate)

local allowed = 0
local retry_after = 0
if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
else
    retry_after = (cost - tokens) / rate
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
-- key TTL = 2x time-to-full so unused buckets expire
redis.call('EXPIRE', key, math.ceil((capacity / rate) * 2) + 1)

return { allowed, tostring(tokens), tostring(retry_after) }
"""


_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_redis = redis_lib.from_url(_REDIS_URL, decode_responses=True)
_take_script = _redis.register_script(_LUA)


@dataclass(frozen=True)
class TakeResult:
    allowed: bool
    tokens_remaining: float
    retry_after: float


class TokenBucket:
    """A logical token bucket backed by Redis state.

    One `TokenBucket` instance represents a *configuration* (capacity +
    refill rate). Buckets are partitioned by the `key_prefix` and a
    caller-supplied subject (typically user_id + endpoint).
    """

    def __init__(
        self,
        key_prefix: str,
        capacity: int,
        refill_rate: float,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")
        self.key_prefix = key_prefix
        self.capacity = capacity
        self.refill_rate = refill_rate

    def _key(self, subject: str) -> str:
        return f"ratelimit:{self.key_prefix}:{subject}"

    def take(self, subject: str, cost: int = 1) -> TakeResult:
        key = self._key(subject)
        now = time.time()
        allowed, remaining, retry_after = _take_script(
            keys=[key],
            args=[self.capacity, self.refill_rate, now, cost],
        )
        return TakeResult(
            allowed=bool(int(allowed)),
            tokens_remaining=float(remaining),
            retry_after=float(retry_after),
        )
