from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(15), nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="patient")
    is_active = Column(Boolean, default=True)
    heart_rate = Column(String, default="72")
    bp = Column(String, default="120/80")

    appointments = relationship("Appointment", back_populates="patient")
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer,ForeignKey('users.id') ,unique=True,nullable=False)
    specialty = Column(String(100))
    experience = Column(Integer)
    consultation_fee = Column(Integer)
    bio = Column(String(500))
    is_verified = Column(Boolean, default=False)

    user = relationship("User", back_populates="doctor_profile")
    appointments = relationship("Appointment", back_populates="doctor")


class Appointment(Base):

    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    date = Column(String(50))
    time = Column(String(50)) 
    status = Column(String(50), default="upcoming")

    patient = relationship("User", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")

class Precription(Base):
    __tablename__ = 'prescriptions'

    id = Column(Integer,primary_key=True, index= True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    appointment_id = Column(Integer, ForeignKey("appointments.id"))

    medicines = Column(String(500))
    notes = Column(String(500))
    date = Column(String(50))

    doctor = relationship("Doctor")
    patient = relationship("User")

class MedicalReport(Base):

    __tablename__ = "medical_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    
    title = Column(String(100))      
    file_url = Column(String(500))   
    date = Column(String(50))

    patient = relationship("User")
    doctor = relationship("Doctor")


class Review(Base):

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    rating = Column(Integer) 
    comment = Column(String(255))
    date = Column(String(50))