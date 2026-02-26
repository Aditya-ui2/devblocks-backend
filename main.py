from fastapi import FastAPI, Depends, status
from sqlalchemy.orm import Session, relationship
from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect # 👈 WebSocket add hua
from typing import List, Dict
import json
from sqlalchemy.orm import aliased
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime,timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func 
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import joinedload
import schemas
import security
from google import genai
import json
import json
import random
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


app = FastAPI()

class Token(BaseModel):
    access_token: str
    token_type: str

class VitalsUpdate(BaseModel):
    heart_rate: str
    bp: str

class ProjectIdea(BaseModel):
    description: str

client = genai.Client(api_key="AIzaSyDPqTheDwCRx44juR0rqtSnEbSsrTaiYPU")
models.Base.metadata.create_all(bind=database.engine)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")   

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Har Task ID ke liye alag list hogi connections ki
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: int):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, websocket: WebSocket, task_id: int):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)

    async def broadcast(self, message: dict, task_id: int):
        # Sirf us task ke logo ko message bhejo
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                await connection.send_text(json.dumps(message))

manager = ConnectionManager()


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()




origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # ⭐ OPTIONS allow karega
    allow_headers=["*"],
)

os.makedirs("uploads",exist_ok=True)
app.mount("/uploads",StaticFiles(directory="uploads"), name="uploads")

@app.post("/signup",response_model=schemas.UserResponse)
def create_user(
    db_user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    email_exist = db.query(models.User).filter(models.User.email == db_user.email).first()
    if email_exist:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="email already registered")
    
    hashed_password = security.get_password_hash(db_user.password)
    
    new_user = models.User(
        full_name = db_user.full_name,
        email = db_user.email,
        password = hashed_password,
        role = db_user.role

    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post("/login")
def login_user(
    user: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    email_exist = db.query(models.User).filter(models.User.email == user.email).first()
    
    if not email_exist:
        raise HTTPException(status_code=404, detail="Invalid Credentials")

    if not security.verify_password(user.password, email_exist.password):
        raise HTTPException(status_code=404, detail="Invalid Credentials")

    return {
        "access_token": "dummy",  # abhi token ignore karo
        "user_id": email_exist.id,
        "full_name": email_exist.full_name,
        "role": email_exist.role
    }

@app.post("/projects",response_model=schemas.ProjectResponse)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db)
):
    new_project = models.Project(
        title = project.title,
        description = project.description,
        owner_id = project.owner_id,
        status = "open"
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    for task in project.tasks:
        new_task = models.Task(
            title=task.title,
            description=task.description,
            price=task.price,
            tech_stack=task.tech_stack,
            client_id = task.client_id,
            category=task.category,
            status="available",
            project_id=new_project.id

        )
        db.add(new_task)

    db.commit()
    return new_project

# ---------------------------------------------------------------------
@app.post("/break-project")
async def break_project_into_tasks(idea: ProjectIdea):
    prompt = f"""
    Act as a Senior Tech Lead. 
    User wants to build: "{idea.description}".
    
    IMPORTANT: 
    - If the user explicitly mentions "React", "Frontend", or "UI", generate ONLY Frontend/Component tasks.
    - If the user mentions "Node", "Python", "Backend", generate ONLY Backend/API tasks.
    - If unspecified, generate a mix of Fullstack tasks.

    Break this into 5-6 micro-technical tasks.
    For each task, provide:
    1. title (Short technical name)
    2. description (Specific tech detail)
    3. price (USD $10-$50)
    4. tech_stack (Specific tools, e.g., Redux, Tailwind, React Query)
    5. category (Must be exactly one of: "Frontend", "Backend", "DevOps")

    Strictly return valid JSON like this:
    [
        {{"id": 1, "title": "Navbar Component", "description": "Responsive nav with framer motion", "price": 15, "tech_stack": "React, Tailwind", "category": "Frontend"}},
        ...
    ]
    """

    try:
        # Client call (Safe wala jo humne fix kiya tha)
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt
        )
        
        # Cleaning Logic
        cleaned_response = response.text.strip()
        if "```json" in cleaned_response:
            cleaned_response = cleaned_response.replace("```json", "").replace("```", "")
        if "```" in cleaned_response:
            cleaned_response = cleaned_response.replace("```", "")
            
        tasks = json.loads(cleaned_response)
        
        # Thoda random data UI ke liye
        import random
        for i, task in enumerate(tasks):
            task['id'] = i + 1
            task['status'] = 'available'
            task['difficulty'] = random.choice(['Easy', 'Medium', 'Hard'])
            task['devs'] = random.randint(1, 10)
            
        return {"tasks": tasks}

    except Exception as e:
        print(f"Error: {e}")
        return {"tasks": []}
