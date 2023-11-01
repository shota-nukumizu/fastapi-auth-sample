## 手順

FastAPIを使用してSQLiteとSQLModelを用いたユーザ認証付きのREST APIを開発するためには、いくつかのステップを踏む必要があります。以下にそのプロセスを説明します。

1. 必要なパッケージのインストール:
   ```
   pip install fastapi uvicorn sqlmodel python-dotenv python-jose[cryptography] passlib[bcrypt]
   ```

2. データベースモデルの作成:
   `models.py`というファイルを作成し、ユーザモデルを定義します。

   `models.py`:
   ```python
   from typing import Optional
   from sqlmodel import Field, SQLModel

   class User(SQLModel, table=True):
      id: Optional[int] = Field(default=None, primary_key=True)
      email: str = Field(unique=True, index=True)
      username: str
      hashed_password: str
   ```

   ここで、`User`クラスはSQLModelを継承しており、SQLiteデータベースに保存されるテーブルの構造を定義しています。`email`フィールドにはユニーク制約を設定しています。

3. データベースとの接続:
   `database.py`というファイルを作成し、データベースとの接続を管理します。

   `database.py`:
   ```python
   from sqlmodel import create_engine, SQLModel, Session

   DATABASE_URL = "sqlite:///./test.db"
   engine = create_engine(DATABASE_URL, echo=True)

   def init_db():
       SQLModel.metadata.create_all(engine)
   ```

   ここで`init_db`関数を定義して、データベーステーブルを初期化する役割を持たせています。

4. ユーザ認証のためのユーティリティ関数の作成:
   `auth.py`というファイルを作成し、パスワードのハッシュ化やトークンの生成など、認証に関連する関数を定義します。

   `auth.py`:
   ```python
   from fastapi import status, HTTPException
   from jose import JWTError, jwt
   from datetime import datetime, timedelta
   from passlib.context import CryptContext
   from typing import Optional

   SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
   ALGORITHM = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES = 30

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def verify_password(plain_password, hashed_password):
       return pwd_context.verify(plain_password, hashed_password)

   def get_password_hash(password):
       return pwd_context.hash(password)

   def create_access_token(data: dict, expires_delta: timedelta | None = None):
       to_encode = data.copy()
       if expires_delta:
           expire = datetime.utcnow() + expires_delta
       else:
           expire = datetime.utcnow() + timedelta(minutes=15)
       to_encode.update({"exp": expire})
       encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
       return encoded_jwt

   def get_current_user(token: str) -> Optional[dict]:
       credentials_exception = HTTPException(
           status_code=status.HTTP_401_UNAUTHORIZED,
           detail="Could not validate credentials",
           headers={"WWW-Authenticate": "Bearer"},
       )
       try:
           payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
           username: str = payload.get("sub")
           if username is None:
               raise credentials_exception
           return {"username": username}
       except JWTError:
           raise credentials_exception
   ```

   ここで、パスワードのハッシュ化、トークンの生成、トークンからユーザ情報を取得するための関数を定義しています。

5. FastAPIアプリケーションの作成とエンドポイントの設定:
   `main.py`というファイルを作成し、FastAPIアプリケーションを定義します。

   `main.py`:
   ```python
   from fastapi import FastAPI, Depends, HTTPException, status
   from sqlmodel import Session, select
   from database import engine, init_db
   from models import User
   from auth import get_password_hash, create_access_token, get_current_user
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
   ```

   ここで、トークンを取得するための`/token`エンドポイントと、現在ログインしているユーザの情報を取得するための`/users/me`エンドポイントを定義しています。

これで基本的なセットアップは完了です。サーバを起動するには以下のコマンドを実行します。

```
uvicorn main:app --reload
```

上述のコマンドを実行することで、FastAPIアプリケーションが`http://127.0.0.1:8000`で実行されます。

サーバを起動した後、以下のURLにアクセスすることで、FastAPIによって自動生成された対話式のAPIドキュメントを利用できます:

```
http://127.0.0.1:8000/docs
```

このドキュメントページでは、定義したエンドポイントの詳細を確認し、リクエストを直接送信して動作をテストすることができます。また、リクエストとレスポンスのスキーマも確認することができます。

### ユーザの作成
ユーザ認証のためには、最初にユーザをデータベースに登録する必要があります。以下のようにエンドポイントを追加してユーザを作成できます:

`main.py`:
```python
from fastapi import Body

@app.post("/users/")
async def create_user(user: User, password: str = Body(...)):
    user.hashed_password = get_password_hash(password)
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user
```

このエンドポイントはユーザ情報とパスワードを受け取り、パスワードをハッシュ化してデータベースに保存します。この際、パスワード自体はデータベースに保存されません。

### アクセストークンの取得
ユーザがデータベースに存在していれば、`/token`エンドポイントを利用してJWTアクセストークンを取得できます。このトークンはその後の認証が必要なリクエストで使用されます。

### ユーザ情報の取得
ログイン後、アクセストークンを使用して`/users/me`エンドポイントから現在ログインしているユーザの情報を取得できます。リクエストヘッダに`Authorization: Bearer <トークン>`を追加してリクエストを送信します。

### サーバの実行
サーバを実行するには以下のコマンドを実行します:

```
uvicorn main:app --reload
```

これで、FastAPIアプリケーションが`http://127.0.0.1:8000`で実行されます。`--reload`オプションを指定すると、コードの変更があった場合にサーバが自動で再起動します。

これで、SQLiteとSQLModelを使用したFastAPIによるユーザ認証付きREST APIの基本的なセットアップが完了しました。アプリケーションの拡張やカスタマイズは、この基本的なフレームワークを元に行うことができます。