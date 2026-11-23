import os
import bcrypt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "clave_secreta_desarrollo_vichuquen_2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def crear_token_acceso(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada. Inicie sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        correo: str = payload.get("sub")
        if correo is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
    if usuario is None:
        raise cred_exc
    return usuario

def requerir_admin(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
    if usuario.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador municipal.")
    return usuario