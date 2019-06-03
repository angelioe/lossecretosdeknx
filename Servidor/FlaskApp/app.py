from threading import Lock
import sqlite3, os, json, urllib3, asyncio, getopt, sys, sqlite3, datetime
from flask import Flask, render_template, session, request, g, url_for, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect


# Create app
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'
socketio = SocketIO(app, async_mode=None)
thread = None
thread_lock = Lock()


def internet_on():
    try:
        http = urllib3.PoolManager(timeout=3.0)
        url = 'http://www.google.com'
        response = http.request('GET', url)
        if response.status == 200 : return True
        if response.status >= 400 or response.status <=600: return False
    except urllib3.URLError as err:
        return False

def background_thread():
    """Example of how to send server generated events to clients."""
    while True:
        socketio.sleep(0.3)
        xconn = sqlite3.connect('./FlaskApp/hopeitworks.db')
        xconn_c = xconn.cursor()
        xsys = xconn_c.execute("SELECT * FROM INSTRUCTIONS ORDER BY ID DESC LIMIT 10")
        system=[]
        for rows in xsys: system.append({'ids': rows[0], 'dates': rows[1], 'controllers': rows[2], 'devices': rows[3], 'functions': rows[4], 'values': rows[5], 'states': rows[6]})
        xsys_json = json.dumps({'logs':system})
        xtel = xconn_c.execute("SELECT * FROM DATA ORDER BY ID DESC LIMIT 10")
        telegram=[]
        for row in xtel: telegram.append({'idd': row[0], 'dated': row[1], 'controllerd': row[2], 'deviced': row[3], 'functiond': row[4], 'valued': row[5]})
        xtel_json = json.dumps({'telegrams':telegram})
        socketio.emit('my_response',{'data':xtel_json, 'sdata':xsys_json})
        xconn.close()



@app.route("/")
def es():
    global thread
    with thread_lock:
        if thread is None: thread = socketio.start_background_task(target=background_thread)
    return render_template('inicio.html',  async_mode=socketio.async_mode)


@app.route('/', methods=['POST'])
def es_post():
    if (request.form['action']=='friki'):
        return redirect(url_for('friki'))
    controller,device,function,value = str(request.form['action']).split("-")
    conn = sqlite3.connect('./FlaskApp/hopeitworks.db')
    try:
        conn.execute('''CREATE TABLE INSTRUCTIONS
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 DATE_TIME TEXT NOT NULL,
                 CONTROLLER TEXT NOT NULL,
                 DEVICE TEXT NOT NULL,
                 FUNCTION TEXT NOT NULL,
                 VALUE TEXT NOT NULL,
                 STATE TEXT NOT NULL);''')
        conn.execute('''CREATE TABLE DATA
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 DATE_TIME TEXT NOT NULL,
                 CONTROLLER TEXT NOT NULL,
                 DEVICE TEXT NOT NULL,
                 FUNCTION TEXT NOT NULL,
                 VALUE TEXT NOT NULL);''')
    except:
        e = "Database already created"
    date_time=str(datetime.datetime.now())+" "+str(datetime.datetime.today().weekday())
    conn.execute("INSERT INTO INSTRUCTIONS (DATE_TIME,CONTROLLER,DEVICE,FUNCTION,VALUE,STATE)\
                    VALUES (?,?,?,?,?,?)",[date_time,controller,device,function,value,"p"]);
    conn.commit()
    conn.close()
    return ('', 204)



@app.route('/friki')
def friki():
    global thread
    with thread_lock:
        if thread is None: thread = socketio.start_background_task(target=background_thread)
    return render_template('friki.html',  async_mode=socketio.async_mode)

@app.route('/friki', methods=['POST'])
def friki_post():
    if (request.form['action']=='inicio'):
        return redirect(url_for('es'))
    return ('', 204)


if __name__ == "__main__":
    conn = sqlite3.connect('./FlaskApp/hopeitworks.db')
    try:
        conn.execute('''CREATE TABLE INSTRUCTIONS
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 DATE_TIME TEXT NOT NULL,
                 CONTROLLER TEXT NOT NULL,
                 DEVICE TEXT NOT NULL,
                 FUNCTION TEXT NOT NULL,
                 VALUE TEXT NOT NULL,
                 STATE TEXT NOT NULL);''')
        conn.execute('''CREATE TABLE DATA
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 DATE_TIME TEXT NOT NULL,
                 CONTROLLER TEXT NOT NULL,
                 DEVICE TEXT NOT NULL,
                 FUNCTION TEXT NOT NULL,
                 VALUE TEXT NOT NULL);''')
    except:
        e = "Database already created"
    conn.close()
    socketio.run(app,host='0.0.0.0',port=5000)
