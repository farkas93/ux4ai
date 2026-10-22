"""Bounded, per-browser callback scheduling for pinned Gradio 5.44.1.

Gradio concurrency IDs are global. Its queue must skip busy browser sessions,
and the complete preprocess/callback/postprocess pipeline must be serialized
within a session (locking only the callback reads stale gr.State values).
"""

import asyncio
import inspect
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import gradio as gr
from gradio.queueing import Queue

from ..config import get_settings


class SessionQueue(Queue):
    def get_events(self):
        busy_sessions = {
            event.session_hash
            for job in self.active_jobs if job
            for event in job
        }
        for concurrency_id, event_queue in self.event_queue_per_concurrency_id.items():
            if (
                event_queue.concurrency_limit is not None
                and event_queue.current_concurrency >= event_queue.concurrency_limit
            ):
                continue
            for index, event in enumerate(event_queue.queue):
                if event.session_hash not in busy_sessions:
                    event_queue.queue.pop(index)
                    return [event], False, concurrency_id
        return None


@dataclass
class _SessionGate:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


class SessionBlocks(gr.Blocks):
    def __init__(self, *args, **kwargs):
        self._session_gates: dict[str, _SessionGate] = {}
        self._ui_slots = asyncio.Semaphore(get_settings().ui_concurrency_limit)
        super().__init__(*args, **kwargs)

    @asynccontextmanager
    async def _session_slot(self, session_hash):
        key = session_hash or "unscoped"
        gate = self._session_gates.setdefault(key, _SessionGate())
        gate.users += 1
        try:
            # Wait for this browser before consuming a global slot. Twenty
            # pending callbacks from one browser must not block other students.
            async with gate.lock, self._ui_slots:
                yield
        finally:
            gate.users -= 1
            if gate.users == 0:
                del self._session_gates[key]

    async def process_api(
        self, block_fn, inputs, state=None, request=None, iterator=None,
        session_hash=None, **kwargs,
    ):
        async with self._session_slot(session_hash):
            return await super().process_api(
                block_fn, inputs, state=state, request=request, iterator=iterator,
                session_hash=session_hash, **kwargs,
            )

    def queue(self, *args, **kwargs):
        limit = get_settings().ui_concurrency_limit
        for fn in self.fns.values():
            if fn.batch or inspect.isgeneratorfunction(fn.fn) or inspect.isasyncgenfunction(fn.fn):
                raise ValueError("The session queue supports only non-batched, non-streaming callbacks")
            fn.concurrency_id = "workspace-sessions"
            fn.concurrency_limit = limit
        kwargs.setdefault("default_concurrency_limit", limit)
        super().queue(*args, **kwargs)
        previous = self._queue
        self._queue = SessionQueue(
            live_updates=previous.live_updates,
            concurrency_count=previous.max_thread_count,
            update_intervals=previous.update_intervals,
            max_size=previous.max_size,
            blocks=self,
            default_concurrency_limit=previous.default_concurrency_limit,
        )
        return self
