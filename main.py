import os

from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from app import models, schemas, crud
from app.database import engine, SessionLocal
from app.security import pwd_context

# สร้างตารางใน Database (ถ้ายังไม่มี)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="RoPA Management API")

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "https://ro-pa-frontend-cn-334.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Configuration ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 2

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schemas สำหรับ Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str

# --- Authentication Helpers ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# ===========================================================================
#                                AUTH ENDPOINTS
# ===========================================================================

@app.post("/login")
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=login_data.username)
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )

    crud.update_last_active(db, user.id)
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# ===========================================================================
#                                USER ENDPOINTS
# ===========================================================================

@app.post("/users", response_model=schemas.User)
async def create_user(user: schemas.User, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@app.get("/users")
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.put("/users/{user_id}")
async def update_user(
    user_id: int, 
    user_update: schemas.UserUpdate, 
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin = crud.get_user_by_username(db, current_username)
    db_user = crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    old_data = {column.name: getattr(db_user, column.name) for column in db_user.__table__.columns}
    updated_user = crud.update_user(db, user_id, user_update)
    
    # บันทึก Log แบบ Background Task
    background_tasks.add_task(
        crud.log_action_background,
        user_id=admin.id,
        action="UPDATE",
        table_name="users",
        record_id=user_id,
        old_model=old_data,
        new_model=user_update.dict(exclude_unset=True)
    )
    return updated_user

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int, 
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin = crud.get_user_by_username(db, current_username)
    db_user = crud.delete_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    background_tasks.add_task(
        crud.log_action_background,
        user_id=admin.id,
        action="DELETE",
        table_name="users",
        record_id=user_id,
        old_model=db_user
    )
    return {"status": "success", "message": "User deleted"}

# ===========================================================================
#                                ROPA ENDPOINTS
# ===========================================================================

@app.post("/ropa-records")
async def create_ropa_record(
    record: schemas.RoPARecord, 
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, current_username)
    db_ropa = crud.create_ropa_record(db, record, user.id)
    
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="CREATE",
        table_name="ropa_record",
        record_id=db_ropa.id,
        new_model=record.dict()
    )
    return db_ropa

@app.get("/ropa-records")
async def read_ropa_records(db: Session = Depends(get_db)):
    return crud.get_ropa_records(db)

@app.get("/ropa-records/{record_id}")
async def read_ropa_record(record_id: int, db: Session = Depends(get_db)):
    db_record = crud.get_ropa_record_by_id(db, record_id)
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")
    return db_record

@app.put("/ropa-records/{record_id}")
async def update_ropa_record(
    record_id: int, 
    record_update: schemas.RoPARecordUpdate, 
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, current_username)
    db_record = crud.get_ropa_record_by_id(db, record_id)
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")

    old_data = {column.name: getattr(db_record, column.name) for column in db_record.__table__.columns}
    updated_record = crud.update_ropa_record(db, record_id, record_update)
    
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="UPDATE",
        table_name="ropa_record",
        record_id=record_id,
        old_model=old_data,
        new_model=record_update.dict(exclude_unset=True)
    )
    return updated_record

