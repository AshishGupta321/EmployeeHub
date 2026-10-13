
import sqlite3

# Connect to SQLite database (created automatically)
con = sqlite3.connect("EmployeeDB.db")
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    salary REAL,
    desig TEXT
)
""")
con.commit()


def display(records):
    if not records:
        print("No employees found!")
        return

    print("-" * 80)
    print(f"{'ID':<8}{'Name':<20}{'Age':<8}{'Salary':<14}{'Designation':<25}")
    print("-" * 80)

    for emp in records:
        print(f"{emp[0]:<8}{emp[1]:<20}{emp[2]:<8}"
              f"{emp[3]:<14.2f}{emp[4]:<25}")

    print("-" * 80)


while True:
    print("""
========== EMPLOYEE MANAGEMENT SYSTEM ==========
1.  Add Employee
2.  Display All Employees
3.  Update Employee
4.  Delete Employee
5.  Search Employee by ID
6.  Search Employee by Name
7.  Display Employees by Designation
8.  Display Employees by Salary Range
9.  Count Number of Employees
10. Highest and Lowest Salary Employees
11. Calculate Average Salary
12. Increase Employee Salary
13. Display Employees by Age Range
14. Delete All Employees
15. Exit
""")

    try:
        choice = int(input("Enter your choice: "))

        if choice == 1:
            eid = int(input("Enter ID: "))
            name = input("Enter name: ")
            age = int(input("Enter age: "))
            salary = float(input("Enter salary: "))
            desig = input("Enter designation: ")

            cur.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                (eid, name, age, salary, desig)
            )
            con.commit()
            print("Employee added successfully!")

        elif choice == 2:
            cur.execute("SELECT * FROM employees")
            display(cur.fetchall())

        elif choice == 3:
            eid = int(input("Enter employee ID to update: "))
            cur.execute("SELECT * FROM employees WHERE id=?", (eid,))
            emp = cur.fetchone()

            if emp:
                name = input("Enter new name: ")
                age = int(input("Enter new age: "))
                salary = float(input("Enter new salary: "))
                desig = input("Enter new designation: ")

                cur.execute("""
                    UPDATE employees
                    SET name=?, age=?, salary=?, desig=?
                    WHERE id=?
                """, (name, age, salary, desig, eid))
                con.commit()
                print("Employee updated successfully!")
            else:
                print("Employee not found!")

        elif choice == 4:
            eid = int(input("Enter employee ID to delete: "))
            cur.execute("DELETE FROM employees WHERE id=?", (eid,))
            con.commit()
            print("Employee deleted!" if cur.rowcount else "Employee not found!")

        elif choice == 5:
            eid = int(input("Enter employee ID: "))
            cur.execute("SELECT * FROM employees WHERE id=?", (eid,))
            display(cur.fetchall())

        elif choice == 6:
            name = input("Enter employee name: ")
            cur.execute(
                "SELECT * FROM employees WHERE name LIKE ?",
                ("%" + name + "%",)
            )
            display(cur.fetchall())

        elif choice == 7:
            desig = input("Enter designation: ")
            cur.execute(
                "SELECT * FROM employees WHERE desig LIKE ?",
                (desig,)
            )
            display(cur.fetchall())

        elif choice == 8:
            low = float(input("Enter minimum salary: "))
            high = float(input("Enter maximum salary: "))
            cur.execute("""
                SELECT * FROM employees
                WHERE salary BETWEEN ? AND ?
                ORDER BY salary
            """, (low, high))
            display(cur.fetchall())

        elif choice == 9:
            cur.execute("SELECT COUNT(*) FROM employees")
            print("Total employees:", cur.fetchone()[0])

        elif choice == 10:
            cur.execute("""
                SELECT * FROM employees
                WHERE salary = (SELECT MAX(salary) FROM employees)
            """)
            print("Highest salary employee(s):")
            display(cur.fetchall())

            cur.execute("""
                SELECT * FROM employees
                WHERE salary = (SELECT MIN(salary) FROM employees)
            """)
            print("Lowest salary employee(s):")
            display(cur.fetchall())

        elif choice == 11:
            cur.execute("SELECT AVG(salary) FROM employees")
            avg = cur.fetchone()[0]
            print(f"Average salary: {avg:.2f}" if avg is not None
                  else "No employees found!")

        elif choice == 12:
            eid = int(input("Enter employee ID: "))
            amount = float(input("Enter salary increase amount: "))

            if amount < 0:
                print("Increase cannot be negative!")
            else:
                cur.execute("""
                    UPDATE employees
                    SET salary = salary + ?
                    WHERE id = ?
                """, (amount, eid))
                con.commit()
                print("Salary increased!" if cur.rowcount
                      else "Employee not found!")

        elif choice == 13:
            low = int(input("Enter minimum age: "))
            high = int(input("Enter maximum age: "))
            cur.execute("""
                SELECT * FROM employees
                WHERE age BETWEEN ? AND ?
                ORDER BY age
            """, (low, high))
            display(cur.fetchall())

        elif choice == 14:
            confirm = input("Delete ALL employees? Type YES to confirm: ")
            if confirm == "YES":
                cur.execute("DELETE FROM employees")
                con.commit()
                print("All employee records deleted!")
            else:
                print("Deletion cancelled.")

        elif choice == 15:
            print("Exiting program...")
            break

        else:
            print("Invalid choice! Enter 1-15.")

    except ValueError:
        print("Invalid input! Please enter valid numbers.")

    except sqlite3.IntegrityError:
        con.rollback()
        print("Employee ID already exists!")

    except sqlite3.Error as e:
        con.rollback()
        print("Database error:", e)

cur.close()
con.close()
