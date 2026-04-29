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

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None  
    fullname: Optional[str] = None
    tel: Optional[str] = None
    role: Optional[str] = None
    departments: Optional[str] = None
    status: Optional[str] = None 

class RoPARecord(BaseModel):
    activity_name: str
    purpose: str
    data_owner: str
    data_subject: str
    data_category: str
    is_sensitive: bool = False
    personal_info: str
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

class RoPARecordUpdate(BaseModel):
    activity_name: Optional[str] = None
    purpose: Optional[str] = None
    data_owner: Optional[str] = None
    data_subject: Optional[str] = None
    data_category: Optional[str] = None
    is_sensitive: Optional[bool] = None
    personal_info: Optional[str] = None
    collection_method: Optional[str] = None
    source: Optional[str] = None
    legal_basis: Optional[str] = None
    is_under_10: Optional[bool] = None
    is_age_10_20: Optional[bool] = None
    is_international: Optional[bool] = None
    storage_format: Optional[str] = None
    retention_method: Optional[str] = None
    retention_start: Optional[str] = None
    retention_period: Optional[str] = None
    access_control: Optional[str] = None
    disposal_method: Optional[str] = None
    consent_exempt_basis: Optional[str] = None
    right_rejection_reason: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None

class Transfer(BaseModel):
    ropa_id: int
    country: str
    recipient_name: str
    transfer_method: str
    protection_std: str
    protection_measure: str

class TransferUpdate(BaseModel):
    country: Optional[str] = None
    recipient_name: Optional[str] = None
    transfer_method: Optional[str] = None
    protection_std: Optional[str] = None
    protection_measure: Optional[str] = None

class SecurityMeasure(BaseModel):
    ropa_id: int
    measure_type: str
    description: str

class SecurityMeasureUpdate(BaseModel):
    measure_type: Optional[str] = None
    description: Optional[str] = None

class AuditLog(BaseModel):
    user_id: int
    record_id: Optional[int] = None
    action: str
    table_name: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None

class Feedback(BaseModel):
    ropa_id: int
    detail: str

class Request(BaseModel):
    ropa_id: int
    req_type: str
    detail: str
    status: str

class RequestUpdate(BaseModel):
    ropa_id: Optional[int] = None
    req_type: Optional[str] = None
    detail: Optional[str] = None
    status: Optional[str] = None

class ExtendRetention(BaseModel):
    extend_period: str
