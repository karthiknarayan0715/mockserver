from sys import modules
from typing import Optional
from app import app, mysql
from flask import render_template, redirect, request, session, flash, url_for, abort
from pymysql.cursors import DictCursor
from random import randrange
import os

conn = mysql.connect()
option = 0

@app.errorhandler(404)
def error(e):
    return render_template('404.html')

@app.route("/")
@app.route("/home")
def home():
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur=conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE creator_id=%s',(session['id']))
    servers = cur.fetchall()
    return render_template('home.html', servers=servers)

@app.route("/login", methods = ['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect('home')
    if request.method == 'POST':
        form = request.form
        username = form.get('username')
        password = form.get('password')
        cur=conn.cursor(DictCursor)
        cur.execute('SELECT * FROM users WHERE username=%s AND password=%s', (username, password))
        account = cur.fetchone()
        if account == None:
            flash('Incorrect username or password')
        else:
            session['logged_in'] = True
            session['id'] = account.get('id')
            session['username'] = account.get('username')
            session['name'] = account.get('name')
            session['email'] = account.get('email')
            return redirect('home')
    return render_template('login.html', title="Login", session=session)

@app.route("/register", methods = ['POST', 'GET'])
def register():
    if 'logged_in' in session:
        return redirect('home')
    if request.method == 'POST':
        form = request.form
        username = form.get('username')
        password = form.get('password')
        password2 = form.get('password2')
        if username and password:
            if password==password2:
                cur = conn.cursor(DictCursor)
                cur.execute('SELECT * FROM users WHERE username=%s', (username))
                account = cur.fetchone()
                if account == None:
                    cur.execute('INSERT INTO users (username, password) VALUES(%s,%s)', (username, password))
                    flash("Your account has been registered, you can login now")
                    conn.commit()
                    cur.close()
                    return redirect(url_for('login'))
                else:
                    flash('looks like you already have an account, try logging in')
            else:
                flash('Password and Repeat password don\'t match')
        else:
            flash('Please fill the form first')
    return render_template('register.html', title="Register",session=session)

@app.route("/logout", methods=['GET'])
def logout():
    session['logged_in'] = False
    session.pop('logged_in')
    session.pop('id')
    session.pop('username')
    session.pop('name')
    session.pop('email')
    return redirect(url_for('login'))

@app.route("/new_server", methods=['POST', 'GET'])
def newserver():
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur = conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE creator_id=%s',(session['id']))
    users_servers = cur.fetchall()
    if request.method == 'POST':
        for server in users_servers:
            if request.form.get('servername') == server['name']:
                flash('Looks like you already have a server named '+server['name'])
                return render_template('newserver.html')
        cur.execute('INSERT INTO servers(name, creator_id) VALUES(%s, %s)', (request.form.get('servername'), session['id']))
        server_id = cur.lastrowid
        conn.commit()
        cur.close()
        flash('Your server has been created!')
        return redirect(url_for('home'))
    return render_template('newserver.html')

@app.route("/<server_name>", methods = ['POST', 'GET'])
def serverpage(server_name):
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur=conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE name=%s AND creator_id=%s', (server_name, session['id']))
    server = cur.fetchone()
    if server:
        cur.execute('SELECT * FROM models WHERE server_id=%s', (server['id']))
        models = cur.fetchall()
        cur.execute('SELECT * FROM routes WHERE server_id=%s', (server['id']))
        routes = cur.fetchall()
        if request.method=='POST':
            for route in routes:
                if request.form.get(str(route['id'])):
                    cur.execute('DELETE FROM routes WHERE id=%s', (str(route['id'])))
                    conn.commit()
                    cur.execute('SELECT * FROM routes WHERE server_id=%s', (server['id']))
                    routes = cur.fetchall()
                    return render_template('serverpage.html', server=server, models=models, routes=routes)
            for model in models:
                if request.form.get(str(model['id'])):
                    cur.execute('DELETE FROM models WHERE id=%s', (str(model['id'])))
                    cur.execute('DELETE FROM fields WHERE model_id=%s', (str(model['id'])))
                    conn.commit()
                    cur.execute('SELECT * FROM models WHERE server_id=%s', (server['id']))
                    models = cur.fetchall() 
                    return render_template('serverpage.html', server=server, models=models, routes=routes)
        return render_template('serverpage.html', server=server, models=models, routes=routes)
    else:
        abort(404)

@app.route("/<server_name>/new_model", methods = ['GET', 'POST'])
def newmodel(server_name):
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur = conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE name=%s AND creator_id=%s', (server_name, session['id']))
    server = cur.fetchone()
    cur.execute('SELECT model_name FROM models WHERE server_id=%s', (server['id']))
    models = cur.fetchall()
    if not server:
        abort(404)
    elif not server['creator_id'] == session['id']:
        flash('Access denied')
        return redirect(url_for('home'))
    global option
    if request.method == "POST":
        if request.form.get('addcolumn'):
            option = option+1
            return render_template('newmodel.html', option=option)
        if request.form.get('removecol'):   
            option = option-1
            return render_template('newmodel.html', option=option)
        if request.form.get('submit'):
            fields = []
            if not request.form.get('db_name'):
                flash('Please fill the form')
                return render_template('newmodel.html', option=option)
            for i in range(option):
                if not request.form.get(str(i)):
                    flash('Please fill the form')
                    return render_template('newmodel.html', option=option)
                for j in range(len(fields)):
                    if (j, request.form.get(str(i))) in fields:
                        flash('Two field can\'t have the same name!')
                        return render_template('newmodel.html', option=option)
                fields.append((i, request.form.get(str(i))))
            for model in models:
                if model['model_name']==request.form.get('db_name'):
                    flash('Looks like you already have a model named '+request.form.get('db_name'))
                    return render_template('newmodel.html', option=option)
            if len(fields)<3:
                flash('You need atleast 3 fields to continue')
                return render_template('newmodel.html', option=option)
            cur = conn.cursor()
            cur.execute('INSERT INTO models(server_id, model_name) VALUES(%s, %s)', (server['id'], request.form.get('db_name')))
            model_id = cur.lastrowid
            for field in fields:
                cur.execute('INSERT INTO fields(model_id, field_index, field) VALUES(%s, %s, %s)', (model_id, field[0], field[1]))
            conn.commit()
            flash('model created')
            return redirect('/'+server_name)          

    return render_template('newmodel.html', option=option)

@app.route("/<server_name>/models/<model_name>")
def modelpage(server_name, model_name):
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur = conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE name=%s AND creator_id=%s', (server_name, session['id']))
    server = cur.fetchone()
    if not server:
        abort(404)
    elif not server['creator_id'] == session['id']:
        flash('Access denied')
        return redirect(url_for('home'))
    cur.execute('SELECT * FROM models WHERE model_name=%s AND server_id=%s', (model_name, server['id']))
    model = cur.fetchone()
    if not model:
        abort(404)
    data = []
    final_data=[]
    cur.execute('SELECT * FROM fields WHERE model_id=%s', (model['id']))
    fields = cur.fetchall()
    for field in fields:
        cur.execute('SELECT * FROM data WHERE field_id=%s', (field['id']))
        cur_data=cur.fetchall()
        data.append(cur_data)
    for i in range(len(data)):
        for j in range(len(data[i])):
            final_data.append([j, data[i][j]['value']])
    print(final_data)
    print(len(data[0]))
    return render_template('modelpage.html', model = model, fields=fields, server=server, data=final_data, value=len(data[0]))

@app.route("/<server_name>/new_route", methods=['GET', 'POST'])
def newroute(server_name):
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur = conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE name=%s AND creator_id=%s', (server_name, session['id']))
    server = cur.fetchone()
    if not server:
        abort(404)
    elif not server['creator_id'] == session['id']:
        flash('Access denied')
        return redirect(url_for('home'))
    if request.method == "POST":
        html_code = str(request.form.get('html_code'))
        name = request.form.get('route_name')
        cur=conn.cursor(DictCursor)
        cur.execute('SELECT * FROM routes WHERE server_id=%s', (server['id']))
        routes_in_server = cur.fetchall()
        for route in routes_in_server:
            if name==route['name']:
                flash('Looks like that name already exists!')
                return render_template('newroute.html')
        print(html_code)
        cur.execute('INSERT INTO routes(server_id, html_code, name) VALUES(%s,%s,%s)',(server['id'], html_code, name))
        conn.commit()
    return render_template('newroute.html')

@app.route("/<server_name>/routes/<route_name>")
def routepage(server_name, route_name):
    if not 'logged_in' in session:
        flash('please login to proceed')
        return redirect(url_for('login'))
    cur = conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE name=%s AND creator_id=%s', (server_name, session['id']))
    server = cur.fetchone()
    cur.execute('SELECT model_name FROM models WHERE server_id=%s', (server['id']))
    models = cur.fetchall()
    print(models)
    if not server:
        abort(404)
    elif not server['creator_id'] == session['id']:
        flash('Access denied')
        return redirect(url_for('home'))
    cur.execute('SELECT * FROM routes WHERE name=%s AND server_id=%s', (route_name, server['id']))
    route = cur.fetchone()
    if route:
        return route['html_code']
    else:
        abort(404)

@app.route("/<server_name>/models/<model_name>/add_data", methods = ['GET', 'POST'])
def adddata(server_name, model_name):
    cur = conn.cursor(DictCursor)
    cur.execute('SELECT * FROM servers WHERE name=%s AND creator_id=%s', (server_name, session['id']))
    server = cur.fetchone()
    cur.execute('SELECT * FROM models WHERE model_name=%s and server_id=%s', (model_name, server['id']))
    model = cur.fetchone()
    cur.execute('SELECT * FROM fields WHERE model_id=%s',(model['id']))
    fields = cur.fetchall()
    if not server:
        abort(404)
    elif not server['creator_id'] == session['id']:
        flash('Access denied')
        return redirect(url_for('home'))
    if not model:
        abort(404)
    if not model['server_id']==server['id']:
        abort(404)
    if request.method=="POST":
        field_vals = []
        for field in fields:
            field_vals.append({field['id']: request.form.get(str(field['id']))})
            cur.execute('INSERT INTO data(field_id, value) VALUES (%s, %s)', (field['id'], request.form.get(str(field['id']))))
            conn.commit()
        return redirect('/'+server_name+'/models/'+model_name)
    return render_template('add_data.html', fields=fields)