#!/usr/bin/env python3
import os

import uvicorn
from ai_tutor.generation.factory import load_dotenv
from ai_tutor.utils.logging import configure_logging


if __name__ == "__main__":
    # Load the project-local environment before FastAPI imports its service.
    # This is important for AI_TUTOR_DATABASE_URL: the repository is created
    # during app initialization, before a model generator is requested.
    load_dotenv()
    configure_logging()
    uvicorn.run(
        "ai_tutor.api.app:app",
        host=os.getenv("AI_TUTOR_API_HOST", "127.0.0.1"),
        port=int(os.getenv("AI_TUTOR_API_PORT", "8000")),
        reload=os.getenv("AI_TUTOR_API_RELOAD", "false").lower() == "true",
    )
