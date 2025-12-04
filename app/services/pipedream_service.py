from pipedream import Pipedream

from app.config import (
    ENVIRONMENT,
    PIPEDREAM_CLIENT_ID,
    PIPEDREAM_CLIENT_SECRET,
    PIPEDREAM_PROJECT_ID,
    setup_logger,
)

logger = setup_logger(__name__)


_client = Pipedream(
    client_id=PIPEDREAM_CLIENT_ID,
    client_secret=PIPEDREAM_CLIENT_SECRET,
    project_id=PIPEDREAM_PROJECT_ID,
    project_environment=ENVIRONMENT,
)
