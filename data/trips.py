import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Trip(SqlAlchemyBase):
    __tablename__ = "trips"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    city = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    country = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    latitude = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    longitude = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    photo_filename = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    is_public = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    user = orm.relationship("User", back_populates="trips")

    
    def to_dict(self, only=None):
        data = {
            "id": self.id,
            "title": self.title,
            "city": self.city,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "description": self.description,
            "photo_filename": self.photo_filename,
            "is_public": self.is_public,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "user_id": self.user_id,
            "user.name": self.user.name if self.user else None,
        }
        if only:
            return {key: data[key] for key in only}
        return data

    def __repr__(self):
        return f"<Trip> {self.id} {self.title} {self.city}"
