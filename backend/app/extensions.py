"""
This module initializes Flask extensions to prevent circular imports.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
