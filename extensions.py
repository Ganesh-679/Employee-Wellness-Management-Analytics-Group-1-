from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()

# In-memory rate limiter — fine for a dev/college-project server.
# For production with multiple workers, back this with Redis instead.
limiter = Limiter(key_func=get_remote_address)
