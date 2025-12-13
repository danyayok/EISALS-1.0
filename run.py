import config
from app import create_app
from app.routers import register_routes

app = create_app()
app.secret_key = config.Config.SECRET_KEY

register_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
