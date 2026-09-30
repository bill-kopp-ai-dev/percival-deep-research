"""Load the private environment file mounted by the Positronic broker."""

from dotenv import load_dotenv

# Existing process variables keep priority over values from the mounted file.
# A missing file is a supported no-op for local development and unit tests.
load_dotenv("/app/.env", override=False)
