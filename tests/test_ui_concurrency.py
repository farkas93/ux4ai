import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import gradio as gr
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipm_toolkit.ui.concurrency import SessionBlocks


def submit(client, fn, session_hash, data=None):
    response = client.post(
        "/app/gradio_api/queue/join",
        json={"fn_index": fn._id, "session_hash": session_hash, "data": data or []},
    )
    assert response.status_code == 200, response.text
    return response.json()["event_id"]


def completed(client, session_hash):
    response = client.get("/app/gradio_api/queue/data", params={"session_hash": session_hash})
    messages = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    results = [message for message in messages if message["msg"] == "process_completed"]
    assert results and all(result["success"] for result in results), messages
    return results


def test_twenty_sessions_progress_in_parallel_but_each_reads_updated_state():
    release = threading.Event()
    eight_started = threading.Event()
    lock = threading.Lock()
    active = peak = 0
    seen = []

    def slow_increment(value, request: gr.Request):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            if active == 8:
                eight_started.set()
            seen.append((request.session_hash, value))
        try:
            assert release.wait(timeout=10)
            return value + 1
        finally:
            with lock:
                active -= 1

    with SessionBlocks(analytics_enabled=False) as blocks:
        value = gr.State(0)
        first = gr.Button("Save")
        second = gr.Button("Switch")
        first.click(slow_increment, value, value)
        second.click(slow_increment, value, value)
    blocks.queue()
    functions = list(blocks.fns.values())
    app = gr.mount_gradio_app(FastAPI(), blocks, path="/app")
    sessions = [f"student-{index}" for index in range(20)]
    with TestClient(app) as client:
        with ThreadPoolExecutor(max_workers=20) as workers:
            # Two callbacks per browser, both submitted before either finishes.
            for session_hash in sessions:
                for fn in functions:
                    submit(client, fn, session_hash, [None])
            streams = [workers.submit(completed, client, session_hash) for session_hash in sessions]
            try:
                assert eight_started.wait(timeout=5)
                assert peak == 8
                assert len({session_hash for session_hash, _value in seen}) == 8
                assert all(value == 0 for _session_hash, value in seen)
            finally:
                release.set()
            assert all(len(stream.result(timeout=15)) == 2 for stream in streams)
        assert all(blocks.state_holder[session_hash][value._id] == 2 for session_hash in sessions)
        assert peak <= 8
        assert not blocks._session_gates


def test_queued_same_browser_callbacks_do_not_occupy_other_students_slots():
    release = threading.Event()
    first_started = threading.Event()
    other_started = threading.Event()

    def slow_action(request: gr.Request):
        if request.session_hash == "busy-browser":
            first_started.set()
            assert release.wait(timeout=10)
        else:
            other_started.set()
        return "done"

    with SessionBlocks(analytics_enabled=False) as blocks:
        gr.Button().click(slow_action, outputs=gr.Textbox())
    blocks.queue()
    fn = next(iter(blocks.fns.values()))
    app = gr.mount_gradio_app(FastAPI(), blocks, path="/app")
    with TestClient(app) as client:
        for _ in range(20):
            submit(client, fn, "busy-browser")
        submit(client, fn, "other-browser")
        try:
            assert first_started.wait(timeout=5)
            assert other_started.wait(timeout=5)
            assert len(completed(client, "other-browser")) == 1
        finally:
            release.set()
        assert len(completed(client, "busy-browser")) == 20


def test_direct_api_calls_serialize_preprocessing_and_release_failed_session():
    entered = asyncio.Event()
    release = asyncio.Event()

    async def increment(value):
        if value == 0:
            entered.set()
            await release.wait()
        return value + 1

    with SessionBlocks(analytics_enabled=False) as blocks:
        value = gr.State(0)
        gr.Button().click(increment, value, value)
    fn = next(iter(blocks.fns.values()))

    async def run():
        state = blocks.state_holder["direct-browser"]
        first = asyncio.create_task(blocks.process_api(fn, [None], state=state, session_hash="direct-browser"))
        await asyncio.wait_for(entered.wait(), timeout=2)
        second = asyncio.create_task(blocks.process_api(fn, [None], state=state, session_hash="direct-browser"))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)
        assert state[value._id] == 2
        with pytest.raises(KeyError):
            await blocks.process_api(999, [], state=state, session_hash="direct-browser")
        assert not blocks._session_gates

    asyncio.run(run())