# ------------------------------------------------------------------------
    

@app.get("/tasks")
def get_all_tasks(search: str = "", db: Session = Depends(get_db)):
    query = db.query(models.Task)
    
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Task.title.ilike(search_term),
                models.Task.description.ilike(search_term),
                models.Task.tech_stack.ilike(search_term)
            )
        )
    
    return query.all()

@app.put("/tasks/{task_id}/start")
def start_task(task_id: int, freelancer_id: int, db: Session = Depends(get_db)):

    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if not task:
        return {"error": "Task not found"}

    task.status = "in_progress"
    
    task.freelancer_id = freelancer_id   # ⭐ MOST IMPORTANT

    db.commit()
    db.refresh(task)

    return task


@app.get("/my-tasks/{user_id}")
def get_active_tasks(user_id: int, role: str, db: Session = Depends(get_db)):

    if role == "freelancer":
        tasks = db.query(models.Task).filter(
            models.Task.status == "in_progress",
            models.Task.freelancer_id == user_id
        ).all()

    else:  # client
        tasks = db.query(models.Task).filter(
            models.Task.status == "in_progress",
            models.Task.owner_id == user_id
        ).all()

    return tasks


@app.post("/tasks/{task_id}/submit")
async def submit_task(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    file_location = f"uploads/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    
    task.status = "completed"
    task.submission_url = file_location

    db.commit()

    return {"message": "Work submitted & Payment released!","file_path": file_location}


@app.get("/reviews")
def get_reviews(
    db: Session = Depends(get_db)
):
    task = db.query(models.Task).filter(
        models.Task.status == "completed",
        models.Task.submission_url != None
    ).all()
    return task


@app.post("/tasks/{task_id}/apply")
def apply_for_task(
    task_id: int,
    cover_letter: str = Form(...),
    bid_amount: int = Form(...),
    freelancer_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == freelancer_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_proposal = models.Proposal(
        task_id=task_id,
        cover_letter=cover_letter,
        bid_amount=bid_amount,
        freelancer_name=user.full_name,
        freelancer_id=user.id,
        status="pending"
    )

    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)
    return new_proposal

@app.get("/tasks/{task_id}/proposals")
def get_task_proposals(task_id: int, db: Session = Depends(get_db)):
    proposals = db.query(models.Proposal).filter(models.Proposal.task_id == task_id).all()
    return proposals


@app.put("/proposals/{proposal_id}/accept")
def accept_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.query(models.Proposal).filter(models.Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
   
    task = proposal.task
    task.status = "in_progress"
    task.freelancer_id = proposal.freelancer_id
    
   
    notif = models.Notification(
        user_id=proposal.freelancer_id,
        message=f"🎉 You were hired for: {task.title}",
        type="hired",
        task_id=task.id,          
        sender_name=proposal.freelancer_name, 
        is_read=False,
        timestamp=datetime.utcnow()
    )
    db.add(notif)
    
    db.commit()
    return {"message": "Freelancer hired and notified"}


@app.put("/tasks/{task_id}/approve")
def approve_task_payment(task_id: int, db: Session = Depends(get_db)):

    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "paid"

    transaction = models.Transaction(
        user_id=task.freelancer_id,  
        amount=task.price,
        description=f"Payment for project: {task.title}",
        type="credit"
    )
    db.add(transaction)

    notif = models.Notification(
        user_id=task.freelancer_id,
        message=f"💰 Payment received for {task.title}",
        type="payment",
        task_id=task.id,       
        sender_name="Client",  
        is_read=False,
        timestamp=datetime.utcnow()
    )
    db.add(notif)

    db.commit()
    return {"message": "Payment released"}


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, task_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
           
            new_message = models.Message(
                task_id=task_id,
                sender=message_data['sender'],
                content=message_data['content']
            )
            db.add(new_message)
            db.commit()
            
           
            response = {
                "sender": new_message.sender,
                "content": new_message.content,
                "timestamp": str(new_message.timestamp)
            }
            
           
            await manager.broadcast(response, task_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)


@app.get("/tasks/{task_id}/messages", response_model=List[schemas.MessageResponse])
def get_chat_history(task_id: int, db: Session = Depends(get_db)):
    return db.query(models.Message).filter(models.Message.task_id == task_id).all()


@app.get("/wallet/history")
def get_wallet_history(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.timestamp.desc()).all()


@app.post("/reviews")
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    # 1. Check karo review pehle se toh nahi hai
    existing = db.query(models.Review).filter(models.Review.task_id == review.task_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already exists for this task")

    # 2. Save Review
    new_review = models.Review(
        task_id=review.task_id,
        reviewer_id=1, 
        freelancer_id=review.freelancer_id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(new_review)
    db.commit()
    return {"message": "Review submitted successfully!"}


@app.get("/reviews")
def get_all_reviews(db: Session = Depends(get_db)):
    return db.query(models.Review).all()

@app.get("/reviews/{user_id}")
def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Review).filter(models.Review.freelancer_id == user_id).all()



@app.put("/users/{user_id}")
def update_user_profile(user_id: int, user_data: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.full_name = user_data.full_name
    
    db.commit()
    return {"message": "Profile updated successfully", "user": user.full_name}



@app.get("/notifications/{user_id}")
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).order_by(models.Notification.timestamp.desc()).all()

@app.put("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: int, db: Session = Depends(get_db)):
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "Marked as read"}



@app.get("/feed")
def get_live_feed(db: Session = Depends(get_db)):
    feed = []
    
    txns = db.query(models.Transaction).order_by(models.Transaction.timestamp.desc()).limit(5).all()
    for t in txns:
        feed.append({
            "text": f"💰 Payment of ${t.amount} released for project.",
            "time": t.timestamp,
            "type": "sale"
        })


    reviews = db.query(models.Review).order_by(models.Review.timestamp.desc()).limit(5).all()
    for r in reviews:
        feed.append({
            "text": f"⭐ Client rated a Freelancer {r.rating} stars!",
            "time": r.timestamp,
            "type": "project"
        })

    feed.sort(key=lambda x: x['time'], reverse=True)
    
    return feed


@app.post("/assets")
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    new_asset = models.Asset(
        title=asset.title,
        description=asset.description,
        price=asset.price,
        creator_id=1,
        sales=0,
        download_link="#"
    )
    db.add(new_asset)
    db.commit()
    return {"message": "Asset listed for sale!"}

@app.get("/assets")
def get_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()



# --- BUY ASSET ENDPOINT ---
@app.post("/assets/{asset_id}/buy")
def buy_asset(asset_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    # 1. Asset dhoondo
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # 2. Buyer se paise kaato (Debit)
    buyer_txn = models.Transaction(user_id=user_id, amount=-asset.price, description=f"Purchased: {asset.title}", type="debit")
    db.add(buyer_txn)

    # 3. Creator ko paise do (Credit)
    seller_txn = models.Transaction(user_id=asset.creator_id, amount=asset.price, description=f"Sold: {asset.title}", type="credit")
    db.add(seller_txn)

    # 4. Sales count badhao aur Notifications bhejo
    asset.sales += 1
    db.add(models.Notification(user_id=user_id, message=f"✅ Purchased {asset.title}"))
    db.add(models.Notification(user_id=asset.creator_id, message=f"💰 Sold asset '{asset.title}'"))

    db.commit()
    return {"message": "Purchase successful"}


@app.post("/break-project")
def break_project(idea: ProjectIdea):
    # Asli AI (Gemini/OpenAI) lagana ho toh yahan API call hogi
    # Abhi ke liye hum "Smart Logic" use kar rahe hain
    
    desc = idea.description.lower()
    tasks = []

    # Logic: Keyword ke hisaab se tasks banao
    if "shop" in desc or "store" in desc or "commerce" in desc:
        tasks.append({"title": "Design Product Page", "description": "Grid layout with filters", "price": 40, "category": "Frontend", "tech_stack": "React"})
        tasks.append({"title": "Setup Stripe Payment", "description": "Integrate payment gateway", "price": 80, "category": "Backend", "tech_stack": "Python"})
    
    elif "chat" in desc or "social" in desc:
        tasks.append({"title": "Setup WebSocket Server", "description": "Real-time messaging backend", "price": 90, "category": "Backend", "tech_stack": "FastAPI"})
        tasks.append({"title": "Chat UI Components", "description": "Message bubbles and list", "price": 45, "category": "Frontend", "tech_stack": "React"})
    
    # Default Tasks (Sabke liye)
    tasks.append({"title": "Setup Database Schema", "description": "Define User and Data models", "price": 30, "category": "Backend", "tech_stack": "SQL"})
    tasks.append({"title": "Authentication System", "description": "Login/Signup with JWT", "price": 50, "category": "Backend", "tech_stack": "FastAPI"})

    return {"tasks": tasks}


# --- USER STATS ENDPOINT ---
@app.get("/stats/{user_id}")
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    # 1. Total Earnings (Saare Credit Transactions ka sum)
    total_earnings = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user_id, 
        models.Transaction.type == "credit"
    ).scalar() or 0

    # 2. Active Tasks (Jo abhi chal rahe hain)
    active_tasks = db.query(models.Task).filter(
        models.Task.freelancer_id == user_id, 
        models.Task.status == "in_progress"
    ).count()

    # 3. Passive Income (Sirf 'Sold asset' wale transactions)
    passive_income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user_id, 
        models.Transaction.type == "credit",
        models.Transaction.description.contains("Sold asset")
    ).scalar() or 0

    # 4. Completed (Win Rate ke liye)
    completed = db.query(models.Task).filter(
        models.Task.freelancer_id == user_id, 
        models.Task.status == "completed"
    ).count()

    return {
        "earnings": total_earnings,
        "active_tasks": active_tasks,
        "passive_income": passive_income,
        "completion_rate": 98 if completed > 0 else 0 # Dummy calculation
    }

# --- GET ALL CLIENT PROPOSALS ---
@app.get("/client/{client_id}/proposals")
def get_client_proposals(client_id: int, db: Session = Depends(get_db)):
    # 1. Client ke saare Projects dhoondo
    projects = db.query(models.Project).filter(models.Project.owner_id == client_id).all()
    project_ids = [p.id for p in projects]
    
    # 2. Un projects ke saare Tasks dhoondo
    tasks = db.query(models.Task).filter(models.Task.project_id.in_(project_ids)).all()
    task_ids = [t.id for t in tasks]
    
    # 3. Un tasks ke saare Pending Proposals dhoondo
    proposals = db.query(models.Proposal).filter(
        models.Proposal.task_id.in_(task_ids),
        models.Proposal.status == "pending"
    ).all()
    
   
    result = []
    for p in proposals:
        task = next((t for t in tasks if t.id == p.task_id), None)
        result.append({
            "id": p.id,
            "freelancer_name": p.freelancer_name,
            "bid_amount": p.bid_amount,
            "cover_letter": p.cover_letter,
            "task_title": task.title if task else "Unknown Task",
            "task_id": p.task_id,
            "image_url": p.image_url
        })
    return result


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.title = task_data.title
    task.price = task_data.price
    task.description = task_data.description
    db.commit()
    return {"message": "Task updated successfully"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Linked proposals bhi delete kar sakte ho, par abhi simple rakhte hain
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}



@app.get("/wallet/{user_id}")
def get_wallet_data(user_id: int, db: Session = Depends(get_db)):
    # 1. Saari transactions laao (Latest first)
    txs = db.query(models.Transaction).filter(models.Transaction.user_id == user_id).order_by(models.Transaction.id.desc()).all()
    
    # 2. Balance Calculate karo (Credit aur Debit ka total sum)
    # Note: Backend me Withdrawal negative amount (-100) save karta hai
    current_balance = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.user_id == user_id).scalar() or 0
    
    total_earned = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user_id, 
        models.Transaction.type == "credit"
    ).scalar() or 0
            
    return {
        "history": txs,
        "total_earned": total_earned,
        "balance": current_balance
    }
