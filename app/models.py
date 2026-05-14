from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        Index(
            "uq_dept_parent_name_nn",
            "parent_id",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
        ),
        Index(
            "uq_dept_root_name",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
        foreign_keys="[Department.parent_id]",
    )
    children: Mapped[list[Department]] = relationship(
        "Department",
        back_populates="parent",
        foreign_keys="[Department.parent_id]",
        passive_deletes=True,
    )
    employees: Mapped[list[Employee]] = relationship(
        "Employee",
        back_populates="department",
        passive_deletes=True,
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    hired_at: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    department: Mapped[Department] = relationship("Department", back_populates="employees")
