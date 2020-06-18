# The "main.py" file is the file that you actually run to make the whole app work.

from app import app
import os

if __name__ == "__main__":
    
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    # app.run(debug="True", ssl_context='adhoc')
    # app.run(debug="True", ssl_context=('cert.pem', 'key.pem'))
    app.run()