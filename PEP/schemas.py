from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    first_name: str
    surname: str
    role: str
    dept: str
    salary: int

    class Config:
        from_attributes = True