@app.post("/wallet/{user_id}/add")
def add_funds_with_id(user_id: int, amount: int, db: Session = Depends(get_db)):
    """
    Frontend aksar URL mein ID bhejta hai, isliye hum ye endpoint fix kar rahe hain.
    """
    new_tx = models.Transaction(
        user_id=user_id,
        amount=amount,
        description="Funds Added via Bank",
        type="credit",
        timestamp=datetime.utcnow()
    )
    db.add(new_tx)
    db.commit()
    return {"message": "Funds Added Successfully", "new_balance_added": amount}

@app.post("/wallet/{user_id}/withdraw")
def withdraw_funds(user_id: int, amount: int, db: Session = Depends(get_db)):
    # Balance check logic yahan add kar sakte ho
    
    new_tx = models.Transaction(
        user_id=user_id,
        amount=-amount, # Negative for withdrawal
        description="Withdrawal to Bank Account",
        type="debit",
        timestamp=datetime.utcnow()
    )
    db.add(new_tx)
    db.commit()
    return {"message": "Withdrawal Successful"}


# --- 2. ASSET STORE API (Assets Table Use Karega) ---

@app.get("/assets")
def get_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()

@app.post("/assets")
def create_asset(asset: dict, db: Session = Depends(get_db)):
    # Frontend se data aayega
    new_asset = models.Asset(
        title=asset['title'],
        description=asset['description'],
        price=asset['price'],
        creator_id=asset['creator_id'],
        sales=0,
        download_link="http://example.com/file.zip" # Dummy link
    )
    db.add(new_asset)
    db.commit()
    return {"message": "Asset Listed!"}

