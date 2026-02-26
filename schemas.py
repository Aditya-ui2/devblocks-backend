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
    email: str    
    name: str
 
class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ==---------------------
    

class TaskCreate(BaseModel):
    title: str
    description: str
    price: int
    tech_stack: str
    category: str = "General"
    client_id: int


class ProjectCreate(BaseModel):
    title: str
    description: str
    owner_id: int 
    tasks: List[TaskCreate] 

class ProjectResponse(BaseModel):
    id: int
    title: str
    status: str
    
    model_config = ConfigDict(from_attributes=True)

class ProposalCreate(BaseModel):
    cover_letter: str
    bid_amount: int
    freelancer_name: str 

class ProposalResponse(ProposalCreate):
    id: int
    status: str
    task_id: int

    class Config:
        from_attributes = True



class MessageCreate(BaseModel):
    sender: str
    content: str

class MessageResponse(MessageCreate):
    id: int
    task_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    task_id: int
    freelancer_id: int
    rating: int
    comment: str


class UserUpdate(BaseModel):
    full_name: str
    title: str = "Freelancer"
    skills: str = "React, Python" 
    bio: str = ""


class AssetCreate(BaseModel):
    title: str
    description: str
    price: int



class ProjectIdea(BaseModel):
    description: str



class TaskUpdate(BaseModel):
    title: str
    price: int
    description: str

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    price: int
    tech_stack: Optional[str] = None
    category: Optional[str] = None
    freelancer_id: Optional[int] = None
    status: str

    class Config:
        orm_mode = True