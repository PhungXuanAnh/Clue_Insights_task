"""
Base model with common fields and utility methods.
"""
from datetime import UTC, datetime

from app import db


class BaseModel(db.Model):
    """
    Base model class that includes common fields and methods for all models.
    """
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model.
        """
        return {column.name: getattr(self, column.name) 
                for column in self.__table__.columns} 