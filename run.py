from app import create_app

app = create_app()  # defaults to 'default' configuration

if __name__ == '__main__':
    app.run(debug=True)
