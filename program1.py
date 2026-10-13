employees = []

while True:
    print("\n----- EMPLOYEE MENU -----")
    print("1. Add Employee")
    print("2. Display Employees")
    print("3. Update Employee")
    print("4. Delete Employee")
    print("5. Exit")

    choice = int(input("Enter your choice: "))

    if choice == 1:
        id = int(input("Enter the ID: "))
        name = input("Enter the name: ")
        age = int(input("Enter the age: "))
        salary = float(input("Enter the salary: "))
        desig = input("Enter the designation: ")

        employee = [id, name, age, salary, desig]
        employees.append(employee)

        print("Employee added successfully!")

    elif choice == 2:
        if len(employees) == 0:
            print("No employees found!")
        else:
            for emp in employees:
                print("\nID:", emp[0])
                print("Name:", emp[1])
                print("Age:", emp[2])
                print("Salary:", emp[3])
                print("Designation:", emp[4])

    elif choice == 3:
        eid = int(input("Enter employee ID to update: "))
        found = False

        for emp in employees:
            if emp[0] == eid:
                emp[1] = input("Enter new name: ")
                emp[2] = int(input("Enter new age: "))
                emp[3] = float(input("Enter new salary: "))
                emp[4] = input("Enter new designation: ")

                print("Employee updated successfully!")
                found = True
                break

        if not found:
            print("Employee not found!")

    elif choice == 4:
        eid = int(input("Enter employee ID to delete: "))
        found = False

        for emp in employees:
            if emp[0] == eid:
                employees.remove(emp)
                print("Employee deleted successfully!")
                found = True
                break

        if not found:
            print("Employee not found!")

    elif choice == 5:
        print("Exiting program...")
        break

    else:
        print("Invalid choice! Try again.")