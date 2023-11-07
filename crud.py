from sqlalchemy.orm import Session

import models, schemas
import bcrypt


def get_exercise(db: Session, exercise_id: int):
    return db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()


def get_exercises(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    order_by: str = "",
    title_like: str = "",
):
    exercises = db.query(models.Exercise)
    if title_like:
        exercises = exercises.filter(models.Exercise.title.like(f"%{title_like}%"))
    if order_by:
        match order_by:
            case "complexity":
                exercises = exercises.order_by(models.Exercise.complexity)
    return exercises.offset(skip).limit(limit).all()


def create_exercise(db: Session, exercise: schemas.ExerciseCreate):
    db_exercise = models.Exercise(
        title=exercise.title,
        text=exercise.text,
        complexity=exercise.complexity,
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def delete_exercise(db: Session, exercise_id: int):
    db.delete(
        db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    )
    db.commit()


def update_exercise(db: Session, exercise_id: int, exercise: schemas.ExercisePatch):
    stored_exercise = (
        db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    )
    update_data = exercise.model_dump(exclude_unset=True)
    for key in update_data:
        setattr(stored_exercise, key, update_data[key])
    db.commit()
    db.refresh(stored_exercise)
    return stored_exercise


def password_hasher(raw_password: str):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


def get_account(db: Session, account_id: int):
    return (
        db.query(models.Account).filter(models.Account.id_account == account_id).first()
    )


def delete_account(db: Session, account_id: int):
    db.delete(
        db.query(models.Account).filter(models.Account.id_account == account_id).first()
    )
    db.commit()


def update_account(db: Session, account_id: int, account: schemas.AccountOut):
    stored_account = (
        db.query(models.Account).filter(models.Account.id_account == account_id).first()
    )
    update_data = account.model_dump(exclude_unset=True)
    for key in update_data:
        setattr(stored_account, key, update_data[key])
    db.commit()
    db.refresh(stored_account)
    return stored_account


def get_accounts(db: Session):
    return db.query(models.Account).all()


def save_user(db: Session, account_in: schemas.AccountIn):
    hashed_password = password_hasher(account_in.password)
    account_db = models.Account(
        email=account_in.email,
        is_user=account_in.is_user,
        is_super_admin=account_in.is_super_admin,
        password=hashed_password,
    )
    db.add(account_db)
    db.commit()
    db.refresh(account_db)
    return account_db


# Users
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id_user == user_id).first()


def update_user(db: Session, user_id: int, user: schemas.UserPatch):
    user_id = db.query(models.User).filter(models.User.id_user == user_id).first()
    update_data = user.model_dump(exclude_unset=True)
    for key in update_data:
        setattr(user_id, key, update_data[key])
    db.commit()
    db.refresh(user_id)
    return user_id


def delete_user(db: Session, user_id: int):
    db.delete(db.query(models.User).filter(models.User.id_user == user_id).first())
    db.commit()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        id_account=user.id_account,
        username=user.username,
        proficiency=user.proficiency,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
