from __future__ import annotations

import uvicorn

from .api import app


def serve() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
