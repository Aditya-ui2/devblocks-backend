from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Connection URL (MySQL)
# Format: mysql+pymysql://<username>:<password>@<host>:<port>/<database_name>
# XAMPP User: root, Password: (empty), Host: localhost, Port: 3306 (default)
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/DevBlock"

# 2. Engine Create karo
# Note: 'check_same_thread' argument hata diya gaya hai kyunki wo sirf SQLite ke liye hota hai.
# 'pool_recycle' add kiya hai taaki connection timeout na ho (MySQL specific issue)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_recycle=3600  # Har 1 ghante me connection refresh karega
)

# 3. Session Maker (Ye waisa hi rahega)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base Class (Ye bhi waisa hi rahega)
Base = declarative_base()

# 5. Dependency Function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()