from flask import Flask
from app.routes.device_routes import device_bp
from app.routes.order_routes import order_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(device_bp)
    app.register_blueprint(order_bp)
    return app