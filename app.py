import os
from flask import Flask
from extensions import db, bcrypt, login_manager, migrate
from models import User
from dotenv import load_dotenv
from routes import routes
from urllib.parse import quote_plus  
from flask_dance.contrib.google import make_google_blueprint, google

# Load env vars
load_dotenv()

app = Flask(__name__)

# Secret key
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

# Database config
sql_uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")

if sql_uri:
    # Fix "postgres://" → "postgresql://" if needed
    if sql_uri.startswith("postgres://"):
        sql_uri = sql_uri.replace("postgres://", "postgresql://", 1)
else:
    # Build URI from parts for local dev
    user = os.getenv("DB_USER")
    pwd = quote_plus(os.getenv("DB_PASS"))
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    sql_uri = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"


app.config['SQLALCHEMY_DATABASE_URI'] = sql_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder
app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER", os.path.join('static', 'upload'))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Google login
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=["https://www.googleapis.com/auth/userinfo.profile",
           "https://www.googleapis.com/auth/userinfo.email",
           "openid"],
    redirect_to="routes.google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

# Init extensions
db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "routes.auth"

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register routes blueprint
app.register_blueprint(routes)

# Dev only: ensure DB tables exist
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

