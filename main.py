from fastapi import FastAPI, Depends, status
from sqlalchemy.orm import Session, relationship
from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime,timedelta
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import joinedload
import schemas
import security
import hashlib
import database
import secrets, security
import shutil
import os
from fastapi import File, UploadFile, Form
import models
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext


class Token(BaseModel):
    access_token: str
    token_type: str

class VitalsUpdate(BaseModel):
    heart_rate: str
    bp: str

models.Base.metadata.create_all(bind=database.engine)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")   

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
    
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

os.makedirs("uploads",exist_ok=True)
app.mount("/uploads",StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------------------------


# def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        
#         # FIX 1: 'email' ki jagah 'username' read karein
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
        
#         # FIX 2: TokenData ko username dein
#         # NOTE: Iske liye schemas.py mein TokenData(username: str) hona chahiye
#         token_data = schemas.TokenData(username=username) 
    
#     except JWTError:
#         raise credentials_exception
    
#     # FIX 3: Database mein 'username' se search karein
#     user = db.query(models.User).filter(models.User.email == token_data.email).first()
    
#     if user is None:
#         raise credentials_exception
#     return user

# ------------------------------------------------------


@app.post("/signup",response_model=schemas.Token)
def create_user(
    userr: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.email == userr.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security.get_password_hash(userr.password)

    new_user = models.User(
        full_name = userr.full_name,
        email = userr.email,
        phone = userr.phone,
        password = hashed_password,
        role = userr.role

    )
    access_token = security.create_access_token(data={"sub": new_user.email, "role": new_user.role})
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"access_token": access_token,
        "token_type": "bearer",
        "role": new_user.role,
        "user_id": new_user.id,
        "name": new_user.full_name
    }



@app.post("/login",response_model=schemas.Token)
def login_user(
    user_credentials: schemas.UserLogin,
    db: Session = Depends(get_db),
    
):
    db_user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    if not db_user:
         raise HTTPException(status_code=400, detail="invalid credentials")
    
    if not security.verify_password(user_credentials.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid Credentials"
        )
    
    access_token = security.create_access_token(data={"sub":db_user.email, "role":db_user.role})
    
    return {"access_token": access_token,
            "token_type": "bearer",
            "role": db_user.role,  
            "user_id": db_user.id,   
            "name": db_user.full_name
             }



@app.post("/doctor-profile")
def create_doctor(
    doctor_q: schemas.DoctorProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # if current_user.role != "doctor":
    #     raise HTTPException(status_code=403, detail="Only doctors can create a profile")
     
    existing_profile = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists")

    db_doctor = models.Doctor(
        user_id = current_user.id,
        specialty = doctor_q.specialty,
        experience = doctor_q.experience,
        consultation_fee = doctor_q.consultation_fee,
        bio = doctor_q.bio
    )
    db.add(db_doctor)
    user_to_update = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    if user_to_update:
        user_to_update.role = "doctor"
        db.add(user_to_update)

    db.commit()
    db.refresh(db_doctor)
    return {"message": "Doctor profile created successfully!"}

@app.get("/doctors")
def get_doctors(
    db: Session = Depends(get_db),

):
    doctors = db.query(models.Doctor).options(joinedload(models.Doctor.user)).all()
    results = []
    for doc in doctors:
        reviews = db.query(models.Review).filter(models.Review.doctor_id == doc.id).all()
        if reviews:
            total_stars = sum([r.rating for r in reviews])
            avg_rating = round(total_stars / len(reviews), 1)
            review_count = len(reviews)
        else:
            avg_rating = 0
            review_count = 0

        results.append({
            "id":doc.id,
            "name":doc.user.full_name,
            "specialty": doc.specialty,
            "experience": doc.experience,
            "consultation_fee": doc.consultation_fee,
            "image": "https://img.freepik.com/free-photo/doctor-with-his-arms-crossed-white-background_1368-5790.jpg",
            "rating": 4.5,
            "consultations": 120,
            "rating": avg_rating,      
            "review_count": review_count,
            "nextAvailable": "Today 5:00 PM"
        }

        )

    return results

@app.post("/book-appointment")
def create_appoints(
    ap_query: schemas.appointmentCreate,
    db: Session =Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)

):
   
    exist_doctor = db.query(models.Doctor).filter(models.Doctor.id == ap_query.doctor_id).first()
    if not exist_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    slot_token = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == ap_query.doctor_id,
        models.Appointment.date == ap_query.date,
        models.Appointment.time == ap_query.time
    ).first()
    if slot_token:
        raise HTTPException(status_code=400, detail="Sorry! This time slot is already booked.")
    
    appoint = models.Appointment(
        patient_id = current_user.id,
        doctor_id = ap_query.doctor_id,
        date = ap_query.date,
        time = ap_query.time,
        status = "upcoming"
    )
    db.add(appoint)
    db.commit()
    db.refresh(appoint)
    return {"message": "Appointment booked successfully!", "id": appoint.id}


