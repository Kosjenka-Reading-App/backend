from sqlalchemy import Column, Integer, String, Float

from database import Base


class Exercise(Base):
    __tablename__ = "exercise"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String)
    complexity = Column(Float)
    text = Column(String)
