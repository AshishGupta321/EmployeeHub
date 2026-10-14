
import logging
import os
from pathlib import Path
from typing import Optional

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from chatbot_service import answer_question


# --------------------------------------------------
# Configuration
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="EmployeeHub API", version="2.0.0")

app.mount(
    "/static",
    StaticFiles(directory=BASE / "static"),
    name="static",
)


# --------------------------------------------------
# Database
# --------------------------------------------------

def db():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is missing. Configure it in .env locally "
            "or in Vercel Environment Variables."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age INTEGER NOT NULL CHECK (age BETWEEN 16 AND 100),
                salary DOUBLE PRECISION NOT NULL CHECK (salary >= 0),
                desig VARCHAR(100) NOT NULL
            )
        """)


@app.on_event("startup")
def startup():
    init_db()


def as_employee(row):
    if not row:
        return None

    employee = dict(row)
    employee["designation"] = employee.get(
        "desig", employee.get("designation", "")
    )
    employee["desig"] = employee.get(
        "desig", employee.get("designation", "")
    )
    return employee


# --------------------------------------------------
# Request models
# --------------------------------------------------

class EmployeeIn(BaseModel):
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=16, le=100)
    salary: float = Field(ge=0)
    desig: str = Field(min_length=1, max_length=100)


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=16, le=100)
    salary: Optional[float] = Field(None, ge=0)
    desig: Optional[str] = Field(None, min_length=1, max_length=100)


class ChatRequest(BaseModel):
    message: str


# --------------------------------------------------
# Frontend
# --------------------------------------------------

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE / "templates" / "index.html")


# --------------------------------------------------
# READ: List employees
# --------------------------------------------------

@app.get("/employees")
def list_employees(
    search: Optional[str] = None,
    designation: Optional[str] = None,
    min_salary: Optional[float] = Query(None, ge=0),
    max_salary: Optional[float] = Query(None, ge=0),
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    sort: str = "id",
):
    sort_map = {
        "id": "id",
        "name": "LOWER(name)",
        "age": "age",
        "salary": "salary",
        "designation": "LOWER(desig)",
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
                CAST(id AS TEXT) ILIKE %s
                OR name ILIKE %s
            )
        """
        args.extend([term, term])

    if designation:
        sql += " AND desig = %s"
        args.append(designation)

    if min_salary is not None:
        sql += " AND salary >= %s"
        args.append(min_salary)

    if max_salary is not None:
        sql += " AND salary <= %s"
        args.append(max_salary)

    if min_age is not None:
        sql += " AND age >= %s"
        args.append(min_age)

    if max_age is not None:
        sql += " AND age <= %s"
        args.append(max_age)

    sql += f" ORDER BY {sort_map[key]} {direction}"

    with db() as con:
        rows = con.execute(sql, args).fetchall()

    return [as_employee(row) for row in rows]


# --------------------------------------------------
# CREATE: Add employee
# --------------------------------------------------

@app.post("/employees", status_code=201)
def add_employee(employee: EmployeeIn):
    with db() as con:
        exists = con.execute(
            "SELECT id FROM employees WHERE id = %s",
            (employee.id,),
        ).fetchone()

        if exists:
            raise HTTPException(
                status_code=409,
                detail="Employee ID already exists",
            )

        con.execute("""
            INSERT INTO employees (id, name, age, salary, desig)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            employee.id,
            employee.name.strip(),
            employee.age,
            employee.salary,
            employee.desig.strip(),
        ))

        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = %s
        """, (employee.id,)).fetchone()

    return {
        "message": "Employee added successfully",
        "employee": as_employee(row),
    }


# --------------------------------------------------
# Dashboard statistics
# --------------------------------------------------

@app.get("/employees/stats/count")
def stats_count():
    with db() as con:
        row = con.execute(
            "SELECT COUNT(*) AS count FROM employees"
        ).fetchone()

    return {"count": row["count"]}


