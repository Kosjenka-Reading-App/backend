from sqlalchemy import or_
from sqlalchemy.orm import Session

import models, schemas
import bcrypt


exercise_order_by_column = {
    schemas.ExerciseOrderBy.category: models.Exercise.category,
    schemas.ExerciseOrderBy.complexity: models.Exercise.complexity,
    schemas.ExerciseOrderBy.title: models.Exercise.title,
    schemas.ExerciseOrderBy.date: models.Exercise.date,
}


account_order_by_column = {
    schemas.AccountOrderBy.email: models.Account.email,
    schemas.AccountOrderBy.account_category: models.Account.account_category,
}


def get_exercise(db: Session, exercise_id: int, user_id: int | None = None):
    if user_id:
        db_exercise = (
            db.query(models.DoExercise)
            .select_from(models.Exercise)
            .join(models.Exercise.users)
            .filter(models.Exercise.id == exercise_id)
            .filter(models.DoExercise.user_id == user_id)
            .add_entity(models.Exercise)
            .first()
        )
        if db_exercise:
            exercise_completion = schemas.ExerciseCompletion.model_validate(
                db_exercise[0]
            )
            exercise = schemas.FullExerciseResponse.model_validate(db_exercise[1])
            exercise.completion = exercise_completion
            return exercise
    return db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()


def get_exercises(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    order_by: schemas.ExerciseOrderBy | None = None,
    order: schemas.Order | None = None,
    complexity: models.Complexity | None = None,
    category: models.Category | None = None,
    title_like: str | None = None,
    user_id: int | None = None,
):
    exercises = db.query(models.Exercise)
    if complexity:
        exercises = exercises.filter(models.Exercise.complexity == complexity)
    if category:
        exercises = exercises.filter(models.Exercise.category.contains(category))
    if title_like:
        exercises = exercises.filter(models.Exercise.title.like(f"%{title_like}%"))
    if user_id:
        exercises = (
            exercises.join(models.DoExercise, isouter=True)
            .add_entity(models.DoExercise)
            .filter(or_(models.DoExercise.user_id == 1, models.Exercise.users == None))
        )
    if order_by:
        exercises = exercises.order_by(
            exercise_order_by_column[order_by].desc()
            if order == schemas.Order.desc
            else exercise_order_by_column[order_by]
        )
    paginated_exercises = exercises.offset(skip).limit(limit)
    if user_id:
        exercises = []
        for ex, do_ex in paginated_exercises:
            if do_ex:
                ex_completion = schemas.ExerciseCompletion.model_validate(do_ex)
                ex = schemas.FullExerciseResponse.model_validate(ex)
                ex.completion = ex_completion
            exercises.append(ex)
        return exercises
    return paginated_exercises.all()


def create_exercise(db: Session, exercise: schemas.ExerciseCreate):
    db_exercise = models.Exercise(
        title=exercise.title,
        text=exercise.text,
        complexity=exercise.complexity,
    )
    db.add(db_exercise)
    if exercise.category:
        for category in exercise.category:
            db_category = get_category(db, category)
            if db_category is None:
                db_category = create_category(db, category)
            db_exercise.category.append(db_category)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def delete_exercise(db: Session, exercise_id: int):
    db.query(models.DoExercise).filter(
        models.DoExercise.exercise_id == exercise_id
    ).delete()
    db.delete(
        db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    )
    db.commit()


def update_exercise(db: Session, exercise_id: int, exercise: schemas.ExercisePatch):
    stored_exercise = (
        db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    )
    update_data = exercise.model_dump(exclude_unset=True)
    if exercise.category:
        _update_exercise_categories(db, stored_exercise, exercise.category)
        update_data.pop("category")
    for key in update_data:
        setattr(stored_exercise, key, update_data[key])
    db.commit()
    db.refresh(stored_exercise)
    return stored_exercise


def update_exercise_completion(
    db: Session,
    db_user: models.User,
    db_exercise: models.Exercise,
    completion: schemas.ExerciseCompletion,
):
    db_do_exercise = (
        db.query(models.DoExercise)
        .filter(models.DoExercise.exercise_id == db_exercise.id)
        .filter(models.DoExercise.user_id == db_user.id_user)
        .first()
    )
    if db_do_exercise is None:
        db_do_exercise = models.DoExercise()
        db.add(db_do_exercise)
        db_user.exercises.append(db_do_exercise)
        db_do_exercise.exercise = db_exercise
    update_data = completion.model_dump(exclude_unset=True)
    update_data.pop("user_id")
    for key in update_data:
        setattr(db_do_exercise, key, update_data[key])
    db.commit()
    db.refresh(db_do_exercise)
    return db_do_exercise


