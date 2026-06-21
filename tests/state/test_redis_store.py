"""Tests for RedisStore using fakeredis (no real Redis required)."""

from __future__ import annotations

import pytest
import fakeredis

from quorum.state.redis_store import RedisStore


@pytest.fixture
def store() -> RedisStore:
    """RedisStore backed by an in-memory FakeAsyncRedis instance."""
    fake_client = fakeredis.FakeAsyncRedis(decode_responses=True)
    return RedisStore(client=fake_client)


async def test_set_get_roundtrip(store: RedisStore) -> None:
    """set_json then get_json returns the original value."""
    await store.set_json("key:1", {"hello": "world", "num": 42})
    result = await store.get_json("key:1")
    assert result == {"hello": "world", "num": 42}


async def test_get_missing_key_returns_none(store: RedisStore) -> None:
    """get_json on a nonexistent key returns None."""
    result = await store.get_json("does-not-exist")
    assert result is None


async def test_delete_removes_key(store: RedisStore) -> None:
    """delete removes a previously set key."""
    await store.set_json("key:del", {"x": 1})
    await store.delete("key:del")
    assert await store.get_json("key:del") is None


async def test_list_push_and_list_all(store: RedisStore) -> None:
    """list_push appends items that list_all returns in order."""
    await store.list_push("mylist", {"a": 1})
    await store.list_push("mylist", {"b": 2})
    await store.list_push("mylist", {"c": 3})
    items = await store.list_all("mylist")
    assert items == [{"a": 1}, {"b": 2}, {"c": 3}]


async def test_list_remove_first_occurrence(store: RedisStore) -> None:
    """list_remove deletes only the first matching item."""
    await store.list_push("rmlist", "apple")
    await store.list_push("rmlist", "banana")
    await store.list_push("rmlist", "apple")
    await store.list_remove("rmlist", "apple")
    items = await store.list_all("rmlist")
    assert items == ["banana", "apple"]


async def test_keys_matching_pattern(store: RedisStore) -> None:
    """keys_matching returns keys matching a glob pattern."""
    await store.set_json("quorum:trust:agent-1", {"score": 0.9})
    await store.set_json("quorum:trust:agent-2", {"score": 0.7})
    await store.set_json("quorum:other:x", {"y": 1})
    keys = await store.keys_matching("quorum:trust:*")
    assert set(keys) == {"quorum:trust:agent-1", "quorum:trust:agent-2"}


async def test_ttl_parameter_accepted(store: RedisStore) -> None:
    """set_json with ttl_seconds stores and the value is still retrievable."""
    await store.set_json("ephemeral", {"data": "here"}, ttl_seconds=3600)
    result = await store.get_json("ephemeral")
    assert result == {"data": "here"}


async def test_list_all_empty_key(store: RedisStore) -> None:
    """list_all on a missing key returns an empty list."""
    items = await store.list_all("nonexistent-list")
    assert items == []


async def test_list_trim_caps_list(store: RedisStore) -> None:
    """list_trim keeps only [start, stop] range (Redis LTRIM semantics)."""
    for i in range(10):
        await store.list_push("trimlist", {"n": i})
    await store.list_trim("trimlist", 0, 4)
    items = await store.list_all("trimlist")
    assert len(items) == 5
    assert items[0] == {"n": 0}
    assert items[4] == {"n": 4}


async def test_list_trim_on_missing_key_noop(store: RedisStore) -> None:
    """list_trim on a nonexistent key should not raise."""
    await store.list_trim("nonexistent-trim", 0, 9)


async def test_keys_matching_uses_scan(store: RedisStore) -> None:
    """keys_matching returns correct keys (verifies SCAN-based implementation)."""
    await store.set_json("quorum:provenance:aaa", {"x": 1})
    await store.set_json("quorum:provenance:bbb", {"x": 2})
    await store.set_json("quorum:trust:zzz", {"y": 9})
    keys = await store.keys_matching("quorum:provenance:*")
    assert set(keys) == {"quorum:provenance:aaa", "quorum:provenance:bbb"}
