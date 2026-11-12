"""
uvicorn very_first2:app --reload
http://127.0.0.1:8000/register
"""

import hashlib
import json
import os
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile,status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

os.makedirs("static/avatars", exist_ok=True)

USER_FILE = "users.json"

# Функции для работы с файлом пользователей
def load_users():
  if os.path.exists(USER_FILE):
    try:
      with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except json.JSONDecodeError:
      return {}
  return {}

def save_users(users):
  with open(USER_FILE, "w", encoding="utf-8") as f:
    json.dump(users, f, ensure_ascii=False, indent=4)

# Инициализируем базу данных из файла
fake_users_db = load_users()

white_urls = ["/", "/login", "/logout", "/register"]

# @app.get("/", response_class=HTMLResponse)
# def main_page(request: Request):
#   return templates.TemplateResponse(request=request, name="main.html")


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, username: str = None):
  user = None
  if username and username in fake_users_db:
    user = fake_users_db[username]
  elif fake_users_db:
    user = list(fake_users_db.values())[-1]
  
  if not user:
    user = {
        "username": "Гость",
        "avatar": "static/default.png",
        "password_hash": "нет",
    }
  return templates.TemplateResponse(
      request=request, name="home.html", context={"user": user}
  )


# Отображение страницы входа
@app.get("/login", response_class=HTMLResponse)
def login_get_page(request: Request):
  return templates.TemplateResponse(request=request, name="login.html")


# Обработка отправки формы входа: проверка и перенаправление на home
@app.post("/login", response_class=HTMLResponse)
def login_post_page(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
  global fake_users_db
  fake_users_db = load_users()  # Обновляем данные из файла

  if username not in fake_users_db:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Неверный логин или пароль",
            "show_register_link": True
        },
    )

  user_data = fake_users_db[username]
  password_hash = hashlib.sha256(password.encode()).hexdigest()

  # Сверяем хэш введенного пароля с сохраненным
  if user_data["password_hash"] != password_hash:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Неверный логин или пароль",
            "show_register_link": True
        },
    )

  # При успешном входе перенаправляем на home с передачей имени пользователя
  return RedirectResponse(url=f"/home?username={username}", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_get_page(request: Request):
  return templates.TemplateResponse(request=request, name="register.html")


@app.post("/register", response_class=HTMLResponse)
async def register_post_page(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    admin_login: str = Form(...),
    admin_password: str = Form(...),
    avatar: UploadFile = File(None),
):
  global fake_users_db
  fake_users_db = load_users()

  if username in fake_users_db:
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"error": "Пользователь с таким именем уже существует"},
    )

  avatar_path = "static/default.png"
  if avatar and avatar.filename:
    file_location = f"static/avatars/{avatar.filename}"
    with open(file_location, "wb+") as file_object:
      file_object.write(await avatar.read())
    avatar_path = file_location

  password_hash = hashlib.sha256(password.encode()).hexdigest()

  # Сохраняем нового пользователя в словарь
  fake_users_db[username] = {
      "username": username,
      "password_hash": password_hash,
      "avatar": avatar_path,
      "admin_login": admin_login,
  }

  # Записываем обновленный словарь в файл users.json
  save_users(fake_users_db)

  return RedirectResponse(url="/login", status_code=303)


@app.get("/404", response_class=HTMLResponse)
def not_found_page(request: Request):
  return templates.TemplateResponse(request=request, name="404.html", status_code=404)


# Глобальный перехватчик для всех несуществующих страниц (ошибок 404)
@app.exception_handler(404)
def custom_404_handler(request: Request, exc):
  return templates.TemplateResponse(
      request=request, 
      name="404.html", 
      status_code=404
  )