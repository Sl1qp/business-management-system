from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvaluationBase(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None
    task_id: int
    user_id: int
    evaluator_id: int


class EvaluationCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None
    task_id: int
    user_id: int
    evaluator_id: int

    model_config = {
        'orm_mode': True,
    }


class EvaluationUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None


class EvaluationInDBBase(EvaluationBase):
    id: int
    created_at: datetime

    model_config = {
        'orm_mode': True,
    }


class Evaluation(EvaluationInDBBase):
    pass


class EvaluationWithDetails(EvaluationInDBBase):
    task_title: Optional[str] = None
    user_name: Optional[str] = None
    evaluator_name: Optional[str] = None

    model_config = {
        'orm_mode': True,
    }


class EvaluationStats(BaseModel):
    user_id: int
    average_rating: float
    total_evaluations: int
    period_start: datetime
    period_end: datetime


class EvaluationCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None
    task_id: int
    user_id: int

    model_config = {
        'orm_mode': True,
    }
