class User:
    def __init__(self, id, first_name, surname, role, department, salary):
        self.id = id
        self.first_name = first_name
        self.surname = surname
        self.role = role
        self.department = department
        self.salary = salary


users = {
    1: User(id=1, first_name="adam", surname="kowalski", role="admin", department="IT", salary=12000),
    2: User(id=2, first_name="anna", surname="nowak", role="manager", department="HR", salary=10000),
    3: User(id=3, first_name="jan", surname="lewandowski", role="worker", department="Production", salary=6000)
}
