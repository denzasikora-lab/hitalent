from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Department, Employee
from app.schemas import (
    DepartmentCreate,
    DepartmentDetailResponse,
    DepartmentNode,
    DepartmentPatch,
    DepartmentRead,
    EmployeeCreate,
    EmployeeRead,
    utc_iso_z,
)
from app.services import department as dept_svc

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Organizational structure API", version="1.0.0")


def _dept_read(d: Department) -> DepartmentRead:
    return DepartmentRead(
        id=d.id,
        name=d.name,
        parent_id=d.parent_id,
        created_at=utc_iso_z(d.created_at),
    )


def _emp_read(e: Employee) -> EmployeeRead:
    return EmployeeRead(
        id=e.id,
        department_id=e.department_id,
        full_name=e.full_name,
        position=e.position,
        hired_at=e.hired_at,
        created_at=utc_iso_z(e.created_at),
    )


@app.post("/departments/", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentRead:
    if body.parent_id is not None:
        parent = db.get(Department, body.parent_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent department not found")
    try:
        d = Department(name=body.name, parent_id=body.parent_id)
        db.add(d)
        db.commit()
        db.refresh(d)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name must be unique within the same parent",
        )
    return _dept_read(d)


@app.post(
    "/departments/{department_id}/employees/",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    department_id: int,
    body: EmployeeCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EmployeeRead:
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    e = Employee(
        department_id=department_id,
        full_name=body.full_name,
        position=body.position,
        hired_at=body.hired_at,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _emp_read(e)


def _build_department_tree(
    root: Department,
    *,
    depth: int,
    include_employees: bool,
    current_depth: int = 0,
) -> DepartmentNode:
    employees: list[EmployeeRead] = []
    if include_employees:
        emps = sorted(
            root.employees,
            key=lambda x: (x.created_at, x.full_name),
        )
        employees = [_emp_read(x) for x in emps]

    children_out: list[DepartmentNode] = []
    if current_depth < depth:
        ch = sorted(root.children, key=lambda c: (c.name, c.id))
        for c in ch:
            children_out.append(
                _build_department_tree(
                    c,
                    depth=depth,
                    include_employees=include_employees,
                    current_depth=current_depth + 1,
                )
            )

    return DepartmentNode(
        department=_dept_read(root),
        employees=employees,
        children=children_out,
    )


@app.get("/departments/{department_id}", response_model=DepartmentDetailResponse)
def get_department(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
    include_employees: bool = True,
) -> DepartmentDetailResponse:
    root = dept_svc.load_department_for_get(db, department_id, depth)
    if root is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    tree = _build_department_tree(root, depth=depth, include_employees=include_employees)
    return tree


@app.patch("/departments/{department_id}", response_model=DepartmentRead)
def patch_department(
    department_id: int,
    body: DepartmentPatch,
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentRead:
    d = db.get(Department, department_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    updates = body.model_dump(exclude_unset=True)

    new_name = d.name
    if "name" in updates:
        new_name = updates["name"]

    new_parent_id = d.parent_id
    if "parent_id" in updates:
        new_parent_id = updates["parent_id"]

    if new_parent_id is not None:
        parent = db.get(Department, new_parent_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent department not found")

    if new_parent_id == department_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department cannot be its own parent",
        )

    if new_parent_id is not None and dept_svc.moving_would_create_cycle(department_id, new_parent_id, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot move department under its descendant (would create a cycle)",
        )

    d.name = new_name
    d.parent_id = new_parent_id

    try:
        db.commit()
        db.refresh(d)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name must be unique within the same parent",
        )
    return _dept_read(d)


@app.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_department(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    mode: Annotated[str, Query(pattern="^(cascade|reassign)$")],
    reassign_to_department_id: int | None = None,
) -> Response:
    d = db.get(Department, department_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    has_children = (
        db.scalar(
            select(Department.id).where(Department.parent_id == department_id).limit(1),
        )
        is not None
    )

    if mode == "reassign":
        if has_children:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Department has child departments. Use cascade or move children first.",
            )
        if reassign_to_department_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="reassign_to_department_id is required when mode=reassign",
            )
        if reassign_to_department_id == department_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="reassign_to_department_id cannot be the department being deleted",
            )
        target = db.get(Department, reassign_to_department_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="reassign target department not found",
            )
        if dept_svc.is_strict_descendant_of(reassign_to_department_id, department_id, db):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="reassign_to_department_id cannot be a descendant of the department being deleted",
            )
        for emp in db.scalars(select(Employee).where(Employee.department_id == department_id)):
            emp.department_id = reassign_to_department_id
        db.delete(d)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    db.delete(d)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
