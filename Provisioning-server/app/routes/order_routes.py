from flask import Blueprint
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

from app.config import settings
from app.controllers import order_controller

# DB setup
engine = create_engine(settings.DATABASE_URL)
Session = scoped_session(sessionmaker(bind=engine))

# Blueprint
order_bp = Blueprint("order_api", __name__)


@order_bp.route("/device_order", methods=["POST"])
def create_order():
    session = Session()
    try:
        return order_controller.create_device_order(session)
    finally:
        session.close()
