from flask import Flask
from app.routes.main_routes import main_bp
from app.routes.rag_routes import bp as rag_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(main_bp)
    app.register_blueprint(rag_bp)
    return app