@app.get("/employees/stats/average-salary")
def stats_average():
    with db() as con:
        row = con.execute(
            "SELECT AVG(salary) AS average FROM employees"
        ).fetchone()

    return {"average_salary": round(row["average"] or 0, 2)}


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
        "lowest": as_employee(lowest),
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


# --------------------------------------------------
# READ: Get one employee
# --------------------------------------------------

@app.get("/employees/{employee_id}")
def get_employee(employee_id: int):
    with db() as con:
        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = %s
        """, (employee_id,)).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return as_employee(row)


# --------------------------------------------------
# UPDATE: Employee details
# --------------------------------------------------

@app.put("/employees/{employee_id}")
def update_employee(employee_id: int, employee: EmployeeUpdate):
    changes = employee.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update",
        )

    for key in ("name", "desig"):
        if key in changes and changes[key] is not None:
            changes[key] = changes[key].strip()

    allowed = {"name", "age", "salary", "desig"}
    changes = {
        key: value
        for key, value in changes.items()
        if key in allowed
    }

    with db() as con:
        exists = con.execute(
            "SELECT id FROM employees WHERE id = %s",
            (employee_id,),
        ).fetchone()

        if not exists:
            raise HTTPException(
                status_code=404,
                detail="Employee not found",
            )

        assignments = ", ".join(
            f"{key} = %s" for key in changes
        )

        con.execute(
            f"UPDATE employees SET {assignments} WHERE id = %s",
            [*changes.values(), employee_id],
        )

        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = %s
        """, (employee_id,)).fetchone()

    return {
        "message": "Employee updated successfully",
        "employee": as_employee(row),
    }


# --------------------------------------------------
# Increase salary
# --------------------------------------------------

@app.post("/employees/{employee_id}/increase-salary")
def increase_salary(
    employee_id: int,
    amount: float = Query(gt=0),
):
    with db() as con:
        exists = con.execute(
            "SELECT id FROM employees WHERE id = %s",
            (employee_id,),
        ).fetchone()

        if not exists:
            raise HTTPException(
                status_code=404,
                detail="Employee not found",
            )

        con.execute("""
            UPDATE employees
            SET salary = salary + %s
            WHERE id = %s
        """, (amount, employee_id))

        row = con.execute("""
            SELECT id, name, age, salary, desig
            FROM employees
            WHERE id = %s
        """, (employee_id,)).fetchone()

    return {
        "message": "Salary increased successfully",
        "employee": as_employee(row),
    }


# --------------------------------------------------
# DELETE: One employee
# --------------------------------------------------

@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int):
    with db() as con:
        cursor = con.execute(
            "DELETE FROM employees WHERE id = %s",
            (employee_id,),
        )
        deleted = cursor.rowcount

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return {"message": "Employee deleted successfully"}


# --------------------------------------------------
# DELETE: All employees
# --------------------------------------------------

@app.delete("/employees")
def delete_all_employees():
    with db() as con:
        cursor = con.execute("DELETE FROM employees")
        deleted = cursor.rowcount

    return {
        "message": "All employee records deleted",
        "deleted_count": deleted,
    }


# --------------------------------------------------
# AI Chatbot
# --------------------------------------------------

@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()

    if not message:
        return {
            "answer": "Please enter a question.",
            "sources": [],
        }

    if len(message) > 2000:
        return {
            "answer": "Please keep your question under 2000 characters.",
            "sources": [],
        }

    try:
        logger.info(
            "Chatbot request received (message_length=%s)",
            len(message),
        )

        result = answer_question(message)

        logger.info("Chatbot request completed successfully")
        return result

    except Exception:
        # Full traceback goes to the server terminal.
        # Never expose API keys or database credentials to the browser.
        logger.exception("EmployeeHub chatbot request failed")

        raise HTTPException(
            status_code=500,
            detail="The chatbot is temporarily unavailable. Please try again.",
        )
