from app import create_app
from app.settings import get_runtime_security_settings

app = create_app()


if __name__ == "__main__":
    settings = get_runtime_security_settings()
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
