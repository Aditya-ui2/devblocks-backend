from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="patient")

    projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(String(1000))
    status = Column(String(50), default="active") # active, completed
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(String(1000))
    price = Column(Integer)
    status = Column(String(50), default="available")
    tech_stack = Column(String(255))
    client_id = Column(Integer)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    submission_url = Column(String(500), nullable=True)

    category = Column(String(100), default="General")
    
    project_id = Column(Integer, ForeignKey("projects.id"))
    messages = relationship("Message", back_populates="task")
    project = relationship("Project", back_populates="tasks")
    proposals = relationship("Proposal", back_populates="task")

class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    cover_letter = Column(String(500)) 
    bid_amount = Column(Integer)       
    status = Column(String(50), default="pending") 
    freelancer_name = Column(String(100))
    image_url = Column(String(500), nullable=True)
    
    
    task_id = Column(Integer, ForeignKey("tasks.id"))
    freelancer_id = Column(Integer, ForeignKey("users.id"))

    task = relationship("Task", back_populates="proposals")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id")) 
    sender = Column(String(50)) # 'client' ya 'freelancer'
    content = Column(String(1000))
    timestamp = Column(DateTime, default=datetime.utcnow)

    
    task = relationship("Task", back_populates="messages")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    amount = Column(Integer) 
    description = Column(String(255))
    type = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    reviewer_id = Column(Integer) 
    freelancer_id = Column(Integer) 
    rating = Column(Integer)      
    comment = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    message = Column(String(255))
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    task_id = Column(Integer, nullable=True)
    sender_name = Column(String, nullable=True)   

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    description = Column(String(500))
    price = Column(Integer)
    sales = Column(Integer, default=0)
    creator_id = Column(Integer)
    download_link = Column(String(255))