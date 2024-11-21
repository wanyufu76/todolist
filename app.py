from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import io
from flask import send_file

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    todos = db.relationship('Todo', backref='user', lazy=True)

# Todo Model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)  # 新增 due_date 欄位
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Index Page - Show Todos
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    todos = Todo.query.filter_by(user_id=session['user_id']).order_by(Todo.date_created).all()
    return render_template('index.html', todos=todos)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('使用者名稱已存在')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('註冊成功，請登入')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('使用者名稱或密碼錯誤，或是帳號未註冊')
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Add Todo
@app.route('/add', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    due_date_str = request.form.get('due_date')
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
    new_todo = Todo(content=content, due_date=due_date, user_id=session['user_id'])
    db.session.add(new_todo)
    db.session.commit()
    return redirect(url_for('index'))

# Delete Todo
@app.route('/delete/<int:id>')
def delete_todo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    todo_to_delete = Todo.query.get_or_404(id)
    if todo_to_delete.user_id != session['user_id']:
        flash('無權限刪除此項目')
        return redirect(url_for('index'))
    db.session.delete(todo_to_delete)
    db.session.commit()
    return redirect(url_for('index'))

# Complete Todo
@app.route('/complete/<int:id>')
def complete_todo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    todo = Todo.query.get_or_404(id)
    if todo.user_id != session['user_id']:
        flash('無權限更新此項目')
        return redirect(url_for('index'))
    todo.completed = not todo.completed
    db.session.commit()
    return redirect(url_for('index'))

from flask import send_file

@app.route('/export')
def export():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 查詢該使用者的所有待辦事項，並格式化資料
    todos = Todo.query.filter_by(user_id=session['user_id']).order_by(Todo.date_created).all()
    data = [{
        '日期': todo.due_date.strftime('%Y-%m-%d') if todo.due_date else '',  # 使用到期日期
        '待辦事項': todo.content,
        '完成狀態': '已完成' if todo.completed else '未完成'
    } for todo in todos]

    # 將資料轉換為 DataFrame
    df = pd.DataFrame(data)
    output = io.BytesIO()

    # 使用 ExcelWriter 寫入 Excel，移除 writer.save()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='待辦事項')

    output.seek(0)  # 將游標設置到文件開頭

    # 傳送 Excel 文件
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name='todos.xlsx',
        as_attachment=True
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
