#!/usr/bin/env python3
import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "ai_tutor.api.app:app",
        host=os.getenv("AI_TUTOR_API_HOST", "127.0.0.1"),
        port=int(os.getenv("AI_TUTOR_API_PORT", "8000")),
        reload=os.getenv("AI_TUTOR_API_RELOAD", "false").lower() == "true",
    )
