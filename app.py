from flask import Flask, render_template, request, redirect, session
from openpyxl import Workbook, load_workbook
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# สร้างไฟล์ผู้ใช้
if not os.path.exists("users.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(["username", "password"])
    wb.save("users.xlsx")

# สร้างไฟล์บันทึกการตรวจสอบ
if not os.path.exists("inspection.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(["username", "สายไฟ", "โครงสร้างเสา", "หลอดไฟ", "ออกระบบ"])
    wb.save("inspection.xlsx")

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        wb = load_workbook("users.xlsx")
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == username:
                return "Username already exists!"
        ws.append([username, password])
        wb.save("users.xlsx")
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        wb = load_workbook("users.xlsx")
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == username and row[1] == password:
                session['user'] = username
                return redirect('/dashboard')
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    if request.method == 'POST':
        wire = request.form.get('wire')
        pole = request.form.get('pole')
        light = request.form.get('light')
        wb = load_workbook("inspection.xlsx")
        ws = wb.active
        ws.append([session['user'], wire, pole, light, ""])
        wb.save("inspection.xlsx")
        return "บันทึกข้อมูลเรียบร้อยแล้ว"
    return render_template('dashboard.html', username=session['user'])

@app.route('/logout')
def logout():
    if 'user' in session:
        wb = load_workbook("inspection.xlsx")
        ws = wb.active
        ws.append([session['user'], "", "", "", "ออกระบบ"])
        wb.save("inspection.xlsx")
        session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)