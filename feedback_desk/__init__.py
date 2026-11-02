"""Feedback Desk: a community feedback and complaints desk."""
from . import core
from .web import create_app

__all__ = ["core", "create_app"]
