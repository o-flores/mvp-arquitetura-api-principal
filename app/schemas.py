from pydantic import BaseModel
from typing import List

class MessageSchema(BaseModel):
    message: str
    code: int

class ValidateDocumentSchema(BaseModel):
    document: str

class ValidationResultSchema(BaseModel):
    document: str
    valid: bool

class ValidationCacheSchema(BaseModel):
    document: str
    valid: bool
    type: str

class ValidationListSchema(BaseModel):
    validations: List[ValidationCacheSchema]

class UpdateValidationSchema(BaseModel):
    document: str
    valid: bool
    type: str

class DeleteValidationSchema(BaseModel):
    document: str