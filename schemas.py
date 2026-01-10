from pydantic import BaseModel, ConfigDict, Field, EmailStr
from sqlalchemy import DateTime
from typing import Optional
from datetime import datetime, date
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import List, Annotated

from pydantic import BaseModel
from typing import Optional

class TokenData(BaseModel):
    email: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str      
    user_id: int    
    name: str
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "patient"

    class config:
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    
    class Config:
        from_attributes = True


# -------------------------------------------


class DoctorProfileCreate(BaseModel):
    specialty: str
    experience: int
    consultation_fee: int 
    bio: str

class DoctorResponse(BaseModel):
    specialty: str
    experience: int
    user: UserResponse

    class config:
        from_attributes = True


# ==========-----------------------
        
class appointmentCreate(BaseModel):
    date: str
    time: str
    doctor_id: int

class appointmentResponse(BaseModel):
    id: int
    doctor_id: int
    doctor_name: str
    specialty: str
    date: str
    time: str
    status: str

    class Config:
        orm_mode = True



# ----------------------------------
        
class PrecriptionCreate(BaseModel):
    medicines: str
    notes: str
    patient_id: int
    appointment_id: int


class PrescriptionResponse(BaseModel):
    id: int
    doctor_name: str
    medicines: str
    notes: str
    date: str

    class Config:
        orm_mode = True

# ===-----------------------------

class ReportResponse(BaseModel):
    id: int
    doctor_name: str
    title: str
    file_url: str
    date: str

    class Config:
        from_attributes = True


# =------------------------------


class AppointmentStatusUpdate(BaseModel):
    status: str



class ReviewCreate(BaseModel):
    rating: int
    comment: str
    doctor_id: int

class ReviewResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int

class DoshboardStats(BaseModel):
    total_patients: int
    todays_appointments: int
    total_reports: int
    rating: float

