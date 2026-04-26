class User:
    def __init__(self, id, first_name, surname, role, dept, salary):
        self.id = id
        self.first_name = first_name
        self.surname = surname
        self.role = role
        self.dept = dept
        self.salary = salary


users = {
    1: User(id=1, first_name="adam", surname="kowalski", role="admin", dept="IT", salary=12000),
    2: User(id=2, first_name="anna", surname="nowak", role="manager", dept="HR", salary=10000),
    3: User(id=3, first_name="jan", surname="lewandowski", role="worker", dept="Production", salary=6000),
    4: User(id=4, first_name="michal", surname="lewandowski", role="worker", dept="Production", salary=7000),
    5: User(id=4, first_name="placeholder", surname="testowy", role="Test", dept="Testowanie", salary=0),
}
