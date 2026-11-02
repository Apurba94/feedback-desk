"""Start the app: python -m feedback_desk [data.db] [--port 8033]"""
import sys

from .fieldkit import main_cli
from .web import create_app

sys.exit(main_cli(create_app, "feedback.db", 8033, sys.argv))
