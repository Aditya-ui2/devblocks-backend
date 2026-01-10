from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Connection URL (MySQL)
# Format: mysql+pymysql://<username>:<password>@<host>/<database_name>
# Agar XAMPP use kar raha hai to password khali chhod de (root:@localhost)
SQLALCHEMY_DATABASE_URL = "sqlite:///./health.db"

# 2. Engine Create karo (Ye database se connect karta hai)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Session Maker (Ye har request ke liye ek naya 'db' session banayega)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base Class (Isse hum models.py me Tables banayenge)
Base = declarative_base()

# 5. Dependency Function (Main.py me use hoga)
# Ye function session open karta hai aur kaam hone ke baad close kar deta hai
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()