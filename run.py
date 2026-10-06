"""Local development server.

Debug mode is OFF unless you ask for it:  set FLASK_DEBUG=1  (Windows: $env:FLASK_DEBUG=1)
"""

import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
