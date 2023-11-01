from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from .database import engine, init_db
from .models import User
from .auth import get_password_hash, create_access_token, get_current_user
from datetime import timedelta

app = FastAPI()

init_db()

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

def authenticate_user(username: str, password: str):
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        result = session.exec(statement)
        user = result.first()
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user