@app.get("/appointments")
def get_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    results = []
    
  
    now = datetime.now()
    today = datetime.now().strftime("%Y-%m-%d")

   
    def check_and_update_status(apt):
        try:
          
            apt_dt = datetime.strptime(f"{apt.date} {apt.time}", "%Y-%m-%d %I:%M %p")
            
          
            if now > (apt_dt + timedelta(minutes=30)) and apt.status == "confirmed":
                apt.status = "cancelled"
                db.add(apt)
                db.commit() 
        except ValueError:
            pass
  
  
    if current_user.role == "user" or current_user.role == "patient":
        my_appts = db.query(models.Appointment).filter(models.Appointment.patient_id == current_user.id).all()

        for apt in my_appts:
            if apt.date < today:
                continue

           
            check_and_update_status(apt)

            doc_record = db.query(models.Doctor).filter(models.Doctor.id == apt.doctor_id).first()
            
            if doc_record:
                doc_user = db.query(models.User).filter(models.User.id == doc_record.user_id).first()
                
                if doc_user:
                    results.append({
                        "id": apt.id,
                        "doctorName": doc_user.full_name,
                        "doctor_id": apt.doctor_id,
                        "specialty": doc_record.specialty, 
                        "date": apt.date,
                        "time": apt.time,
                        "status": apt.status
                    })

   
    elif current_user.role == 'doctor':
        doctor_rec = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        
        if doctor_rec:
           doc_appoint = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_rec.id).all()

           for apt in doc_appoint:
                if apt.date < today:
                    continue

                check_and_update_status(apt)

                patient_user = db.query(models.User).filter(models.User.id == apt.patient_id).first()

                if patient_user:
                    results.append({
                        "id": apt.id,
                        "patientName": patient_user.full_name,
                        "patient_id": patient_user.id, 
                        "issue": "General Checkup",            
                        "date": apt.date,
                        "time": apt.time,
                        "status": apt.status,
                        "type": "Video"                       
                    })

    return results


@app.post("/prescriptions")
def create_pres(
    prescrip: schemas.PrecriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)

):
    if current_user.role != 'doctor':
        raise HTTPException(status_code=403, detail="Only doctors can write prescriptions")
    
    doc_id = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()

    new_pres = models.Precription(
        doctor_id = doc_id.id,
        medicines = prescrip.medicines,
        notes = prescrip.notes,
        patient_id = prescrip.patient_id,
        appointment_id = prescrip.appointment_id,
        date = datetime.now().strftime("%Y-%m-%d")
    )
    db.add(new_pres)

    appointment = db.query(models.Appointment).filter(models.Appointment.id == prescrip.appointment_id).first()
    if appointment:
        appointment.status = "complete"
        db.add(appointment)

    db.commit()
    db.refresh(new_pres)
    return {"message": "Prescription sent and Appointment marked as Completed!"}



