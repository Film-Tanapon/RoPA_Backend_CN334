from sqlalchemy.orm import Session
from app import models, schemas
from app.security import get_password_hash
from app.database import SessionLocal
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

def parse_retention_until(retention_start: str, retention_period: str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            start_date = datetime.strptime(retention_start.strip(), fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"ไม่สามารถอ่านรูปแบบวันที่ได้: '{retention_start}'")

    # Parse retention_period: จับตัวเลขและหน่วย (เดือน / ปี)
    match = re.match(r"(\d+)\s*(เดือน|ปี)", retention_period.strip())
    if not match:
        raise ValueError(
            f"รูปแบบ retention_period ไม่ถูกต้อง: '{retention_period}' (ตัวอย่าง: '6 เดือน', '5 ปี')"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "เดือน":
        retention_until = start_date + relativedelta(months=amount)
    else:
        retention_until = start_date + relativedelta(years=amount)

    return retention_until

def extend_retention_period(db: Session, record_id: int, extend_period: str):
    """
    ขยาย retention_until และ retention_period ของ RoPARecord
    โดยไม่สร้าง record ใหม่ใน database
    
    extend_period: เช่น "6 เดือน", "1 ปี"
    """
    db_ropa = get_ropa_record_by_id(db, record_id)
    if not db_ropa:
        return None

    # Parse extend_period
    match = re.match(r"(\d+)\s*(เดือน|ปี)", extend_period.strip())
    if not match:
        raise ValueError(
            f"รูปแบบ extend_period ไม่ถูกต้อง: '{extend_period}' (ตัวอย่าง: '6 เดือน', '1 ปี')"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    # คำนวณ retention_until ใหม่จากค่าเดิม
    current_until = db_ropa.retention_until
    if current_until is None:
        raise ValueError(f"Record {record_id} ไม่มี retention_until กำหนดไว้")

    if unit == "เดือน":
        new_until = current_until + relativedelta(months=amount)
    else:
        new_until = current_until + relativedelta(years=amount)

    # คำนวณ retention_period รวมใหม่ (นับจาก retention_start ถึง new_until)
    try:
        start_date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                start_date = datetime.strptime(db_ropa.retention_start.strip(), fmt)
                break
            except ValueError:
                continue
        
        if start_date is None:
            raise ValueError(f"ไม่สามารถอ่าน retention_start: '{db_ropa.retention_start}'")

        # Strip timezone info เพื่อให้ compare กับ naive datetime ได้
        new_until_naive = new_until.replace(tzinfo=None) if new_until.tzinfo else new_until
        delta = relativedelta(new_until_naive, start_date)
        total_months = delta.years * 12 + delta.months

        if total_months % 12 == 0:
            new_period_str = f"{total_months // 12} ปี"
        else:
            new_period_str = f"{total_months} เดือน"

    except Exception as e:
        raise ValueError(f"คำนวณ retention_period ใหม่ไม่ได้: {e}")

    # อัปเดตเฉพาะ 2 field
    db_ropa.retention_until = new_until
    db_ropa.retention_period = new_period_str

    db.commit()
    db.refresh(db_ropa)
    return db_ropa

#========================================================Users===========================================================#
def create_user(db: Session, user: schemas.User):
    password = get_password_hash(user.password_hash)

    db_user = models.User(
    username = user.username,
    email=user.email,
    password_hash = password,
    fullname=user.fullname,
    tel=user.tel,
    role=user.role,
    departments=user.departments,
    status=user.status
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate): 
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True) 
    
    if "password_hash" in update_data:
        hashed_pw = get_password_hash(update_data.pop("password_hash"))
        update_data["password_hash"] = hashed_pw

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

def update_last_active(db: Session, user_id: int):
    from datetime import datetime, timezone
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db_user.last_active = datetime.now(timezone.utc)
        db.commit()

def delete_user(db: Session, user_id: int):
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

#========================================================RoPA Record===========================================================#

def create_ropa_record(db: Session, ropa: schemas.RoPARecord, user_id: int):
    record_dict = ropa.dict()
    
    try:
        retention_until = parse_retention_until(
            record_dict["retention_start"],
            record_dict["retention_period"]
        )
    except ValueError as e:
        raise ValueError(str(e))

    db_ropa = models.RoPARecord(
        **record_dict,
        retention_until=retention_until,
        create_by=user_id
    )

    db.add(db_ropa)
    db.commit()
    db.refresh(db_ropa)
    return db_ropa

def get_ropa_records(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.RoPARecord).offset(skip).limit(limit).all()

def get_ropa_record_by_id(db: Session, record_id: int):
    return db.query(models.RoPARecord).filter(models.RoPARecord.id == record_id).first()

def get_ropa_records_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.RoPARecord).filter(models.RoPARecord.create_by == user_id).offset(skip).limit(limit).all()

def update_ropa_record(db: Session, record_id: int, ropa_update: schemas.RoPARecordUpdate):
    db_ropa = get_ropa_record_by_id(db, record_id)
    if not db_ropa:
        return None

    update_data = ropa_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ropa, key, value)

    db.commit()
    db.refresh(db_ropa)
    return db_ropa

def delete_ropa_record(db: Session, record_id: int):
    db_ropa = get_ropa_record_by_id(db, record_id)
    if not db_ropa:
        return None
    
    ropa_dict = {col.name: getattr(db_ropa, col.name) 
                 for col in db_ropa.__table__.columns}
    
    db.query(models.Transfer).filter(models.Transfer.ropa_id == record_id).delete()
    db.query(models.SecurityMeasure).filter(models.SecurityMeasure.ropa_id == record_id).delete()
    db.query(models.Feedback).filter(models.Feedback.ropa_id == record_id).delete()

    db.delete(db_ropa)
    db.commit()

    return ropa_dict

