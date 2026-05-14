from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, Field, field_validator


def utc_iso_z(value: dt.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    else:
        value = value.astimezone(dt.UTC)
    text = value.isoformat(timespec="seconds")
    return re.sub(r"\+00:00$", "Z", text)


class DepartmentCreate(BaseModel):
    name: str = Field(max_length=200)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_trim(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("name must not be empty")
        if len(s) > 200:
            raise ValueError("name length must be at most 200")
        return s


class DepartmentPatch(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_trim_opt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            raise ValueError("name must not be empty")
        if len(s) > 200:
            raise ValueError("name length must be at most 200")
        return s


class DepartmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    parent_id: int | None
    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def dt_to_z(cls, v: object) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, dt.datetime):
            return utc_iso_z(v)
        raise TypeError("created_at must be datetime or str")


class EmployeeCreate(BaseModel):
    full_name: str = Field(max_length=200)
    position: str = Field(max_length=200)
    hired_at: dt.date | None = None

    @field_validator("full_name", "position")
    @classmethod
    def trim_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty")
        if len(s) > 200:
            raise ValueError("length must be at most 200")
        return s


class EmployeeRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: dt.date | None
    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def dt_to_z(cls, v: object) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, dt.datetime):
            return utc_iso_z(v)
        raise TypeError("created_at must be datetime or str")


class DepartmentNode(BaseModel):
    department: DepartmentRead
    employees: list[EmployeeRead]
    children: list["DepartmentNode"]


DepartmentNode.model_rebuild()

DepartmentDetailResponse = DepartmentNode
