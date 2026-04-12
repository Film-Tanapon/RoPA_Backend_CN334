from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError, ExpiredSignatureError 
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone


from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models, schemas, crud
from app.database import engine, SessionLocal

from app.schemas import User

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:5500", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

SECRET_KEY = "my_super_secret_key" 
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    username: str
    password: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Incorrect Token")
            
        return username
        
    except ExpiredSignatureError: # --- แก้ไขการเรียก Error ตรงนี้ ---
        raise HTTPException(status_code=401, detail="Token expired. Please re-login.")
        
    except JWTError: # --- แก้ไขการเรียก Error ตรงนี้ ---
        raise HTTPException(status_code=401, detail="Incorrect Token")

#===========================================Login=========================================================#
@app.post("/login")
async def login(user_data: LoginRequest,
                db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=user_data.username)

    if not user or not pwd_context.verify(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username or Password Incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expire = datetime.now(timezone.utc) + timedelta(minutes = 30)
    payload = {
        "sub": user_data.username,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "message": "Login Success",
        "access_token": token, 
        "token_type": "bearer"
    }

#===========================================Users=========================================================#
@app.post("/user")
async def create_user(user_data: schemas.User,
                      db: Session = Depends(get_db)):
    print(f"Recieved data: {user_data}")
    saved_data = crud.create_user(db=db, user=user_data)
    return {"status": "success", "message": "Sign-up data received", "data": saved_data}

@app.get("/users")
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return {
        "status": "success",
        "data": users
    }

@app.get("/users/me")
async def read_users_me(current_username: str = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if user is None:
        raise HTTPException(status_code=404, detail="No User data")
    
    user.last_active = func.now()

    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "status": "success",
        "data": user
    }

@app.get("/users/{user_id}")
async def read_user(user_id: int,
                    db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "status": "success",
        "data": db_user
    }

@app.put("/users/{user_id}")
async def user_update(user_id: int,
                      user_update: schemas.UserUpdate,
                      current_username: str = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_user_old = crud.get_user_by_id(db, user_id)
    if not db_user_old:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user_old = jsonable_encoder(db_user_old) if db_user_old else None
    
    update_data = crud.update_user(db,user_id, user_update)
    update_data = jsonable_encoder(update_data) if update_data else None


    crud.log_action(db, user.id, "UPDATE", "users", user_id, old_model=db_user_old, new_model=update_data)

    return {"status": "success", "message": "RoPA record data updated", "data": update_data}


@app.delete("/users/{user_id}")
async def delete_user(user_id: int,
                      current_username: str = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    db_user = crud.delete_user(db, user_id)
    db_user = jsonable_encoder(db_user) if db_user else None

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    crud.log_action(db, user.id, "DELETE", "users", user_id, old_model=db_user)
    
    return {
        "status": "success",
        "data": db_user
    }

#===========================================RoPA Record=========================================================#
@app.get("/ropa-records")
async def read_ropa_records(skip: int = 0,
                            limit: int = 100,
                            db: Session = Depends(get_db)):
    records = crud.get_ropa_records(db, skip=skip, limit=limit)
    return {
        "status": "success",
        "data": records
    }

@app.get("/ropa-records/me")
async def read_my_ropa_records(skip: int = 0,
                               limit: int = 100,
                               current_username: str = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db,username=current_username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    records = crud.get_ropa_records_by_user(db, user_id=user.id, skip=skip, limit=limit)
    
    return {
        "status": "success",
        "data": records
    }

@app.get("/ropa-records/{record_id}")
async def read_ropa_record(record_id: int,
                           db: Session = Depends(get_db)):
    record = crud.get_ropa_record_by_id(db, record_id=record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="RoPA record not found")
        
    return {
        "status": "success",
        "data": record
    }

@app.post("/ropa-records")
async def create_ropa_record(ropa_data: schemas.RoPARecord, 
                            current_username: str = Depends(get_current_user), 
                            db : Session = Depends(get_db)
                            ):
    user = crud.get_user_by_username(db, username=current_username)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    saved_data = crud.create_ropa_record(db, ropa_data)

    crud.log_action(db, user.id, "CREATE", "ropa_records", saved_data.id, new_model=saved_data)
    
    return {"status": "success", "message": "RoPA record data received", "data": saved_data}

@app.put("/ropa-records/{record_id}")
async def update_ropa_record(record_id: int, 
                            ropa_update: schemas.RoPARecordUpdate, 
                            current_username: str = Depends(get_current_user), 
                            db: Session = Depends(get_db)
                            ):

    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    db_ropa_old = crud.get_ropa_record_by_id(db, record_id)
    if not db_ropa_old:
        raise HTTPException(status_code=404, detail="RoPA record not found")

    update_data = crud.update_ropa_record(db, record_id, ropa_update)
    
    crud.log_action(db, user.id, "UPDATE", "ropa_records", record_id, old_model=db_ropa_old, new_model=update_data)

    return {"status": "success", "message": "RoPA record data updated", "data": update_data}

@app.delete("/ropa-record/{record_id}")
async def delete_ropa_record(record_id: int,
                             current_username: str = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    db_ropa = crud.delete_ropa_record(db, record_id)
    if db_ropa is None:
        raise HTTPException(status_code=404, detail="RoPA record not found")
    
    crud.log_action(db, user.id, "DELETE", "ropa_records", record_id, old_model=db_ropa)
    return {
        "status": "success",
        "data": db_ropa
    }

#===========================================Transfers=========================================================#
@app.get("/transfers/{ropa_id}")
async def read_transfer_by_ropa_id(ropa_id: int,
                                   db: Session = Depends(get_db)):
    transfer = crud.get_transfer_by_ropa_id(db, ropa_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer data not found")
        
    return {
        "status": "success",
        "data": transfer
    }

@app.post("/transfers")
async def create_transfer(transfer_data: schemas.Transfer, 
                        current_username: str = Depends(get_current_user), 
                        db : Session = Depends(get_db)
                        ):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    saved_data = crud.create_transfer(db, transfer_data)
    
    crud.log_action(db, user.id, "CREATE", "transfers", ropa_id = saved_data.ropa_id, new_model=saved_data)
    
    return {"status": "success", "message": "Transfer data received", "data": saved_data}

@app.put("/transfers/{transfer_id}")
async def update_transfer(transfer_id: int, 
                        transfer_update: schemas.TransferUpdate, 
                        current_username: str = Depends(get_current_user), 
                        db: Session = Depends(get_db)
                        ):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_transfer_old = crud.get_transfer_by_id(db, transfer_id)
    if db_transfer_old is None:
        raise HTTPException(status_code=404, detail="Transfer data not found")
    
    update_data = crud.update_transfer(db, transfer_id, transfer_update)
    
    crud.log_action(db, user.id, "UPDATE", "transfers", ropa_id = db_transfer_old.ropa_id, old_model=db_transfer_old, new_model=update_data)

    return {"status": "success", "message": "Transfer data updated", "data": update_data}

@app.delete("/transfers/{transfer_id}")
async def delete_transfer(transfer_id: int,
                        current_username: str = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_transfer = crud.delete_transfer(db, transfer_id)
    if db_transfer is None:
        raise HTTPException(status_code=404, detail="Transfer data not found")
    
    crud.log_action(db, user.id, "DELETE", "transfers", ropa_id = db_transfer.ropa_id, old_model=db_transfer)
    
    return {
        "status": "success",
        "data": db_transfer
    }

#===========================================SecurityMeasure=========================================================#

@app.get("/security/{ropa_id}")
async def read_security_by_ropa_id(ropa_id: int,
                                db: Session = Depends(get_db)):
    security = crud.get_security_by_ropa_id(db, ropa_id)
    if security is None:
        raise HTTPException(status_code=404, detail="Security Measure not found")
        
    return {
        "status": "success",
        "data": security
    }

@app.post("/security")
async def create_security(security_data: schemas.SecurityMeasure,
                          current_username: str = Depends(get_current_user),
                          db : Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    saved_data = crud.create_security(db, security_data)
    
    crud.log_action(db, user.id, "CREATE", "security_measure", ropa_id = saved_data.ropa_id, new_model=saved_data)

    return {"status": "success", "message": "Security Measure data received", "data": saved_data}

@app.put("/security/{security_id}")
async def update_security(security_id: int,
                          security_update: schemas.SecurityMeasureUpdate,
                          current_username: str = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_security_old = crud.get_security_by_id(db, security_id)
    if not db_security_old:
        raise HTTPException(status_code=404, detail="Security Measure data not found")
    
    update_data = crud.update_security(db, security_id, security_update)
    crud.log_action(db, user.id, "UPDATE", "security_measure", ropa_id = db_security_old.ropa_id, old_model=db_security_old, new_model=update_data)
    

    return {"status": "success", "message": "Security Measure data updated", "data": update_data}

@app.delete("/security/{security_id}")
async def delete_security(security_id: int,
                          current_username: str = Depends(get_current_user),
                          db: Session = Depends(get_db)):

    user = crud.get_user_by_username(db, username=current_username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    db_security = crud.delete_security(db, security_id)
    if db_security is None:
        raise HTTPException(status_code=404, detail="Security Measure data not found")
    
    crud.log_action(db, user.id, "DELETE", "security_measure", ropa_id = db_security.ropa_id, old_model=db_security)
    
    return {
        "status": "success",
        "data": db_security
    }

#===========================================AuditLogs=========================================================#
@app.get("/logs")
async def read_logs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)):
    logs = crud.get_logs(db, skip=skip, limit=limit)
    return {
        "status": "success",
        "data": logs
    }

@app.get("logs/{ropa_id}")
async def read_logs_by_ropa_id(ropa_id: int,
                               db: Session = Depends(get_db)):
    logs = crud.get_logs_by_ropa_id(db, ropa_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="Ropa record not found")
        
    return {
        "status": "success",
        "data": logs
    }

@app.post("/logs")
async def create_log(log_data: schemas.AuditLog,
                     db : Session = Depends(get_db)):
    print(f"Recieved data: {log_data}")
    saved_data = crud.create_log(db, log_data)
    return {"status": "success", "message": "log data received", "data": saved_data}

#===========================================Feedback=========================================================#

@app.get("/feedbacks/{ropa_id}")
async def read_feedback_by_ropa_id(ropa_id: int,
                               db: Session = Depends(get_db)):
    feedbacks = crud.get_feedback_by_ropa_id(db, ropa_id)
    if feedbacks is None:
        raise HTTPException(status_code=404, detail="Ropa record not found")
        
    return {
        "status": "success",
        "data": feedbacks
    }

@app.post("/feedback")
async def create_feedback(feedback_data: schemas.Feedback,
                     db : Session = Depends(get_db)):
    print(f"Recieved data: {feedback_data}")
    saved_data = crud.create_feedback(db, feedback_data)
    return {"status": "success", "message": "log data received", "data": saved_data}

@app.delete("/feedback")
async def delete_feedback(feedback_id: int,
                      db: Session = Depends(get_db)):
    db_feedback = crud.delete_user(db, feedback_id)
    if db_feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {
        "status": "success",
        "data": db_feedback
    }




