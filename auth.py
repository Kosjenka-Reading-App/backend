from typing import Type

from sqlalchemy.orm import Session
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

import models, schemas, crud
import jwt
import time
import bcrypt
import os

JWT_VALID_TIME_ACCESS = 60 * 20  # 20min
JWT_VALID_TIME_REFRESH = 60 * 60 * 24 * 7  # One week
JWT_VALID_TIME_PWD_RESET = 60 * 10  # 10min
JWT_SECRET = "C0ddVvlcaL4UuChF8ckFQoVCGbtizyvK"
JWT_ALGORITHM = "HS256"

#Mail Config
conf = ConnectionConfig(
    MAIL_USERNAME = "kosjenka.readingapp@gmail.com",
    MAIL_PASSWORD = "qcjb hvps xmlf rtpm",
    MAIL_FROM = "kosjenka.readingapp@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="Kosjenka Support",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = False,
    TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), 'html_templates')
)


def createToken(
    account_id: int, account_category: str, valid_time: int, is_access_token: bool
):
    payload = {
        "account_id": account_id,
        "account_category": account_category,
        "is_access_token": is_access_token,
        "expires": time.time() + valid_time,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decodeJWT(token: str) -> Type[schemas.AuthSchema] | None:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if decoded_token["expires"] < time.time():
            return None
        ret = schemas.AuthSchema
        ret.account_id = decoded_token["account_id"]
        ret.account_category = decoded_token["account_category"]
        ret.is_access_token = decoded_token["is_access_token"]
        return ret
    except:
        return None


def get_user(db: Session, login: schemas.LoginSchema):
    user = db.query(models.Account).filter(models.Account.email == login.email).first()
    if user == None:
        return None
    if not bcrypt.checkpw(
        login.password.encode("utf-8"), user.password.encode("utf-8")
    ):
        return None
    return user


def generateToken(account: schemas.AccountOut):
    reponse = schemas.TokenSchema
    reponse.access_token = createToken(
        account_id=account.id_account,
        account_category=account.account_category,
        valid_time=JWT_VALID_TIME_ACCESS,
        is_access_token=True,
    )
    reponse.refresh_token = createToken(
        account_id=account.id_account,
        account_category=account.account_category,
        valid_time=JWT_VALID_TIME_REFRESH,
        is_access_token=False,
    )
    return reponse


def generate_refresh_token(old_token: str, decoded_token: Type[schemas.AuthSchema]):
    reponse = schemas.TokenSchema
    reponse.access_token = createToken(
        account_id=decoded_token.account_id,
        account_category=decoded_token.account_category,
        valid_time=JWT_VALID_TIME_ACCESS,
        is_access_token=True,
    )
    reponse.refresh_token = old_token
    return reponse

#Password reset
def get_account_by_email(db: Session, email: EmailStr):
    account = db.query(models.Account).filter(models.Account.email == email).first()
    return account
    
async def send_password_reset_mail(account: models.Account, base_url: str):
    token = createPasswortResetToken(email=account.email, valid_time=JWT_VALID_TIME_PWD_RESET)
    template_body = {
        "user": account.email,
        "url": f"{base_url}reset_password?token={token}",
        "expire_in_minutes": (JWT_VALID_TIME_PWD_RESET / 60)
    }    
    message = MessageSchema(
        subject="Kosjenka - Password Reset",
        recipients=[account.email],
        template_body=template_body,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message, template_name="reset_password_email.html")
         
def createPasswortResetToken(email: EmailStr, valid_time: int):
    payload = {
        "email": email,
        "expires": time.time() + valid_time,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def reset_password(db: Session, new_password: str, token: str):
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if decoded_token["expires"] < time.time():
            return "TOKEN_EXPIRED"
        account = get_account_by_email(db, decoded_token["email"])
        if account is None:
            return "EMAIL_NOT_FOUND"
        hashed_pw = crud.password_hasher(new_password)
        setattr(account, "password", hashed_pw)
        db.commit()
        db.refresh(account)
        return "SUCCESS"
    except:
        return "ERROR"
    
            