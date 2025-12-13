from flask import render_template, request, redirect, url_for, jsonify, session
from datetime import datetime
import uuid
import os
from app.data_manager import get_user, get_posts_by_author, add_post, get_all_users, remove_post, add_user, load_json, \
    save_json, USERS_PATH, POSTS_PATH, add_comment, delete_comment, can_delete_comment, get_posts, generate_id, \
    react_to_post, react_to_comment, get_user_reaction_to_post, get_user_reaction_to_comment, get_post, valid_pass
from config import Config
from werkzeug.utils import secure_filename

SECRET_CODE = Config.SECRET_KEY
USER_ID = 194679


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def register_routes(app):

    @app.route('/test_session')
    def give_test_session():
        session['test_session'] = "rabotaet"
        return jsonify({"test_session": "rabotaet"})
    @app.route('/admin')
    def admin():
        # просто шаблон для админки
        user_id = session["user_id"]
        if not (user_id and session.get("secret_key") == SECRET_CODE):
            return jsonify({"error": "Not authorized"}), 403
        user = get_user(user_id)
        if not user:
            # будем возвращать 404 типо умные хихих страницы то "нет", а на деле он не админ
            # мудрая маскировка короче
            return 404

    @app.route('/')
    def index():
        return render_template('welcome.html')

    @app.route('/cab')
    def cab():
        user_id = session.get("user_id", None)

        if not (user_id and session.get("secret_key") == SECRET_CODE):
            return redirect("/login")

        user = get_user(user_id)
        if not user:
            return "Пользователь не найден", 404

        posts_user = get_posts_by_author(user_id)
        users = get_all_users()
        return render_template('cab.html',
                                posts=posts_user,
                                posts_len=len(posts_user),
                                rating=user["rating"],
                                created_at=user["created_at"],
                                comments_len=len(user["reacted"]["commented_at"]),
                                ava_path=user["img_path"],
                                name=user["name"],
                                author_user_id=user_id,
                                users=users)
        return 403

    @app.route('/login')
    def login():
        if session.get('user_id'):
            return redirect('/cab')
        return render_template('login.html')

    @app.route('/register')
    def register():
        if session.get('user_id'):
            return redirect('/cab')
        return render_template('register.html')

    @app.route('/graphs')
    def graphs():
        filter_data = {
            'regions': [
                {'id': 'rostov', 'name': 'Ростовская обл.'},
                {'id': 'bryansk', 'name': 'Брянская обл.'},
                {'id': 'belgorod', 'name': 'Белгородская обл.'},
                {'id': 'voronezh', 'name': 'Воронежская обл.'},
                {'id': 'krasnodar', 'name': 'Краснодарский край'}
            ],
            'themes': [
                {'id': 'medical', 'name': 'Медицинские'},
                {'id': 'construction', 'name': 'Строительные'},
                {'id': 'it', 'name': 'IT и связь'},
                {'id': 'education', 'name': 'Образовательные'},
                {'id': 'military', 'name': 'Оборонные (Воен.)'},
                {'id': 'transport', 'name': 'Транспортные'},
                {'id': 'agriculture', 'name': 'Агросельхозные'},
                {'id': 'science', 'name': 'Научные'},
                {'id': 'culture', 'name': 'Культурные'},
                {'id': 'other', 'name': 'Прочие'}
            ],
            'laws': [
                {'id': '44fz', 'name': '44-ФЗ'},
                {'id': '223fz', 'name': '223-ФЗ'},
                {'id': 'pp615', 'name': 'ПП РФ 615'}
            ],
            'price_range': {
                'min': 0,
                'max': 100000,
                'step': 1000
            }
        }

        posts = get_posts()
        users = get_all_users()

        print(posts)
        return render_template('graphics.html',
                               filters=filter_data,
                               posts=posts,
                               users=users,
                               USER_ID=USER_ID)

    # ========== СИСТЕМА КОММЕНТАРИЕВ ==========
    @app.route('/api/add_comment', methods=['POST'])
    def add_comment_route():
        try:
            user_id = session["user_id"]

            if not (user_id and session.get("secret_key") == SECRET_CODE):
                return jsonify({"error": "Not authorized"}), 403
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400
            print(request)
            post_id = data.get("post_id")
            text = data.get("text")
            parent_comm_id = data.get("parent_comm_id")

            print(
                f"DEBUG: Получены данные - post_id: {post_id}, user_id: {user_id}, text: {text}, parent_comm_id: {parent_comm_id}")

            if not post_id:
                return jsonify({"status": "error", "message": "Post ID is required"}), 400
            if not text or not text.strip():
                return jsonify({"status": "error", "message": "Text is required"}), 400
            posts = get_posts()
            post_exists = any(post["id"] == int(post_id) for post in posts)
            if not post_exists:
                return jsonify({"status": "error", "message": f"Post {post_id} not found"}), 404

            comment_id = add_comment(post_id, user_id, text.strip(), parent_comm_id)

            if comment_id:
                return jsonify({"status": "success", "comment_id": comment_id})
            else:
                return jsonify({"status": "error", "message": "Failed to add comment"}), 500

        except Exception as e:
            print(f"Ошибка в add_comment_route: {e}")
            return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

    @app.route('/api/delete_comment', methods=['POST'])
    def delete_comment_route():
        try:
            user_id = session["user_id"]

            if not (user_id and session.get("secret_key") == SECRET_CODE):
                return jsonify({"error": "Not authorized"}), 403
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            post_id = data.get("post_id")
            comment_id = data.get("comment_id")

            print(f"DEBUG: Удаление комментария - post_id: {post_id}, comment_id: {comment_id}")

            if not all([post_id, comment_id]):
                return jsonify({"status": "error", "message": "Missing fields"}), 400

            if not can_delete_comment(user_id, comment_id, post_id):
                return jsonify({"status": "error", "message": "No permission to delete"}), 403

            if delete_comment(post_id, comment_id, user_id):
                return jsonify({"status": "success", "message": "Comment deleted"})
            else:
                return jsonify({"status": "error", "message": "Comment not found"}), 404

        except Exception as e:
            print(f"Ошибка в delete_comment_route: {e}")
            return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

    # ========== СИСТЕМА ЛАЙКОВ/ДИЗЛАЙКОВ ==========
    @app.route('/api/react_post', methods=['POST'])
    def react_post_route():
        try:
            user_id = session["user_id"]

            if not (user_id and session.get("secret_key") == SECRET_CODE):
                return jsonify({"error": "Not authorized"}), 403
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            post_id = data.get("post_id")
            reaction_type = data.get("reaction_type")
            print(post_id, reaction_type)

            print(f"DEBUG: Реакция на пост - post_id: {post_id}, reaction_type: {reaction_type}")

            if not all([post_id, reaction_type]):
                return jsonify({"status": "error", "message": "Missing fields"}), 400

            if reaction_type not in ['up', 'down']:
                return jsonify({"status": "error", "message": "Invalid reaction type"}), 400

            new_rating, user_reaction = react_to_post(user_id, post_id, reaction_type)
            print(f"DEBUG: Результат - new_rating: {new_rating}, user_reaction: {user_reaction}")

            if new_rating is not None:
                return jsonify({
                    "status": "success",
                    "new_rating": new_rating,
                    "user_reaction": user_reaction
                })
            else:
                return jsonify({"status": "error", "message": "Post not found"}), 404

        except Exception as e:
            print(f"Ошибка в react_post_route: {e}")
            return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

    @app.route('/api/react_comment', methods=['POST'])
    def react_comment_route():
        try:
            user_id = session["user_id"]

            if not (user_id and session.get("secret_key") == SECRET_CODE):
                return jsonify({"error": "Not authorized"}), 403
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            post_id = data.get("post_id")
            comment_id = data.get("comment_id")
            reaction_type = data.get("reaction_type")

            print(
                f"DEBUG: Реакция на комментарий - post_id: {post_id}, comment_id: {comment_id}, reaction_type: {reaction_type}")

            if not all([post_id, comment_id, reaction_type]):
                return jsonify({"status": "error", "message": "Missing fields"}), 400

            if reaction_type not in ['up', 'down']:
                return jsonify({"status": "error", "message": "Invalid reaction type"}), 400

            new_rating, user_reaction = react_to_comment(user_id, comment_id, post_id, reaction_type)
            print(f"DEBUG: Результат реакции на комментарий - new_rating: {new_rating}, user_reaction: {user_reaction}")
            from app.data_manager import debug_user_ratings
            debug_user_ratings()

            if new_rating is not None:
                return jsonify({
                    "status": "success",
                    "new_rating": new_rating,
                    "user_reaction": user_reaction
                })
            else:
                return jsonify({"status": "error", "message": "Comment not found"}), 404

        except Exception as e:
            print(f"Ошибка в react_comment_route: {e}")
            return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

    @app.route('/api/get_user_reactions', methods=['POST'])
    def get_user_reactions_route():
        try:
            user_id = session["user_id"]

            if not (user_id and session.get("secret_key") == SECRET_CODE):
                return jsonify({"error": "Not authorized"}), 403
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            post_ids = data.get("post_ids", [])
            comment_data = data.get("comment_data", [])

            print(f"DEBUG: Получено {len(post_ids)} постов и {len(comment_data)} комментариев")

            reactions = {
                "posts": {},
                "comments": {}
            }

            for post_id in post_ids:
                reaction = get_user_reaction_to_post(user_id, post_id)
                reactions["posts"][str(post_id)] = reaction

            for i, comment_info in enumerate(comment_data):
                post_id = comment_info.get("post_id")
                comment_id = comment_info.get("comment_id")
                if post_id and comment_id:
                    reaction = get_user_reaction_to_comment(user_id, comment_id, post_id)
                    key = f"{post_id}_{comment_id}"
                    reactions["comments"][key] = reaction
                    print(
                        f"DEBUG: Комментарий {i + 1}/{len(comment_data)} - post:{post_id}, comment:{comment_id}, reaction:{reaction}")

            print(
                f"DEBUG: Возвращаем реакции - посты: {len(reactions['posts'])}, комментарии: {len(reactions['comments'])}")
            print(reactions)
            return jsonify({
                "status": "success",
                "reactions": reactions
            })

        except Exception as e:
            print(f"Ошибка в get_user_reactions_route: {e}")
            return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

    # ========== СИСТЕМНЫЕ МАРШРУТЫ ==========
    @app.route('/api/upload_avatar', methods=['POST'])
    def upload_avatar():
        try:
            user_id = session["user_id"]

            if not(user_id and session.get("secret_key")==SECRET_CODE):
                return jsonify({"error": "Not authorized"}), 403
            if 'avatar' not in request.files:
                return jsonify({'status': 'error', 'message': 'Файл не найден'})
            file = request.files['avatar']
            if file.filename == '':
                return jsonify({'status': 'error', 'message': 'Файл не выбран'})
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                basedir = os.path.abspath(os.path.dirname(__file__))
                AVA_FOLDER = os.path.join(basedir, "static", "users", "avas")
                os.makedirs(AVA_FOLDER, exist_ok=True)
                file_path = os.path.join(AVA_FOLDER, filename)
                file.save(file_path)
                users = load_json(USERS_PATH)
                if str(user_id) in users:
                    try:
                        old_avatar = users[str(user_id)]['img_path']
                        if old_avatar != "ava.png":
                            old_path = os.path.join(AVA_FOLDER, old_avatar)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                    except Exception as e:
                        print(f"Не удалось удалить старую аватарку: {e}")
                    users[str(user_id)]['img_path'] = filename
                    save_json(USERS_PATH, users)
                    print(f"Аватарка обновлена для пользователя {user_id}")
                else:
                    return jsonify({'status': 'error', 'message': 'Пользователь не найден'})
                return jsonify({
                    'status': 'success',
                    'message': 'Аватарка обновлена',
                    'new_path': filename
                })
            return jsonify({'status': 'error', 'message': 'Недопустимый формат файла'})

        except Exception as e:
            print(f"Ошибка при загрузке аватарки: {e}")
            return jsonify({'status': 'error', 'message': str(e)})

    @app.route('/api/register', methods=["POST"])
    def reg_user():
        try:
            if session.get('user_id') and session["secret_key"]==SECRET_CODE:
                return redirect("/cab")
            username = request.form.get('username')
            password = request.form.get('password')
            if len(password) < 8:
                raise "Некорректный пароль"
            email = request.form.get('email')
            phone = request.form.get('phone')
            subscribed = request.form.get('agree_news')
            file = request.files.get('fileInput')
            basedir = os.path.abspath(os.path.dirname(__file__))
            AVA_FOLDER = os.path.join(basedir, "static", "users", "avas")
            os.makedirs(AVA_FOLDER, exist_ok=True)

            if file and file.filename:
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                save_path = os.path.join(AVA_FOLDER, filename)
                file.save(save_path)
                img_path = filename
                print(f"Файл сохранён: {save_path}")
            else:
                print("Файл не был загружен, используем стандартную аватарку.")
                img_path = "ava.png"

            idishnik = str(generate_id())
            new_user = {
                idishnik: {
                    "name": username,
                    "password": password,
                    "email": email,
                    "phone": phone,
                    "subscribed": subscribed,
                    "rating": 0,
                    "img_path": img_path,
                    "reacted": {
                        "up": [],
                        "down": [],
                        "commented_at": []
                    },
                    "created_at": datetime.utcnow().isoformat()
                }
            }

            add_user(new_user, idishnik)
            session['user_id'] = idishnik
            session["date_created"] = datetime.utcnow().isoformat()
            session["secret_key"] = SECRET_CODE
            return redirect(url_for('cab'))
        except Exception as e:
            print(f"Ошибка при регистрации: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/login', methods=["POST"])
    def login_user():
        try:
            if session.get('user_id') and session["secret_key"]==SECRET_CODE:
                return redirect("/cab")
            email = request.form.get('email')
            password = request.form.get('password')
            print(email, password)
            valid, date, id = valid_pass(email, password)
            if valid:
                session['user_id'] = id
                session['date_created'] = datetime.utcnow().isoformat()
                session["secret_key"] = SECRET_CODE
                return redirect("/cab")
            else:
                return jsonify({"error": "Wrong email or password"}), 403
        except Exception as e:
            print(f"Ошибка входа: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/logout')
    def logout():
        session.clear()
        return redirect("/")
    @app.route('/api/add_post', methods=['POST'])
    def add_post_route():
        try:
            if not session.get('user_id') or session["secret_key"] != SECRET_CODE:
                return jsonify({"error": "Not authorized!"}), 403
            title = request.form.get('title')
            desc = request.form.get('desc')
            file = request.files.get('fileInput')
            print("DEBUG file:", file)
            basedir = os.path.abspath(os.path.dirname(__file__))
            GRAPHS_FOLDER = os.path.join(basedir, "static", "users", "graphs")
            os.makedirs(GRAPHS_FOLDER, exist_ok=True)


            if file and file.filename:
                old_filename = file.filename
                print(old_filename)
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                save_path = os.path.join(GRAPHS_FOLDER, filename)
                file.save(save_path)
                img_path = filename
                print(f"Файл сохранён: {save_path}")
            else:
                print("Файл не был загружен, используем стандартный график.")
                old_filename = 'graph.png'
                img_path = "graph.png"

            new_post = {
                "id": generate_id(),
                "title": title,
                "desc": desc,
                "short_img_path": old_filename,
                "img_path": img_path,
                "rating": 0,
                "author": session.get('user_id'),
                "who_reacted": {"up": [], "down": []},
                "comms": [],
                "created_at": datetime.utcnow().isoformat()
            }

            add_post(new_post)
            return redirect(url_for('cab'))
        except Exception as e:
            print(f"Ошибка при добавлении поста: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/delete_post', methods=["POST"])
    def delete_post():
        try:
            post_id = request.json.get('post_id')

            if not post_id:
                return jsonify({"status": "error", "message": "No post_id provided"}), 400
            if session.get('user_id')==get_post(post_id)["author"] and session["secret_key"]==SECRET_CODE:
                remove_post(post_id)
                return jsonify({"status": "success"})
            else:
                return jsonify({"error": "Not Authorized!"}), 403
        except Exception as e:
            print(f"Ошибка при удалении поста: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
