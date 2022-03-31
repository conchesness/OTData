from app import app
import os
from flask import render_template, redirect, url_for, flash

@app.route('/equity/<currdir>')
@app.route('/equity')
def equity(currdir=None):
    charts = {}
    root = './app/static/Spring2022'
    for info in os.walk(root, topdown=True): 
        rootDirs = info[1]
        break
    for directory in rootDirs:
        for info in os.walk(f'{root}/{directory}', topdown=True):
            charts[info[0]] = info[2]
    return render_template('equity.html', root = root, rootDirs = rootDirs, charts=charts, currdir=currdir)