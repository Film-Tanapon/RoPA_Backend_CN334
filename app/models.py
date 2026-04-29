from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    fullname = Column(String)
    tel = Column(String)
    role = Column(String)
    departments = Column(String)
    status = Column(String)
    create_date = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class RoPARecord(Base):
    __tablename__ = "ropa_record"

    id = Column(Integer, primary_key=True, index=True)
    activity_name = Column(String)
    purpose = Column(String)
    data_owner = Column(String)
    data_subject = Column(String)
    data_category = Column(String)
    is_sensitive = Column(Boolean)
    personal_info = Column(String)
    collection_method = Column(String)
    source = Column(String)
    legal_basis = Column(String)
    is_under_10 = Column(Boolean)
    is_age_10_20 = Column(Boolean)
    is_international = Column(Boolean)
    storage_format = Column(String)
    retention_method = Column(String)
    retention_start = Column(String)
    retention_period = Column(String)
    retention_until = Column(DateTime(timezone=True))
    access_control = Column(String)
    disposal_method = Column(String)
    consent_exempt_basis = Column(String)
    right_rejection_reason = Column(String)
    risk_level = Column(String)
    status = Column(String)
    create_date = Column(DateTime(timezone=True), server_default=func.now())
    create_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    ropa_id = Column(Integer, ForeignKey("ropa_record.id", ondelete="CASCADE"))
    country = Column(String)
    recipient_name = Column(String)
    transfer_method = Column(String)
    protection_std = Column(String)
    protection_measure = Column(String)

class SecurityMeasure(Base):
    __tablename__ = "security_measures"

    id = Column(Integer, primary_key=True, index=True)
    ropa_id = Column(Integer, ForeignKey("ropa_record.id", ondelete="CASCADE"))
    measure_type = Column(String)
    description = Column(String)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    record_id = Column(Integer)
    action = Column(String)
    table_name = Column(String)
    old_value = Column(JSON)
    new_value = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    ropa_id = Column(Integer, ForeignKey("ropa_record.id", ondelete="CASCADE"))
    detail = Column(String)
    create_date = Column(DateTime(timezone=True), server_default=func.now())

class Request(Base):
    __tablename__ = "request"

    id = Column(Integer, primary_key=True, index=True)
    ropa_id = Column(Integer, ForeignKey("ropa_record.id", ondelete="CASCADE"))
    req_type = Column(String)
    detail = Column(String, nullable=True)
    status= Column(String)
    create_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    create_date = Column(DateTime(timezone=True), server_default=func.now())