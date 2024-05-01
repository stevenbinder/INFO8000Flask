from flask import Flask, render_template, request, redirect,url_for, make_response,jsonify
from werkzeug.utils import secure_filename
from datetime import date,datetime
import os, time, sqlite3
import pandas as pd
import requests
import json
import numpy as np
from passlib.hash import sha256_crypt
import bcrypt
from operator import itemgetter

app=Flask(__name__,static_folder='data')
username=''
password=''
hashPass=''

def dbConnectionUsers():
    con=sqlite3.connect('data/users.db')
    return con

def dbConnectionData():
    con=sqlite3.connect('data/data.db')
    return con

@app.route('/',methods=['GET','POST'])
def root():
    global username,password
    username=request.form.get('username','')
    password=request.form.get('password','')
    with dbConnectionUsers() as con:
        c=con.cursor()
        if username!='':        
            c.execute("SELECT username, password, APIkey FROM users WHERE username=? AND password=?",(username,password))
            res=c.fetchone()
            if res:
                if bcrypt.checkpw(bytes(password,'utf-8'),res[2])==True:
                    return redirect(url_for('home',username=username))
            else:
                bpass=bytes(password,'utf-8')
                hashPass=bcrypt.hashpw(bpass,bcrypt.gensalt(rounds=14))
                c.execute("INSERT INTO users(username,password,APIkey) values (?,?,?);",(username,password,hashPass))
                return redirect(url_for('home',username=username))
    return render_template('login.html',title='login')

@app.route('/home/<username>', methods=['GET','POST'])
def home(username):
    global hashPass
    with dbConnectionUsers() as con:
        c=con.cursor()
        c.execute('SELECT * FROM users WHERE username=?',(username,))
        res=c.fetchone()
        if res:
            username=res[0]
            password=res[1]
            hashPass=res[2]
            return render_template('home.html',username=username,hashPass=hashPass),hashPass

@app.route('/report', methods=['POST'])
def report():
    des=request.form.get('des','')
    file=request.files.get('file',None)
    ipAdd=str(request.remote_addr)
    ipAdd=ipAdd.replace(' ','')
    if ipAdd=='127.0.0.1':
        ipAdd='47.4.229.90'     
    resp=requests.get(f'https://geolocation-db.com/jsonp/{ipAdd}')
    res=resp.content.decode()
    res=res.split("(")[1].strip(")")
    res=json.loads(res)
    lat=res['latitude']
    lon=res['longitude']
    state=res['state']
    county=res['city']
    resp=requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m").json()
    curTempC=resp['current']['temperature_2m']
    curWindKmH=resp['current']['wind_speed_10m']
    weather=str(curTempC)+'|'+str(curWindKmH)
    apiKey=open('data/apiKey.txt').read()
    host="https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    params={'key':apiKey}
    query=f'In one word, please categorize this description:{des}'
    body={'contents':[{'parts':[{'text':query}]}]}
    res=requests.post(host,params=params,json=body)
    categorization=res.json()['candidates'][0]['content']['parts'][0]['text']
    dateTime=date.today()
    if file:
        file.save(f'data/{secure_filename(file.filename)}')
        fileName=file.filename
        with dbConnectionData() as con:
            c=con.cursor()
            c.execute("INSERT INTO data(username,APIkey,ip_address,date_time,latitude,longitude,description,file_name,state,county,weather,model_des) values (?,?,?,?,?,?,?,?,?,?,?,?);",
                                        (username,hashPass,ipAdd,dateTime,lat,lon,des,fileName,state,county,weather,categorization))
        return render_template('report.html',username=username,password=password,hashPass=hashPass,des=des,fileName=fileName,ipAdd=ipAdd,dateTime=dateTime,lat=lat,lon=lon,state=state,county=county,curTempC=curTempC,curWindKmH=curWindKmH,categorization=categorization)
    else:
        return render_template('home.html',username=username,password=password,hashPass=hashPass)

@app.route('/data', methods=['GET'])
def data():
    table=[]
    if request.method=='GET':
        res=request.args

    file_type=res.get('file_type',default='',type=str)
    start_date=res.get('start_date',default='',type=str)
    end_date=res.get('end_date',default='',type=str)
    lat=res.get('lat',default='',type=str)
    lng=res.get('lng',default='',type=str)
    dist=res.get('dist',default='',type=str)
    sort=res.get('sort',default='newest',type=str)
    max=res.get('max',default='',type=str)
    if sort=='newest':
        dbSort='DESC'
    if sort=='oldest':
        dbSort='ASC'
    with dbConnectionData() as con:
        c=con.cursor()
        c.execute(f'SELECT * FROM data ORDER BY date_time {dbSort}')
        res=c.fetchall()
    if start_date==end_date==lat==lng==dist=='':
        table=res
    else:
        for entry in res:
            if start_date!='' and end_date!='':
                if int(entry[3][:4])>=int(start_date[:4]) and int(entry[3][:4])<=int(end_date[:4]):
                    if int(entry[3][5:7])>=int(start_date[5:7]) and int(entry[3][5:7])<=int(end_date[5:7]):
                        if int(entry[3][8:10])<=int(end_date[8:10]):
                            table.append(entry)      
            else:
                if start_date!='':
                    if int(entry[3][:4])>=int(start_date[:4]):
                        if int(entry[3][5:7])>int(start_date[5:7]):
                            table.append(entry)
                        else:
                            if int(entry[3][8:10])>=int(start_date[8:10]):
                                table.append(entry) 

                if end_date!='':
                    if int(entry[3][:4])<=int(end_date[:4]):
                        if int(entry[3][5:7])<int(end_date[5:7]):
                            table.append(entry)
                        else:
                            if int(entry[3][5:7])==int(end_date[5:7]) and int(entry[3][8:10])<=int(end_date[8:10]):
                                table.append(entry)
            if lat!='':
                lat1=np.deg2rad(float(lat))
                lng1=np.deg2rad(float(lng))
                dist=float(dist)   
                lat2=np.deg2rad(float(entry[4]))
                lng2=np.deg2rad(float(entry[5]))
                distance=(2*6371)*np.arcsin(np.sqrt(((np.sin((lat2-lat1)/2)**2))+(np.cos(lat1))*(np.cos(lat2))*((np.sin((lng2-lng1)/2)**2))))
                if distance<dist:
                    table.append(entry)  
    if file_type=='CSV':
        csvData=pd.DataFrame(data=table)
        csvData=csvData.drop(labels=[1,12],axis=1)
        csvData=csvData.rename(columns={0:'Username',2:'IP Address',3:'Date of Upload',4:'Latitude',5:'Longitude',6:'File Description',7:'File Name',8:'State',9:'County',10:'Weather',11:"Gemini's Description"})
        response=make_response(csvData.to_csv(index=False))
        response.headers['Content-Disposition']='attachment; filename=data.csv'
        return response
    if file_type=='JSON':
        return jsonify(table)
    return render_template('data.html',table=table)
    

if __name__=='__main__':    
    app.run(debug=True,port=5000)