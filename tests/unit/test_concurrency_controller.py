"""Unit tests for ConcurrencyController (Platinum P6)."""

import pytest
from intelligence.concurrency_controller import ConcurrencyController, ConcurrencySlot


class TestConcurrencySlot:
    def test_valid_creation(self):
        s = ConcurrencySlot(slot_id=0, task_id="task.md")
        assert s.status == "active"
        assert s.started_at != ""

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError, match="status"):
            ConcurrencySlot(slot_id=0, task_id="task.md", status="invalid")

    def test_all_valid_statuses(self):
        for st in ("active", "completed", "timed_out", "released"):
            s = ConcurrencySlot(slot_id=0, task_id="task.md", status=st)
            assert s.status == st

    def test_to_dict(self):
        s = ConcurrencySlot(slot_id=1, task_id="task.md")
        d = s.to_dict()
        assert d["slot_id"] == 1
        assert d["task_id"] == "task.md"
        assert "started_at" in d


class TestAcquireRelease:
    def test_acquire_returns_slot(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        slot = cc.acquire("task.md")
        assert slot is not None
        assert slot.task_id == "task.md"
        assert slot.status == "active"

    def test_acquire_up_to_max(self, platinum_config):
        platinum_config["max_parallel_tasks"] = 2
        cc = ConcurrencyController(config=platinum_config)
        s1 = cc.acquire("a.md")
        s2 = cc.acquire("b.md")
        s3 = cc.acquire("c.md")
        assert s1 is not None
        assert s2 is not None
        assert s3 is None

    def test_release_frees_slot(self, platinum_config):
        platinum_config["max_parallel_tasks"] = 1
        cc = ConcurrencyController(config=platinum_config)
        slot = cc.acquire("a.md")
        cc.release(slot.slot_id)
        slot2 = cc.acquire("b.md")
        assert slot2 is not None

    def test_complete_releases(self, platinum_config):
        platinum_config["max_parallel_tasks"] = 1
        cc = ConcurrencyController(config=platinum_config)
        slot = cc.acquire("a.md")
        cc.complete(slot.slot_id)
        slot2 = cc.acquire("b.md")
        assert slot2 is not None

    def test_active_count(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        assert cc.get_active_count() == 0
        s1 = cc.acquire("a.md")
        assert cc.get_active_count() == 1
        s2 = cc.acquire("b.md")
        assert cc.get_active_count() == 2
        cc.release(s1.slot_id)
        assert cc.get_active_count() == 1

    def test_slot_ids_increment(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        s1 = cc.acquire("a.md")
        s2 = cc.acquire("b.md")
        assert s2.slot_id == s1.slot_id + 1


class TestQueue:
    def test_queue_and_dequeue(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        cc.queue("low.md", risk_score=0.2)
        cc.queue("high.md", risk_score=0.9)
        task = cc.dequeue()
        assert task == "high.md"

    def test_dequeue_empty_returns_none(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        assert cc.dequeue() is None

    def test_get_queued_order(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        cc.queue("low.md", risk_score=0.1)
        cc.queue("mid.md", risk_score=0.5)
        cc.queue("high.md", risk_score=0.9)
        queued = cc.get_queued()
        assert queued[0][0] == "high.md"
        assert queued[-1][0] == "low.md"

    def test_queue_multiple_same_risk(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        cc.queue("a.md", risk_score=0.5)
        cc.queue("b.md", risk_score=0.5)
        queued = cc.get_queued()
        assert len(queued) == 2


class TestTimeouts:
    def test_no_timeouts_fresh_slots(self, platinum_config):
        cc = ConcurrencyController(config=platinum_config)
        cc.acquire("a.md")
        timed = cc.check_timeouts()
        assert timed == []

    def test_timeout_expired_slot(self, platinum_config):
        platinum_config["task_timeout_minutes"] = 0
        cc = ConcurrencyController(config=platinum_config)
        cc.acquire("a.md")
        import time
        time.sleep(0.01)
        timed = cc.check_timeouts()
        assert "a.md" in timed
        assert cc.get_active_count() == 0
