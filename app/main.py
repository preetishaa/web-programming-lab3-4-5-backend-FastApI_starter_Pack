from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal
from app import models, auth
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="FastAPI Auth Example")

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TodoRequest(BaseModel):
    title: str
    description: str

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=data.name,
        email=data.email,
        password=auth.hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return JSONResponse(
        status_code=201,
        content={"message": "User registered successfully"}
    )

@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not auth.verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_data = {"sub": str(user.id), "email": user.email}
    token = auth.create_access_token(token_data)

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

@app.post("/todos/{user_id}", status_code=201)
def create_todo(user_id: int, data: TodoRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    todo = models.Todo(
        title=data.title,
        description=data.description,
        user_id=user_id
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return {"message": "Todo created successfully", "todo": {"id": todo.id, "title": todo.title, "description": todo.description}}

@app.get("/todos/{user_id}")
def get_todos(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    todos = db.query(models.Todo).filter(models.Todo.user_id == user_id).all()
    return {"todos": [{"id": t.id, "title": t.title, "description": t.description} for t in todos]}