@app.put("/ropa-records/{record_id}/extend-retention")
async def extend_retention(
    record_id: int,
    extend_data: schemas.ExtendRetention,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        extended_record = crud.extend_retention_period(db, record_id, extend_data.extend_period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="UPDATE",
        table_name="ropa_record",
        record_id=record_id,
        old_model={column.name: getattr(extended_record, column.name) for column in extended_record.__table__.columns},
        new_model=extended_record.dict()
    )
    return extended_record

@app.patch("/ropa-records/{record_id}/extend-retention")
async def extend_retention(
    record_id: int,
    body: schemas.ExtendRetention,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        updated = crud.extend_retention_period(db, record_id, body.extend_period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")

    return {
        "status": "success",
        "record_id": record_id,
        "retention_period": updated.retention_period,
        "retention_until": updated.retention_until
    }

@app.delete("/ropa-records/{record_id}")
async def delete_ropa_record(
    record_id: int, 
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, current_username)

    db_ropa_dict = crud.delete_ropa_record(db, record_id)
    if not db_ropa_dict:
        raise HTTPException(status_code=404, detail="Record not found")
    
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="DELETE",
        table_name="ropa_record",
        record_id=record_id,
        old_model=db_ropa_dict
    )
    return {"status": "success", "data": db_ropa_dict}

#===========================================Transfers=========================================================#
 
@app.get("/transfers/{ropa_id}")
async def read_transfer_by_ropa_id(
    ropa_id: int,
    db: Session = Depends(get_db)
):
    transfer = crud.get_transfer_by_ropa_id(db, ropa_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer data not found")
    return {"status": "success", "data": transfer}
 
@app.post("/transfers")
async def create_transfer(
    transfer_data: schemas.Transfer,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    saved_data = crud.create_transfer(db, transfer_data)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="CREATE",
        table_name="transfers",
        record_id=saved_data.ropa_id,
        new_model=saved_data
    )
    
    return {"status": "success", "message": "Transfer data received", "data": saved_data}
 
@app.put("/transfers/{transfer_id}")
async def update_transfer(
    transfer_id: int,
    transfer_update: schemas.TransferUpdate,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_transfer_old = crud.get_transfer_by_id(db, transfer_id)
    if db_transfer_old is None:
        raise HTTPException(status_code=404, detail="Transfer data not found")
 
    old_data = {column.name: getattr(db_transfer_old, column.name) for column in db_transfer_old.__table__.columns}
    update_data = crud.update_transfer(db, transfer_id, transfer_update)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="UPDATE",
        table_name="transfers",
        record_id=db_transfer_old.ropa_id,
        old_model=old_data,
        new_model=transfer_update.dict(exclude_unset=True)
    )
 
    return {"status": "success", "message": "Transfer data updated", "data": update_data}
 
@app.delete("/transfers/{transfer_id}")
async def delete_transfer(
    transfer_id: int,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
 
    db_transfer = crud.get_transfer_by_id(db, transfer_id)
    if db_transfer is None:
        raise HTTPException(status_code=404, detail="Transfer data not found")
 
    old_data = {column.name: getattr(db_transfer, column.name) for column in db_transfer.__table__.columns}
    crud.delete_transfer(db, transfer_id)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="DELETE",
        table_name="transfers",
        record_id=db_transfer.ropa_id,
        old_model=old_data
    )
    
    return {"status": "success", "data": old_data}
 
#===========================================SecurityMeasure=========================================================#
 
@app.get("/security/{ropa_id}")
async def read_security_by_ropa_id(
    ropa_id: int,
    db: Session = Depends(get_db)
):
    security = crud.get_security_by_ropa_id(db, ropa_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security Measure not found")
    return {"status": "success", "data": security}
 
@app.post("/security")
async def create_security(
    security_data: schemas.SecurityMeasure,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    saved_data = crud.create_security(db, security_data)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="CREATE",
        table_name="security_measures",
        record_id=saved_data.ropa_id,
        new_model=saved_data
    )
 
    return {"status": "success", "message": "Security Measure data received", "data": saved_data}
 
@app.put("/security/{security_id}")
async def update_security(
    security_id: int,
    security_update: schemas.SecurityMeasureUpdate,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_security_old = crud.get_security_by_id(db, security_id)
    if not db_security_old:
        raise HTTPException(status_code=404, detail="Security Measure data not found")
 
    old_data = {column.name: getattr(db_security_old, column.name) for column in db_security_old.__table__.columns}
    update_data = crud.update_security(db, security_id, security_update)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="UPDATE",
        table_name="security_measures",
        record_id=db_security_old.ropa_id,
        old_model=old_data,
        new_model=security_update.dict(exclude_unset=True)
    )
 
    return {"status": "success", "message": "Security Measure data updated", "data": update_data}
 
@app.delete("/security/{security_id}")
async def delete_security(
    security_id: int,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
 
    db_security = crud.get_security_by_id(db, security_id)
    if db_security is None:
        raise HTTPException(status_code=404, detail="Security Measure data not found")
 
    old_data = {column.name: getattr(db_security, column.name) for column in db_security.__table__.columns}
    crud.delete_security(db, security_id)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="DELETE",
        table_name="security_measures",
        record_id=db_security.ropa_id,
        old_model=old_data
    )
    
    return {"status": "success", "data": old_data}

# ===========================================================================
#                                LOGS & FEEDBACK
# ===========================================================================

@app.get("/logs/{ropa_id}")
async def read_logs_by_ropa_id(ropa_id: int, db: Session = Depends(get_db)):
    logs = crud.get_logs_by_ropa_id(db, ropa_id)
    return {"status": "success", "data": logs}

@app.get("/feedback")
async def read_feedback(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    requests = crud.get_feedback(db, skip=skip, limit=limit)
    return requests

@app.get("/feedback/{ropa_id}")
async def read_feedback_by_ropa_id(ropa_id: int, db: Session = Depends(get_db)):
    feedbacks = crud.get_feedback_by_ropa_id(db, ropa_id)
    return {"status": "success", "data": feedbacks}

@app.post("/feedback")
async def create_feedback(
    feedback_data: schemas.Feedback, 
    db: Session = Depends(get_db)
):
    saved_data = crud.create_feedback(db, feedback_data)
    return {"status": "success", "message": "Feedback created", "data": saved_data}

@app.delete("/feedback/{feedback_id}")
async def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    # แก้ไขให้เรียกฟังก์ชัน delete_feedback ที่ถูกต้อง
    db_feedback = crud.delete_feedback(db, feedback_id)
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"status": "success", "message": "Feedback deleted"}

#===========================================REQUEST=========================================================#
@app.get("/requests")
async def read_request(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    requests = crud.get_request(db, skip=skip, limit=limit)
    return requests

@app.post("/requests")
async def create_requests(
    request_data: schemas.Request,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    saved_data = crud.create_request(db, request_data, user.id)
 
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="CREATE",
        table_name="request",
        record_id=saved_data.ropa_id,
        new_model=saved_data
    )
 
    return {"status": "success", "message": "Request data received", "data": saved_data}

@app.put("/requests/{request_id}")
async def update_request(
    request_id: int,
    request_update: schemas.RequestUpdate,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_request_old = crud.get_request_by_id(db, request_id)
    if not db_request_old:
        raise HTTPException(status_code=404, detail="Request data not found")
 
    old_data = {column.name: getattr(db_request_old, column.name) for column in db_request_old.__table__.columns}
    update_data = crud.update_request(db, request_id, request_update)
 
    # [แก้ไข #1] เปลี่ยนจาก crud.log_action() → background_tasks + log_action_background()
    background_tasks.add_task(
        crud.log_action_background,
        user_id=user.id,
        action="UPDATE",
        table_name="request",
        record_id=db_request_old.ropa_id,
        old_model=old_data,
        new_model=request_update.dict(exclude_unset=True)
    )
 
    return {"status": "success", "message": "Request data updated", "data": update_data}


