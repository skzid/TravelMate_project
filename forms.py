from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class RegisterForm(FlaskForm):
    email = EmailField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=4)])
    password_again = PasswordField("Повторите пароль", validators=[DataRequired()])
    name = StringField("Имя пользователя", validators=[DataRequired()])
    about = TextAreaField("Немного о себе")
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    email = EmailField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class TripForm(FlaskForm):
    title = StringField("Название записи", validators=[DataRequired()])
    city = StringField("Город", validators=[DataRequired()])
    description = TextAreaField("Описание", validators=[DataRequired(), Length(min=10)])
    photo = FileField(
        "Фотография",
        validators=[FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Можно загрузить только изображение.")],
    )
    is_public = BooleanField("Показывать всем", default=True)
    submit = SubmitField("Сохранить")
