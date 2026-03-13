import asyncio
import sys
from pathlib import Path

import pulumi
import pytest


# Ensure tests can import top-level project packages (e.g., components).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _PulumiMocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        return f"{args.name}_id", args.inputs

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {}


@pytest.fixture(autouse=True)
def _pulumi_test_runtime():
    # Python 3.14 no longer creates a default loop automatically.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    pulumi.runtime.set_mocks(_PulumiMocks())
    try:
        yield
    finally:
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        asyncio.set_event_loop(None)
