from app import app
from flask import render_template


@app.route('/clock')
def clock():
    return render_template('clock.html')