# Accounts
def password_hasher(raw_password: str):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


def get_account(db: Session, auth_user: schemas.AuthSchema, account_id: int):
    if auth_user.account_id == account_id:
        return (
            db.query(models.Account)
            .filter(models.Account.id_account == account_id)
            .first()
        )
    if models.AccountType(auth_user.account_category) == models.AccountType.Superadmin:
        return (
            db.query(models.Account)
            .filter(
                models.Account.id_account == account_id,
                models.Account.account_category == models.AccountType.Admin,
            )
            .first()
        )
    return None


def delete_account(db: Session, account_id: int):
    db.delete(
        db.query(models.Account).filter(models.Account.id_account == account_id).first()
    )
    db.commit()


def update_account(db: Session, account_id: int, account: schemas.AccountPatch):
    stored_account = (
        db.query(models.Account).filter(models.Account.id_account == account_id).first()
    )
    update_data = account.model_dump(exclude_unset=True)
    for key in update_data:
        setattr(stored_account, key, update_data[key])
    db.commit()
    db.refresh(stored_account)
    return stored_account


def get_accounts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    order_by: schemas.AccountOrderBy | None = None,
    order: schemas.Order | None = None,
    email_like: str | None = None,
):
    accounts = db.query(models.Account).filter(
        or_(
            models.Account.account_category == models.AccountType.Admin,
            models.Account.account_category == models.AccountType.Superadmin,
        )
    )
    if email_like:
        accounts = accounts.filter(models.Account.email.like(f"%{email_like}%"))
    if order_by:
        accounts = accounts.order_by(
            account_order_by_column[order_by].desc()
            if order == schemas.Order.desc
            else account_order_by_column[order_by]
        )
    return accounts.offset(skip).limit(limit).all()


def create_account(
    db: Session, account_in: schemas.AccountIn, account_category: models.AccountType
):
    hashed_password = password_hasher(account_in.password)
    account_db = models.Account(
        email=account_in.email,
        account_category=account_category,
        password=hashed_password,
    )
    db.add(account_db)
    db.commit()
    db.refresh(account_db)
    return account_db


def email_is_registered(db: Session, email: str):
    db_account = db.query(models.Account).filter(models.Account.email == email).first()
    return db_account is not None


# Users
def get_users(db: Session, account_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(models.User)
        .filter(models.User.id_account == account_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user(db: Session, user_id: int, account_id: int):
    return (
        db.query(models.User)
        .filter(models.User.id_account == account_id)
        .filter(models.User.id_user == user_id)
        .first()
    )


def update_user(db: Session, user_id: int, user: schemas.UserPatch):
    user_id = db.query(models.User).filter(models.User.id_user == user_id).first()
    update_data = user.model_dump(exclude_unset=True)
    for key in update_data:
        setattr(user_id, key, update_data[key])
    db.commit()
    db.refresh(user_id)
    return user_id


def delete_user(db: Session, user_id: int):
    db.query(models.DoExercise).filter(models.DoExercise.user_id == user_id).delete()
    db.delete(db.query(models.User).filter(models.User.id_user == user_id).first())
    db.commit()


def create_user(db: Session, account_id: int, user: schemas.UserCreate):
    db_user = models.User(
        id_account=account_id,
        username=user.username,
        proficiency=user.proficiency,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def _update_exercise_categories(
    db: Session, exercise: models.Exercise, categories: list[str]
):
    new_categories = []
    for category in categories:
        db_category = get_category(db, category)
        if db_category is None:
            db_category = create_category(db, category)
        new_categories.append(db_category)
    exercise.category = new_categories


def get_categories(
    db: Session,
    skip: int,
    limit: int,
    order: schemas.Order | None,
    name_like: str | None,
):
    categories = db.query(models.Category)
    if name_like:
        categories = categories.filter(models.Category.category.like(f"%{name_like}%"))
    if order:
        categories = categories.order_by(
            models.Category.category.desc()
            if order == schemas.Order.desc
            else models.Category.category
        )
    categories = categories.offset(skip).limit(limit).all()
    return [cat.category for cat in categories]


def get_category(db: Session, category: str):
    return (
        db.query(models.Category).filter(models.Category.category == category).first()
    )


def create_category(db: Session, category: str):
    db_category = models.Category(
        category=category,
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def delete_category(db: Session, category: str):
    db.delete(
        db.query(models.Category).filter(models.Category.category == category).first()
    )
    db.commit()


def update_category(db: Session, old_category: str, new_category: schemas.Category):
    stored_category = (
        db.query(models.Category)
        .filter(models.Category.category == old_category)
        .first()
    )
    setattr(stored_category, "category", new_category.category)
    db.commit()
    db.refresh(stored_category)
    return stored_category
