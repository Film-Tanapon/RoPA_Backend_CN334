from pydantic import BaseModel
from typing import Optional, Dict, Any

class User(BaseModel):
    username: str
    email: str
    password_hash: str
    fullname: str
    tel: str
    role: str
    departments: str
    status: str

class RoPARecord(BaseModel):
    activity_name: str
    purpose: str
    data_owner: str
    data_subject: str
    data_category: str
    is_sensitive: bool = False
    collection_method: str
    source: str
    legal_basis: str
    is_under_10: bool = False
    is_age_10_20: bool = False
    is_international: bool = False
    storage_format: str
    retention_method: str
    retention_start: str
    retention_period: str
    access_control: str
    disposal_method: str
    consent_exempt_basis: str
    right_rejection_reason: str
    risk_level: str
    status: str
    create_by: int

class Transfer(BaseModel):
    ropa_id: int
    country: str
    recipient_name: str
    transfer_method: str
    protection_std: str
    protection_measure: str

class SecurityMeasure(BaseModel):
    ropa_id: int
    measure_type: str
    description: str

class AuditLog(BaseModel):
    user_id: int
    record_id: int
    action: str
    table_name: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None

class Feedback(BaseModel):
    ropa_id: int
    detail: str
    create_by: int