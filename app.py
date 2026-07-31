from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import random
import string
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'cambiar_por_una_clave_segura'
app.permanent_session_lifetime = timedelta(days=7)

# Configuración MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'crudflask'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['PROFILE_FOLDER'] = os.path.join(app.root_path, 'static', 'profile_pics')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['GOOGLE_API_KEY'] = ''  # Pega tu API Key aquí

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MEDIA_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mp3', 'wav', 'ogg'}


def get_db_connection(use_database=True):
    config = {
        'host': app.config['MYSQL_HOST'],
        'user': app.config['MYSQL_USER'],
        'password': app.config['MYSQL_PASSWORD'],
    }
    if use_database:
        config['database'] = app.config['MYSQL_DB']
    return mysql.connector.connect(**config)


def ensure_database():
    conn = get_db_connection(use_database=False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{app.config['MYSQL_DB']}` DEFAULT CHARACTER SET utf8mb4")
    conn.commit()
    cur.close()
    conn.close()


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def get_user_by_email(email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, email, password_hash, is_admin, profile_pic, two_factor_code FROM users WHERE email=%s', (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            profile_pic VARCHAR(255),
            two_factor_code VARCHAR(10),
            theme VARCHAR(10) DEFAULT 'light'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255),
            body TEXT,
            media_filename VARCHAR(255),
            media_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            post_id INT NOT NULL,
            user_id INT NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            post_id INT NOT NULL,
            user_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_like (post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ''')
    conn.commit()
    cur.close()
    conn.close()


def initialize_database():
    ensure_database()
    create_tables()


@app.route('/')
def home():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute('''
        SELECT p.id, p.title, p.body, p.media_filename, p.media_type, p.created_at,
               u.name AS author_name, u.profile_pic AS author_pic,
               (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS likes_count
        FROM posts p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.created_at DESC
    ''')
    posts = cur.fetchall()
    cur.close()
    conn.close()

    theme = session.get('theme', 'light')
    return render_template('home.html', posts=posts, theme=theme)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        profile_pic = request.files.get('profile_pic')

        if not name or not email or not password:
            flash('Todos los campos obligatorios deben completarse.', 'error')
            return redirect(url_for('register'))

        if profile_pic and allowed_file(profile_pic.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
        else:
            filename = None

        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (name, email, password_hash, profile_pic) VALUES (%s, %s, %s, %s)',
                        (name, email, password_hash, filename))
            conn.commit()
            flash('Registro exitoso. Inicia sesión con tu correo y contraseña.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash('Error al crear usuario: {}'.format(e), 'error')
            return redirect(url_for('register'))
        finally:
            cur.close()
            conn.close()

    theme = session.get('theme', 'light')
    return render_template('register.html', theme=theme)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = get_user_by_email(email)
        if user and check_password_hash(user[3], password):
            code = generate_code()
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE users SET two_factor_code=%s WHERE id=%s', (code, user[0]))
            conn.commit()
            cur.close()
            conn.close()
            session['two_factor_user'] = user[0]
            session['two_factor_email'] = email
            flash('Introduce el código de dos factores enviado a tu correo.', 'info')
            return redirect(url_for('two_factor'))

        flash('Correo o contraseña incorrectos.', 'error')
        return redirect(url_for('login'))

    theme = session.get('theme', 'light')
    return render_template('login.html', theme=theme, api_key=app.config['GOOGLE_API_KEY'])


@app.route('/two_factor', methods=['GET', 'POST'])
def two_factor():
    if request.method == 'POST':
        code = request.form['2fa_code']
        user_id = session.get('two_factor_user')
        if not user_id:
            flash('Sesión de dos factores expirada. Vuelve a iniciar sesión.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT two_factor_code, is_admin FROM users WHERE id=%s', (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and user[0] == code:
            session.pop('two_factor_user', None)
            session.pop('two_factor_email', None)
            session['user_id'] = user_id
            session['is_admin'] = bool(user[1])
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('home'))

        flash('Código de dos factores incorrecto.', 'error')
        return redirect(url_for('two_factor'))

    theme = session.get('theme', 'light')
    return render_template('two_factor.html', theme=theme)


@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT name, email, profile_pic, theme FROM users WHERE id=%s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        profile_pic = request.files.get('profile_pic')
        theme = request.form.get('theme', 'light')

        filename = user['profile_pic']
        if profile_pic and allowed_file(profile_pic.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['PROFILE_FOLDER'], filename))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE users SET name=%s, email=%s, profile_pic=%s, theme=%s WHERE id=%s',
                    (name, email, filename, theme, user_id))
        conn.commit()
        cur.close()
        conn.close()
        session['theme'] = theme
        flash('Perfil actualizado.', 'success')
        return redirect(url_for('profile'))

    theme = session.get('theme', user['theme'] if user else 'light')
    return render_template('profile.html', user=user, theme=theme)


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute('''
        SELECT p.id, p.title, p.body, p.media_filename, p.media_type, p.created_at,
               u.name AS author_name, u.profile_pic AS author_pic
        FROM posts p
        JOIN users u ON u.id = p.user_id
        WHERE p.id = %s
    ''', (post_id,))
    post = cur.fetchone()

    cur.execute('''
        SELECT c.id, c.content, c.created_at, u.name AS commenter_name, u.profile_pic AS commenter_pic
        FROM comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.post_id = %s
        ORDER BY c.created_at ASC
    ''', (post_id,))
    comments = cur.fetchall()
    cur.close()
    conn.close()

    theme = session.get('theme', 'light')
    return render_template('post.html', post=post, comments=comments, theme=theme)


@app.route('/create_post', methods=['POST'])
def create_post():
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para publicar.', 'error')
        return redirect(url_for('login'))

    title = request.form.get('title')
    body = request.form.get('body')
    media = request.files.get('media')
    media_filename = None
    media_type = None

    if media and allowed_file(media.filename, ALLOWED_MEDIA_EXTENSIONS):
        media_filename = secure_filename(media.filename)
        media_type = media.mimetype
        media.save(os.path.join(app.config['UPLOAD_FOLDER'], media_filename))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO posts (user_id, title, body, media_filename, media_type) VALUES (%s, %s, %s, %s, %s)',
                (user_id, title, body, media_filename, media_type))
    conn.commit()
    cur.close()
    conn.close()
    flash('Publicación creada.', 'success')
    return redirect(url_for('home'))


@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para comentar.', 'error')
        return redirect(url_for('login'))

    content = request.form.get('content')
    if content:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)',
                    (post_id, user_id, content))
        conn.commit()
        cur.close()
        conn.close()
        flash('Comentario agregado.', 'success')

    return redirect(url_for('view_post', post_id=post_id))


@app.route('/like/<int:post_id>')
def like(post_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para dar me gusta.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO likes (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('home'))


@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, email, is_admin FROM users ORDER BY name')
    users = cur.fetchall()
    cur.execute('''
        SELECT p.id, p.title, p.created_at, u.name AS author_name
        FROM posts p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.created_at DESC
    ''')
    posts = cur.fetchall()
    cur.close()
    conn.close()

    theme = session.get('theme', 'light')
    return render_template('admin.html', users=users, posts=posts, theme=theme)


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, email, is_admin FROM users WHERE id=%s', (user_id,))
    user = cur.fetchone()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form.get('password')
        is_admin = bool(request.form.get('is_admin'))
        if password:
            password_hash = generate_password_hash(password)
            cur.execute('UPDATE users SET name=%s, email=%s, password_hash=%s, is_admin=%s WHERE id=%s',
                        (name, email, password_hash, is_admin, user_id))
        else:
            cur.execute('UPDATE users SET name=%s, email=%s, is_admin=%s WHERE id=%s',
                        (name, email, is_admin, user_id))
        conn.commit()
        flash('Usuario actualizado.', 'success')
        return redirect(url_for('admin_dashboard'))

    cur.close()
    conn.close()
    theme = session.get('theme', 'light')
    return render_template('admin_edit_user.html', user=user, theme=theme)


@app.route('/admin/delete_post/<int:post_id>')
def admin_delete_post(post_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM posts WHERE id=%s', (post_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Publicación eliminada.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    # Inicializar base de datos antes de arrancar (compatible con distintas versiones de Flask)
    ensure_database()
    create_tables()
    app.run(debug=True)