#========================================================Transfers===========================================================#

def get_transfer_by_id(db: Session, transfer_id: int):
    return db.query(models.Transfer).filter(models.Transfer.id == transfer_id).first()

def get_transfer_by_ropa_id(db: Session, ropa_id: int):
    return db.query(models.Transfer).filter(models.Transfer.ropa_id == ropa_id).first()

def create_transfer(db: Session, transfer: schemas.Transfer):
    db_tranfer = models.Transfer(**transfer.dict())
    db.add(db_tranfer)
    db.commit()
    db.refresh(db_tranfer)
    return db_tranfer

def update_transfer(db: Session, transfer_id: int, transfer_update: schemas.TransferUpdate):
    db_transfer = get_transfer_by_id(db, transfer_id)
    if not db_transfer:
        return None

    update_data = transfer_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_transfer, key, value)

    db.commit()
    db.refresh(db_transfer)
    return db_transfer

def delete_transfer(db: Session, transfer_id: int):
    db_transfer = get_transfer_by_id(db, transfer_id)
    if db_transfer:
        db.delete(db_transfer)
        db.commit()
    return db_transfer

#========================================================Security Measure===========================================================#

def get_security_by_id(db: Session, security_id: int):
    return db.query(models.SecurityMeasure).filter(models.SecurityMeasure.id == security_id).first()

def get_security_by_ropa_id(db: Session, ropa_id: int):
    return db.query(models.SecurityMeasure).filter(models.SecurityMeasure.ropa_id == ropa_id).all()

def create_security(db: Session, security: schemas.SecurityMeasure):
    db_security = models.SecurityMeasure(**security.dict())
    db.add(db_security)
    db.commit()
    db.refresh(db_security)
    return db_security

def update_security(db: Session, security_id: int, security_update: schemas.SecurityMeasureUpdate):
    db_security = get_security_by_id(db, security_id)
    if not db_security:
        return None

    update_data = security_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_security, key, value)

    db.commit()
    db.refresh(db_security)
    return db_security

def delete_security(db: Session, security_id: int):
    db_security = get_security_by_id(db, security_id)
    if db_security:
        db.delete(db_security)
        db.commit()
    return db_security

#========================================================Audit Log===========================================================#
def get_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AuditLog).offset(skip).limit(limit).all()

def get_logs_by_ropa_id(db: Session, ropa_id: int):
    return db.query(models.AuditLog).filter(models.AuditLog.ropa_id == ropa_id, models.AuditLog.table_name == "ropa_record").all()

def create_log(db: Session, log: schemas.AuditLog):
    db_log = models.AuditLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def log_action_background(
    user_id: int, 
    action: str, 
    table_name: str, 
    record_id: int, 
    old_model=None, 
    new_model=None
):
    db = SessionLocal()
    try:
        def model_to_dict(model):
            if not model:
                return None
            if isinstance(model, dict):
                return {
                    k: v.isoformat() if hasattr(v, 'isoformat') else v
                    for k, v in model.items()
                }
            return {
                col.name: (
                    getattr(model, col.name).isoformat() 
                    if hasattr(getattr(model, col.name), 'isoformat') 
                    else getattr(model, col.name)
                )
                for col in model.__table__.columns
            }

        old_value = model_to_dict(old_model)
        new_value = model_to_dict(new_model)

        log_data = schemas.AuditLog(
            user_id=user_id,
            record_id=record_id,
            action=action,
            table_name=table_name,
            old_value=old_value,
            new_value=new_value
        )
        
        db_log = models.AuditLog(**log_data.dict())
        db.add(db_log)
        db.commit()
    except Exception as e:
        print(f"Background Log Error: {e}")
    finally:
        db.close()

#========================================================Feedback===========================================================#

def get_feedback_by_id(db: Session, feedback_id: int):
    return db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()

def get_feedback(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Feedback).offset(skip).limit(limit).all()

def get_feedback_by_ropa_id(db: Session, ropa_id: int):
    return db.query(models.Feedback).filter(models.Feedback.ropa_id == ropa_id).all()

def create_feedback(db: Session, log: schemas.Feedback):
    db_feedback = models.Feedback(**log.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def delete_feedback(db: Session, feedback_id: int):
    db_feedback = get_feedback_by_id(db, feedback_id)
    if db_feedback:
        db.delete(db_feedback)
        db.commit()
    return db_feedback


#========================================================REQUEST===========================================================#
def get_request_by_id(db: Session, request_id: int):
    return db.query(models.Request).filter(models.Request.id == request_id).first()

def get_request(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Request).offset(skip).limit(limit).all()

def create_request(db: Session, request: schemas.Request, user_id: int):
    request_dict = request.dict()
    db_request = models.Request(
        **request_dict,
        create_by=user_id,
    )

    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    return db_request

def update_request(db: Session, request_id: int, request_update: schemas.RequestUpdate):
    db_request = get_request_by_id(db, request_id)
    if not db_request:
        return None

    update_data = request_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_request, key, value)

    db.commit()
    db.refresh(db_request)
    return db_request

def delete(db: Session, request_id: int):
    db_request = get_request_by_id(db, request_id)
    if db_request:
        db.delete(db_request)
        db.commit()
    return db_request