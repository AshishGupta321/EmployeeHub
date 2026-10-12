# app.py

from pathlib import Path
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "EmployeeDB.db"

app = FastAPI(title="EmployeeHub API", version="2.0.0")

app.mount(
    "/static",
    StaticFiles(directory=BASE / "static"),
    name="static"
)


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                salary REAL NOT NULL,
                desig TEXT NOT NULL
            )
        """)

        # Support databases using "designation" instead of "desig".
        cols = {
            row["name"]
            for row in con.execute("PRAGMA table_info(employees)")
        }

        if "desig" not in cols and "designation" in cols:
            con.execute("ALTER TABLE employees ADD COLUMN desig TEXT")
            con.execute("""
                UPDATE employees
                SET desig = designation
                WHERE desig IS NULL
            """)

        con.commit()


@app.on_event("startup")
def startup():
    init_db()


def as_employee(row):
    if not row:
        return None

    employee = dict(row)

    # Support both field names for frontend compatibility.
    employee["designation"] = employee.get(
        "desig", employee.get("designation", "")
    )
    employee["desig"] = employee.get(
        "desig", employee.get("designation", "")
    )

    return employee


class EmployeeIn(BaseModel):
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=16, le=100)
    salary: float = Field(ge=0)
    desig: str = Field(min_length=1, max_length=100)


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100
    )
    age: Optional[int] = Field(None, ge=16, le=100)
    salary: Optional[float] = Field(None, ge=0)
    desig: Optional[str] = Field(
        None, min_length=1, max_length=100
    )


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE / "templates" / "index.html")


# READ: List employees with optional filtering and sorting.
@app.get("/employees")
def list_employees(
    search: Optional[str] = None,
    designation: Optional[str] = None,
    min_salary: Optional[float] = Query(None, ge=0),
    max_salary: Optional[float] = Query(None, ge=0),
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    sort: str = "id"
):
    sort_map = {
        "id": "id",
        "name": "name COLLATE NOCASE",
        "age": "age",
        "salary": "salary",
        "designation": "desig COLLATE NOCASE"
    }

    key = sort.lstrip("-")
    if key not in sort_map:
        key = "id"

    direction = "DESC" if sort.startswith("-") else "ASC"

    sql = """
        SELECT id, name, age, salary, desig
        FROM employees
        WHERE 1=1
    """
    args = []

    if search:
        term = f"%{search.strip()}%"
        sql += """
            AND (
                CAST(id AS TEXT) LIKE ?
                OR name LIKE ?
            )
        """
        args.extend([term, term])

    if designation:
        sql += " AND desig = ?"
        args.append(designation)

    if min_salary is not None:
        sql += " AND salary >= ?"
        args.append(min_salary)

    if max_salary is not None:
        sql += " AND salary <= ?"
        args.append(max_salary)

    if min_age is not None:
        sql += " AND age >= ?"
        args.append(min_age)

    if max_age is not None:
        sql += " AND age <= ?"
        args.append(max_age)

    sql += f" ORDER BY {sort_map[key]} {direction}"

    with db() as con:
        rows = con.execute(sql, args).fetchall()

    return [as_employee(row) for row in rows]


# CREATE: Add an employee.
@app.post("/employees", status_code=201)
def add_employee(employee: EmployeeIn):
    with db() as con:
        exists = con.execute(
            "SELECT id FROM employees WHERE id = ?",
            (employee.id,)
        ).fetchone()

        if exists:
            raise HTTPException(
                status_code=409,
                detail="Employee ID already exists"
            )

        con.execute("""
            INSERT INTO employees
                (id, name, age, salary, desig)
            VALUES (?, ?, ?, ?, ?)
        """, (
            employee.id,
            employee.name.strip(),
            employee.age,
            employee.salary,
            employee.desig.strip()
        ))

        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = ?
        """, (employee.id,)).fetchone()

        con.commit()

    return {
        "message": "Employee added successfully",
        "employee": as_employee(row)
    }


# Dashboard statistics: define these before /employees/{employee_id}.
@app.get("/employees/stats/count")
def stats_count():
    with db() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0]

    return {"count": count}


@app.get("/employees/stats/average-salary")
def stats_average():
    with db() as con:
        average = con.execute(
            "SELECT AVG(salary) FROM employees"
        ).fetchone()[0]

    return {"average_salary": round(average or 0, 2)}


@app.get("/employees/stats/salary-extremes")
def stats_extremes():
    with db() as con:
        highest = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            ORDER BY salary DESC
            LIMIT 1
        """).fetchone()

        lowest = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            ORDER BY salary ASC
            LIMIT 1
        """).fetchone()

    return {
        "highest": as_employee(highest),
        "lowest": as_employee(lowest)
    }


@app.get("/employees/stats/designations")
def stats_designations():
    with db() as con:
        rows = con.execute("""
            SELECT desig, COUNT(*) AS count
            FROM employees
            GROUP BY desig
            ORDER BY count DESC
        """).fetchall()

    return [
        {"designation": row["desig"], "count": row["count"]}
        for row in rows
    ]


# READ: Get one employee.
@app.get("/employees/{employee_id}")
def get_employee(employee_id: int):
    with db() as con:
        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = ?
        """, (employee_id,)).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return as_employee(row)


# UPDATE: Edit employee details.
@app.put("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    employee: EmployeeUpdate
):
    changes = employee.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update"
        )

    for key in ("name", "desig"):
        if key in changes and changes[key] is not None:
            changes[key] = changes[key].strip()

    with db() as con:
        exists = con.execute(
            "SELECT id FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()

        if not exists:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        assignments = ", ".join(
            f"{key} = ?" for key in changes
        )

        con.execute(
            f"UPDATE employees SET {assignments} WHERE id = ?",
            [*changes.values(), employee_id]
        )

        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = ?
        """, (employee_id,)).fetchone()

        con.commit()

    return {
        "message": "Employee updated successfully",
        "employee": as_employee(row)
    }


# Increase an employee's salary.
@app.post("/employees/{employee_id}/increase-salary")
def increase_salary(
    employee_id: int,
    amount: float = Query(gt=0)
):
    with db() as con:
        exists = con.execute(
            "SELECT id FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()

        if not exists:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        con.execute("""
            UPDATE employees
            SET salary = salary + ?
            WHERE id = ?
        """, (amount, employee_id))

        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = ?
        """, (employee_id,)).fetchone()

        con.commit()

    return {
        "message": "Salary increased successfully",
        "employee": as_employee(row)
    }


# DELETE: One employee.
@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int):
    with db() as con:
        cursor = con.execute(
            "DELETE FROM employees WHERE id = ?",
            (employee_id,)
        )
        con.commit()

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return {"message": "Employee deleted successfully"}


# DELETE: All employees.
@app.delete("/employees")
def delete_all_employees():
    with db() as con:
        cursor = con.execute("DELETE FROM employees")
        deleted = cursor.rowcount
        con.commit()

    return {
        "message": "All employee records deleted",
        "deleted_count": deleted
    }