@app.post("/assets/{asset_id}/buy")
def buy_asset(asset_id: int, user_id: int, db: Session = Depends(get_db)):
    # 1. Asset dhoondo
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        return {"error": "Asset not found"}
        
    # 2. Buyer ke account se paise kato (Debit)
    debit_tx = models.Transaction(
        user_id=user_id,
        amount=-asset.price,
        description=f"Bought Asset: {asset.title}",
        type="debit",
        timestamp=datetime.utcnow()
    )
    
    # 3. Creator ke account me paise daalo (Credit)
    credit_tx = models.Transaction(
        user_id=asset.creator_id,
        amount=asset.price,
        description=f"Asset Sold: {asset.title}",
        type="credit",
        timestamp=datetime.utcnow()
    )
    
    # 4. Sales count badhao
    asset.sales += 1
    
    db.add(debit_tx)
    db.add(credit_tx)
    db.commit()
    
    return {"message": "Asset Purchased Successfully!"}



# --- HIRE FREELANCER ENDPOINT ---
@app.post("/proposals/{proposal_id}/hire")
def hire_freelancer(proposal_id: int, db: Session = Depends(get_db)):

    proposal = db.query(models.Proposal).filter(
        models.Proposal.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    task = db.query(models.Task).filter(
        models.Task.id == proposal.task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # ⭐ THIS IS THE MOST IMPORTANT PART
    task.freelancer_id = proposal.freelancer_id
    task.status = "in_progress"

    proposal.status = "accepted"

    db.commit()

    return {"message": "Freelancer Hired Successfully"}

@app.get("/notifications/{user_id}")
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).order_by(models.Notification.id.desc()).all()



@app.post("/wallet/add")
def add_funds_secure(amount: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    Ye secure wala version hai jo Token se ID leta hai.
    """
    new_tx = models.Transaction(
        user_id=current_user.id, 
        amount=amount, 
        description="Funds Added via Bank (Secure)", 
        type="credit",
        timestamp=datetime.utcnow()
    )
    db.add(new_tx)
    db.commit()
    return {"message": "Funds Added", "user": current_user.full_name}



@app.get("/wallet/{user_id}/analytics")
def get_wallet_analytics(user_id: int, db: Session = Depends(get_db)):

    last_7_days = datetime.utcnow() - timedelta(days=7)

    results = db.query(
        func.date(models.Transaction.timestamp).label("date"),
        func.sum(models.Transaction.amount).label("total")
    ).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.type == "credit",
        models.Transaction.timestamp >= last_7_days
    ).group_by(
        func.date(models.Transaction.timestamp)
    ).all()

    data = []

    for r in results:
        data.append({
            "date": str(r.date),
            "amount": r.total
        })

    return data



@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "name": user.full_name,
        "title": f"{user.role.capitalize()} Developer",
        "skills": "React, FastAPI"   # abhi dummy, baad me db me add karenge
    }


from sqlalchemy.orm import aliased
from models import User, Task

@app.get("/client-active-tasks/{user_id}")
def get_client_active_tasks(user_id: int, db: Session = Depends(get_db)):

    Freelancer = aliased(User)
    Client = aliased(User)

    tasks = db.query(
        Task,
        Freelancer.full_name.label("freelancer_name"),
        Client.full_name.label("client_name")
    ).join(
        Freelancer, Task.freelancer_id == Freelancer.id
    ).join(
        Client, Task.client_id == Client.id
    ).filter(
        Task.client_id == user_id,
        Task.status == "active"
    ).all()

    result = []

    for task, freelancer_name, client_name in tasks:
        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "price": task.price,
            "client_name": client_name,
            "freelancer_name": freelancer_name
        })

    return result


@app.get("/freelancer-active-tasks/{user_id}")
def get_freelancer_active_tasks(user_id: int, db: Session = Depends(get_db)):

    Freelancer = aliased(User)
    Client = aliased(User)

    tasks = db.query(
        Task,
        Freelancer.full_name.label("freelancer_name"),
        Client.full_name.label("client_name")
    ).join(
        Freelancer, Task.freelancer_id == Freelancer.id
    ).join(
        Client, Task.client_id == Client.id
    ).filter(
        Task.freelancer_id == user_id,
        Task.status == "active"
    ).all()

    result = []

    for task, freelancer_name, client_name in tasks:
        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "price": task.price,
            "client_name": client_name,
            "freelancer_name": freelancer_name
        })

    return result