@app.get("/prescription")
def get_prescrip(
    db:Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "user" and current_user.role != "patient":
        raise HTTPException(status_code=400, detail="Only patients can view prescriptions")
    
    my_pres = db.query(models.Precription).filter(models.Precription.patient_id == current_user.id).all()

    results = []

    for pres in my_pres:
        doc = db.query(models.Doctor).filter(models.Doctor.id == pres.doctor_id).first()
        db_user = db.query(models.User).filter(models.User.id == doc.user_id).first()

        if db_user:
           results.append({
            "id": pres.id,
            "doctor_name": db_user.full_name,
            "medicines": pres.medicines,
            "notes": pres.notes,
            "date": pres.date
        })

    return results


@app.post("/reports")
def create_reports(
    title: str = Form(...),
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)

):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can upload reports")
    
    doc_detail = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()

    file_location = f"uploads/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file , buffer)

    full_url = f"http://127.0.0.1:8000/{file_location}"

    new_report = models.MedicalReport(
        patient_id=patient_id,
        doctor_id=doc_detail.id,
        title=title,
        file_url=full_url,
        date=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return {"message": "Report uploaded successfully!"}


    
@app.get("/my-reports")
def get_reports(
    db:Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "user" and current_user.role != "patient":
        raise HTTPException(status_code=400, detail="Only patients can view Reports")
    
    my_report = db.query(models.MedicalReport).filter(models.MedicalReport.patient_id == current_user.id).all()
    results = []

    for repo in my_report:
        doc = db.query(models.Doctor).filter(models.Doctor.id == repo.doctor_id).first()
        doc_user = db.query(models.User).filter(models.User.id == doc.user_id).first()

        results.append({
            "id": repo.id,
            "doctor_name": doc_user.full_name,
            "title": repo.title,
            "file_url":repo.file_url,
            "date":repo.date,


        })
    return results


@app.put("/appointments/{appointment_id}")
def update_appoint(
    appointment_id: int,
    status_update: schemas.AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "doctor":
       raise HTTPException(status_code=400, detail="Only doctor can update")
    
    appoint = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()

    if not appoint:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    doctor_appoint = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if appoint.doctor_id != doctor_appoint.id:
        raise HTTPException(status_code=403, detail="You are not authorized to update this appointment")
    
    appoint.status = status_update.status
    db.commit()

    return {"message": f"Appointment status updated to {status_update.status}"}


@app.post("/reviews")
def create_review(
    revieww: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),

):
    if current_user.role != "user" and current_user.role != "patient":
        raise HTTPException(status_code=403, detail="only patient can review")
    


    appointment = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == revieww.doctor_id,
        models.Appointment.patient_id == current_user.id,
        models.Appointment.status == "completed"
    ).first()

    if not appointment:
        raise HTTPException(status_code=400, detail="You can only review doctors after a completed appointment")
    
    new_review = models.Review(
        rating=revieww.rating,
        comment=revieww.comment,
        patient_id=current_user.id,
        doctor_id=revieww.doctor_id,
        date=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(new_review)

    # doctor = db.query(models.Doctor).filter(models.Doctor.id == revieww.doctor_id).first()
    db.commit()
    db.refresh(new_review)
    return {"message": "Thank you for your review!"}


@app.get("/doctor/stats",response_model=schemas.DoshboardStats)
def dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access stats")
    
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    total_patients = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor.id).distinct().count()
    todays_str = datetime.now().strftime("%Y-%m-%d")
    todays_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.id,
        models.Appointment.date == todays_str
    ).count()

    total_reports = db.query(models.MedicalReport).filter(
        models.MedicalReport.doctor_id == doctor.id
    ).count()

    reviews = db.query(models.Review).filter(models.Review.doctor_id == doctor.id).all()
    avg_rating = 0.0
    if reviews:
        total_stars = sum([r.rating for r in reviews])
        avg_rating = round(total_stars / len(reviews),1)

    return{
        "total_patients": total_patients,
        "todays_appointments": todays_appointments,
        "total_reports": total_reports,
        "rating": avg_rating
    }

@app.get("/patient/stats")
def get_patient_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    appoint_count = db.query(models.Appointment).filter(models.Appointment.patient_id == current_user.id).count()

    return({
        "heart_rate":current_user.heart_rate,
        "bp":current_user.bp,
        "appointments":appoint_count
    })

@app.put("/patient/stats")
def update_patient_stats(
    Vitals: VitalsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    user_to_update = db.query(models.User).filter(models.User.id == current_user.id).first()
    if user_to_update:
     current_user.heart_rate = Vitals.heart_rate,
     current_user.bp = Vitals.bp,
     db.add(user_to_update)
     db.commit()
     return {"message": "Vitals updated"}
    raise HTTPException(status_code=404, detail="User not found")
