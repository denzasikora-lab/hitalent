from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Department


def normalize_name(name: str) -> str:
    return name.strip()


def validate_department_name(name: str) -> None:
    if not name:
        raise ValueError("Department name must not be empty")
    if len(name) > 200:
        raise ValueError("Department name length must be at most 200")


def normalize_person_field(value: str, field: str) -> str:
    v = value.strip()
    if not v:
        raise ValueError(f"{field} must not be empty")
    if len(v) > 200:
        raise ValueError(f"{field} length must be at most 200")
    return v


def subtree_loader(levels_of_children_below: int):
    """Eager-load employees and nested children for `levels_of_children_below` levels under each node."""

    def recurse(remaining: int):
        if remaining <= 0:
            return (selectinload(Department.employees),)
        return (
            selectinload(Department.employees),
            selectinload(Department.children).options(*recurse(remaining - 1)),
        )

    return recurse(levels_of_children_below)


def load_department_for_get(db: Session, department_id: int, depth: int) -> Department | None:
    stmt = (
        select(Department)
        .where(Department.id == department_id)
        .options(*subtree_loader(depth))
    )
    return db.execute(stmt).scalar_one_or_none()


def moving_would_create_cycle(dept_id: int, new_parent_id: int, db: Session) -> bool:
    """True if new_parent_id is dept_id or any of its ancestors traces back to dept_id (move under own subtree)."""
    cur: int | None = new_parent_id
    while cur is not None:
        if cur == dept_id:
            return True
        row = db.get(Department, cur)
        if row is None:
            break
        cur = row.parent_id
    return False


def is_strict_descendant_of(node_id: int, ancestor_id: int, db: Session) -> bool:
    """True if node_id is strictly under ancestor_id in the tree."""
    row = db.get(Department, node_id)
    while row is not None and row.parent_id is not None:
        if row.parent_id == ancestor_id:
            return True
        row = db.get(Department, row.parent_id)
    return False
