# CRUD Flask Social

Aplicación web en Flask para subir publicaciones con texto, fotos, videos y audios.

## Requisitos

- Python 3.11+ o Python 3.10
- XAMPP con MySQL activo
- Paquetes Python:
  - flask
  - mysql-connector-python
  - werkzeug

## Instalación

1. Instala los paquetes:

```bash
pip install flask mysql-connector-python werkzeug
```

2. Copia este proyecto en `c:\Users\ale30\Desktop\CRUDFLASK`.

3. Abre `app.py` y configura tu API Key de Google en `app.config['GOOGLE_API_KEY']`.

4. Ajusta la configuración de MySQL si es necesario:

- `app.config['MYSQL_USER']`
- `app.config['MYSQL_PASSWORD']`
- `app.config['MYSQL_HOST']`

5. Ejecuta la app:

```bash
python app.py
```

6. Abre `http://127.0.0.1:5000`.

## Características

- Registro con nombre, correo, contraseña y foto de perfil
- Inicio de sesión con código de 2 factores
- Publicaciones con texto y archivos multimedia
- Comentarios y botones de me gusta
- Perfil editable con modo claro/oscuro
- Panel de administrador para revisar usuarios y borrar publicaciones
- Base de datos MySQL con tablas `users`, `posts`, `comments` y `likes`
