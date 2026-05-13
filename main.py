import os
from datetime import datetime
import requests
from flask import Flask, abort, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from data import db_session
from data.trips import Trip
from data.users import User
from forms import LoginForm, RegisterForm, TripForm


UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
GEOCODER_API_KEY = "8013b162-6b42-4997-9691-77b7074026e0"


app = Flask(__name__)
app.config["SECRET_KEY"] = "travelmate_secret_key"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Сначала войдите в аккаунт."
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def prepare_folders():
    os.makedirs("db", exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


prepare_folders()
db_session.global_init(os.path.join("db", "travelmate.sqlite"))


def geocode_city(city_name):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": GEOCODER_API_KEY,
        "geocode": city_name,
        "format": "json",
        "results": 1,
    }
    response = requests.get(url, params=params, timeout=5)
    response.raise_for_status()
    data = response.json()
    feature = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    lon, lat = map(float, feature["Point"]["pos"].split())
    country = feature["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"][0]["name"]
    return country, lon, lat


def save_trip_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{current_user.id}_{timestamp}_{filename}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def trip_from_form(form, trip=None):
    if trip is None:
        trip = Trip()
    trip.title = form.title.data
    trip.city = form.city.data.strip()
    trip.description = form.description.data
    trip.is_public = form.is_public.data
    try:
        country, lon, lat = geocode_city(trip.city)
        trip.country = country
        trip.longitude = lon
        trip.latitude = lat
    except Exception:
        trip.country = "Не удалось определить"
        trip.longitude = None
        trip.latitude = None
    photo_filename = save_trip_photo(form.photo.data)
    if photo_filename:
        trip.photo_filename = photo_filename
    return trip


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return make_response(jsonify({"error": "Not found"}), 404)
    return render_template("error.html", title="404", message="Страница не найдена"), 404


@app.errorhandler(400)
def bad_request(_):
    if request.path.startswith("/api/"):
        return make_response(jsonify({"error": "Bad request"}), 400)
    return render_template("error.html", title="400", message="Некорректный запрос"), 400


@app.route("/")
def index():
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        trips = db_sess.query(Trip).filter(
            (Trip.user_id == current_user.id) | (Trip.is_public == True)
        ).order_by(Trip.created_date.desc()).all()
    else:
        trips = db_sess.query(Trip).filter(
            Trip.is_public == True
        ).order_by(Trip.created_date.desc()).all()
    return render_template("index.html", title="TravelMate", trips=trips)



@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template(
                "register.html",
                title="Регистрация",
                form=form,
                message="Пароли не совпадают",
            )
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template(
                "register.html",
                title="Регистрация",
                form=form,
                message="Пользователь с такой почтой уже есть",
            )
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect(url_for("login"))
    return render_template("register.html", title="Регистрация", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for("index"))
        return render_template(
            "login.html",
            title="Вход",
            form=form,
            message="Неправильная почта или пароль",
        )
    return render_template("login.html", title="Вход", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/trips/new", methods=["GET", "POST"])
@login_required
def add_trip():
    form = TripForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        trip = trip_from_form(form)
        trip.user_id = current_user.id
        db_sess.add(trip)
        db_sess.commit()
        return redirect(url_for("index"))
    return render_template(
        "trip_form.html",
        title="Новое место",
        form=form,
        button_text="Добавить",
    )


@app.route("/trips/<int:trip_id>/edit", methods=["GET", "POST"])
@login_required
def edit_trip(trip_id):
    db_sess = db_session.create_session()
    trip = db_sess.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == current_user.id,
    ).first()
    if not trip:
        abort(404)
    form = TripForm()

    if request.method == "GET":
        form.title.data = trip.title
        form.city.data = trip.city
        form.description.data = trip.description
        form.is_public.data = trip.is_public

    if form.validate_on_submit():
        trip_from_form(form, trip)
        db_sess.commit()
        return redirect(url_for("index"))

    return render_template(
        "trip_form.html",
        title="Редактирование",
        form=form,
        button_text="Сохранить",
    )


@app.route("/trips/<int:trip_id>/delete")
@login_required
def delete_trip(trip_id):
    db_sess = db_session.create_session()
    trip = db_sess.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == current_user.id,
    ).first()

    if not trip:
        abort(404)
    db_sess.delete(trip)
    db_sess.commit()
    return redirect(url_for("index"))


@app.route("/api/trips", methods=["GET"])
def api_get_trips():
    db_sess = db_session.create_session()
    trips = db_sess.query(Trip).filter(
        Trip.is_public == True
    ).order_by(Trip.created_date.desc()).all()

    return jsonify({
        "trips": [
            trip.to_dict(
                only=("id", "title", "city", "country", "latitude", "longitude")
            )
            for trip in trips
        ]
    })


@app.route("/api/trips/<int:trip_id>", methods=["GET"])
def api_get_one_trip(trip_id):
    db_sess = db_session.create_session()
    trip = db_sess.get(Trip, trip_id)
    if not trip or not trip.is_public:
        return make_response(jsonify({"error": "Not found"}), 404)

    return jsonify({
        "trip": trip.to_dict(
            only=(
                "id",
                "title",
                "city",
                "country",
                "latitude",
                "longitude",
                "description",
                "user.name",
            )
        )
    })


@app.route("/api/trips", methods=["POST"])
def api_create_trip():
    if not request.json:
        return make_response(jsonify({"error": "Empty request"}), 400)

    required = ["title", "city", "description", "user_id"]
    if not all(key in request.json for key in required):
        return make_response(jsonify({"error": "Bad request"}), 400)
    db_sess = db_session.create_session()
    user = db_sess.get(User, request.json["user_id"])
    if not user:
        return make_response(jsonify({"error": "User not found"}), 404)
    trip = Trip(
        title=request.json["title"],
        city=request.json["city"],
        description=request.json["description"],
        is_public=bool(request.json.get("is_public", True)),
        user=user,
    )
    try:
        trip.country, trip.longitude, trip.latitude = geocode_city(trip.city)
    except Exception:
        trip.country = "Не удалось определить"
    db_sess.add(trip)
    db_sess.commit()
    return jsonify({"id": trip.id})


def main():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
