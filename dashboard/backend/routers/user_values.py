"""
User-Defined Values API endpoints.

Provides endpoints for managing custom dropdown values that users add
when tagging questions. These values are persisted and made available
in dropdowns for future questions.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from pydantic import BaseModel

from ..services.database import get_database

router = APIRouter(prefix="/user-values", tags=["user-values"])


class UserDefinedValue(BaseModel):
    field_name: str
    value: str


class UserDefinedValueCreate(BaseModel):
    field_name: str
    value: str
    created_by: Optional[str] = None


class UserDefinedValuesBatch(BaseModel):
    values: List[UserDefinedValue]
    created_by: Optional[str] = None


class UserDefinedValuesResponse(BaseModel):
    values: Dict[str, List[str]]


# ============== Get Values ==============

@router.get("/", response_model=UserDefinedValuesResponse)
async def get_all_user_defined_values():
    """
    Get all user-defined values grouped by field name.

    Returns a dict where keys are field names and values are lists of
    custom values that users have added.

    Example response:
    {
        "values": {
            "treatment_1": ["Teclistamab", "Elranatamab"],
            "drug_class_1": ["T-cell engager", "Gamma secretase inhibitor"]
        }
    }
    """
    db = get_database()
    values = db.get_all_user_defined_values()
    return UserDefinedValuesResponse(values=values)


@router.get("/{field_name}", response_model=List[str])
async def get_user_defined_values_for_field(field_name: str):
    """
    Get user-defined values for a specific field.

    Args:
        field_name: The tag field name (e.g., 'treatment_1', 'drug_class_1')

    Returns:
        List of user-defined values for this field
    """
    db = get_database()
    values = db.get_user_defined_values(field_name)
    return values


# ============== Add Values ==============

@router.post("/")
async def add_user_defined_value(value: UserDefinedValueCreate):
    """
    Add a single user-defined value for a field.

    This is called automatically when a user saves a tag with a custom value
    that isn't in the static canonical list.

    Returns:
        success: True if the value was added, False if it already exists
    """
    if not value.value or not value.value.strip():
        raise HTTPException(status_code=400, detail="Value cannot be empty")

    db = get_database()
    added = db.add_user_defined_value(
        field_name=value.field_name,
        value=value.value.strip(),
        created_by=value.created_by
    )

    return {
        "success": added,
        "message": f"Value '{value.value}' {'added' if added else 'already exists'} for field '{value.field_name}'"
    }


@router.post("/batch")
async def add_user_defined_values_batch(request: UserDefinedValuesBatch):
    """
    Add multiple user-defined values at once.

    This is useful when saving multiple custom values from a single
    tag edit operation.

    Returns:
        added_count: Number of new values added
    """
    db = get_database()
    values_data = [{"field_name": v.field_name, "value": v.value} for v in request.values]
    added_count = db.add_user_defined_values_batch(values_data, created_by=request.created_by)

    return {
        "success": True,
        "added_count": added_count,
        "total_submitted": len(request.values)
    }


# ============== Delete Values ==============

@router.delete("/{field_name}/{value}")
async def delete_user_defined_value(field_name: str, value: str):
    """
    Delete a user-defined value.

    This is an admin operation to remove a value that was added in error.
    """
    db = get_database()
    deleted = db.delete_user_defined_value(field_name, value)

    if not deleted:
        raise HTTPException(status_code=404, detail="Value not found")

    return {
        "success": True,
        "message": f"Value '{value}' deleted from field '{field_name}'"
    }
