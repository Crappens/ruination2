"""A dev server to aid in development."""

from app.app_factories import init_runination_app

if __name__ == '__main__':
    app = init_runination_app(debug=True, config_name='qa')
    app.run(host='0.0.0.0', port=8000)
