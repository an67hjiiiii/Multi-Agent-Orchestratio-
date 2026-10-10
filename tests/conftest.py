"""Select the explicit local-file backend for legacy isolated tests."""

import os


os.environ["APP_STORAGE_BACKEND"] = "file"
