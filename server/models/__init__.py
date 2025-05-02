"""
Models package initialization.
"""
from config.database import db
from .user import User
from .lead import Lead
from .campaign import Campaign

__all__ = ['db', 'User', 'Lead', 'Campaign'] 