from flask import Flask,render_template, request, make_response, Response, redirect
import json
from werkzeug.utils import secure_filename
from time import time
import sqlite3
from twilio.rest import Client
import csv
import xlwt
from flask_mail import Mail, Message
import io
import os
import threading
from plyer import notification
from datetime import date, datetime
from Adafruit_IO import RequestError, Client, Feed
from playsound import playsound 

UPLOAD_FOLDER = 'C:/Users/Dell/Desktop/XYMA/static/uploads/'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.urandom(24)


# SQLite3 Connection
conn = sqlite3.connect('data.db', check_same_thread=False)
curs = conn.cursor()

# Adafruit Connection
# ADAFRUIT_IO_USERNAME = "senthil_v"
# ADAFRUIT_IO_KEY = "c71df31bb11e4204993e69710cc0067e"
# aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
# temperature_feed = aio.feeds('temperature')
# humidity_feed = aio.feeds('humidity')

#Data into Adafruit
# def Adafruit():
#     threading.Timer(10.0, Adafruit).start()
#     for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
#         temp = row[1]
#         hum = row[2]
#     aio.send(temperature_feed.key, str(temp))
#     aio.send(humidity_feed.key, str(hum))
# Adafruit()

#Text to Speech  
playsound("welcome.mp3")

def notification():
    threading.Timer(5.0, notification).start()
    for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
        time = str(row[0])
        temp = row[1]
        hum = row[2]
    if(temp > 30):
        notification.notify(title="Message form ARMS", message=f"Temperature was High with {temp} C at {time}",timeout=2)
    if(hum > 30):
        notification.notify(title="Message form ARMS", message=f"Humidity was High with {hum}  at {time}",timeout=2)
notification()

# Error Handling
@app.errorhandler(404)
def error(error):
    return render_template('error.html'), 404

#Normal message config
def whatsappmsg(wa_number, wa_message):
    account_sid = 'ACCOUNT_SID'
    auth_token = 'AUTH_TOKEN'
    client = Client(account_sid, auth_token)
    message = client.messages \
        .create(
            from_='+12563339136',
            body=wa_message,
            to=wa_number
        )
    if message:
        return True
    else:
        return False

#Home Page
@app.route('/')
def main():
    return render_template('home.html')

#Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        if request.form['username'] != 'Admin' or request.form['password'] != 'admin' or request.form['api'] != '123456789ABCDEF':
            error = 'Invalid Credentials. Please try again.'
        else:
            return render_template('index.html')
    return render_template('login.html', error=error)

#Dashbaord Page
@app.route('/home', methods=["GET", "POST"])
def home():
    return render_template('index.html')

#Report Page
@app.route("/report")
def report():
    return render_template('report.html')

#track car Page
@app.route("/track")
def track():
    return render_template('markerflow.html')

#Remote Access Page
@app.route("/remote")
def remote():
    return render_template('remote.html')

#All data Page
@app.route("/alldata")
def alldata():
    conn.row_factory = sqlite3.Row
    curs.execute("SELECT * FROM data ORDER BY timestamp DESC")
    rows = curs.fetchall()
    return render_template('alldata.html', rows=rows)

#Web cam Page
@app.route("/cam")
def webcam():
    return render_template('cam.html')

#Upload File
@app.route("/upload")
def upload():
    return render_template(('upload.html'))

# Seperate Temerature Data Page
@app.route("/temp_data")
def tempdata():
    conn.row_factory = sqlite3.Row
    curs.execute("SELECT timestamp,temp FROM data ORDER BY timestamp DESC")
    tempdata = curs.fetchall()
    return render_template('tempdata.html',tempdata=tempdata)

# Seperate Humidity Data Page
@app.route("/hum_data")
def humdata():
    conn.row_factory = sqlite3.Row
    curs.execute("SELECT timestamp,hum FROM data ORDER BY timestamp DESC")
    humdata = curs.fetchall()
    return render_template('humdata.html',humdata=humdata)

#Upload file to Firebase storage
@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():
    file = request.files['image']
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))
    return render_template("/report.html")

# Messaging Service
@app.route("/wamsg", methods=['POST'])
def wamsg():
    wa_number = request.form['wa-phone']
    wa_message = request.form['wa-msg']
    wa_msg = whatsappmsg(wa_number, wa_message)
    if wa_msg:
        wa_error = 'Succesfull'
        return render_template('report.html', wa_error=wa_error)

    else:
        wa_error = 'Invalid Credentials. Please try again.'
        return render_template('report.html', wa_error=wa_error)

# Send Email
@app.route("/send_email")
def send_email():
    mail_settings = {
        "MAIL_SERVER": 'smtp.gmail.com',
        "MAIL_PORT": 465,
        "MAIL_USE_TLS": False,
        "MAIL_USE_SSL": True,
        "MAIL_USERNAME": 'EMAIL_ID',
        "MAIL_PASSWORD": 'PASSWORD'
    }

    app.config.update(mail_settings)
    mail = Mail(app)
    with app.app_context():
        msg = Message(subject="Mail from ARMS-Raspi",
                      sender=app.config.get("MAIL_USERNAME"),
                      recipients=["RECEIVER_MAIL_ID"],
                      body="Temp value is High")
        mail.send(msg)
    email_success = "Succesfull"
    return render_template('report.html', email_success=email_success)

# Download Report Excel Format
@app.route("/download/excel")
def download_report():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data")
    result = cursor.fetchall()

    #output in bytes
    output = io.BytesIO()
    # create WorkBook object
    workbook = xlwt.Workbook()
    # add a sheet
    sh = workbook.add_sheet('Data')

    # add headers
    sh.write(0, 0, 'Time Stamp')
    sh.write(0, 1, 'Temperature')
    sh.write(0, 2, 'Humidity')

    idx = 0
    for row in result:
        time = str(row[0])
        temp = row[1]
        hum = row[2]
        sh.write(idx+1, 0, time)
        sh.write(idx+1, 1, temp)
        sh.write(idx+1, 2, hum)
        idx += 1

    workbook.save(output)
    output.seek(0)

    return Response(output, mimetype="application/ms-excel", headers={"Content-Disposition": "attachment;filename=data.xls"})


# Download Report CSV Format
@app.route("/download/csv")
def download_csv():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data")
    result = cursor.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)

    line = ['Timestamp, Temperature, Humidity']
    # writer.writerow(line)
    for row in result:
        time = str(row[0])
        temp = str(row[1])
        hum = str(row[2])
        line = [time + ',' + temp + ',' + hum]
        writer.writerow(line)
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=data.csv"})


#Sensor Data
@app.route('/data', methods=["GET", "POST"])
def data():
    # Data Format
    # [TIME, Temperature, Humidity]
    for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
        temp = int(row[1])
        hum = int(row[2])
    Temperature = temp
    Humidity = hum
    data = [time() * 1000, Temperature, Humidity]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

#Location Data
@app.route('/locationdata', methods=["GET", "POST"])
def locationdata():
    for row in curs.execute("SELECT * FROM map ORDER BY timestamp DESC LIMIT 1"):
        longi = row[1]
        lati = row[2]
    Longitude = longi
    Latitude = lati
    data = {"geometry":{"type":"Point","coordinates":[Latitude, Longitude]},"type":"Feature","properties":{}}
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

if __name__ == "__main__":
    app.run(debug=True)
