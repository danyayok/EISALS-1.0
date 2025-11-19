import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_PATH = DATA_DIR / "users.json"
POSTS_PATH = DATA_DIR / "posts.json"

_used_ids = set()

def debug_user_ratings():
    users = load_json(USERS_PATH)
    print(f"=== DEBUG: Рейтинги пользователей ===")
    for user_id, user_data in users.items():
        print(f"Пользователь {user_id}: {user_data.get('name')} - Рейтинг: {user_data.get('rating')}")
    print("=== DEBUG END ===")


def _load_used_ids():
    global _used_ids
    _used_ids.clear()

    try:
        users = load_json(USERS_PATH)
        for user_id in users.keys():
            _used_ids.add(int(user_id))

        posts = load_json(POSTS_PATH)
        for post in posts:
            _used_ids.add(post["id"])
            if post.get("comms"):
                for comment in post["comms"]:
                    _used_ids.add(comment["id"])
                    if comment.get("comms"):
                        for sub_comment in comment["comms"]:
                            _used_ids.add(sub_comment["id"])

        print(f"DEBUG: Загружено {len(_used_ids)} занятых ID")
    except Exception as e:
        print(f"Ошибка при загрузке ID: {e}")
        _used_ids = set()

def generate_id():
    global _used_ids
    if not _used_ids:
        _load_used_ids()

    max_attempts = 1000
    for _ in range(max_attempts):
        new_id = random.randint(100000, 999999)
        if new_id not in _used_ids:
            _used_ids.add(new_id)
            return new_id

    for _ in range(max_attempts):
        new_id = random.randint(1000000, 9999999)
        if new_id not in _used_ids:
            _used_ids.add(new_id)
            return new_id

    raise Exception("Не удалось сгенерировать уникальный ID")

def load_json(path):
    try:
        if not path.exists():
            return {} if path.name == "users.json" else []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки {path}: {e}")
        return {} if path.name == "users.json" else []

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения {path}: {e}")
        raise

# ========== СИСТЕМА КОММЕНТАРИЕВ ==========

def add_comment(post_id, user_id, text, parent_comm_id=None):
    try:
        posts = load_json(POSTS_PATH)
        users = load_json(USERS_PATH)
        post_id = int(post_id)
        user_id = int(user_id)

        print(f"DEBUG: Добавление комментария к посту {post_id}, parent: {parent_comm_id}")

        for post in posts:
            if post["id"] == post_id:
                comment_id = generate_id()
                new_comment = {
                    "id": comment_id,
                    "user": user_id,
                    "text": text,
                    "rating": 0,
                    "who_reacted": {"up": [], "down": []},
                    "comms": []
                }

                if parent_comm_id:
                    parent_comm_id = int(parent_comm_id)
                    # из-за того что последний return False находился в for я час не мог понять
                    # почему даёт инфу ток о первой ветке коммов, пока не заметил пробел
                    def check_comments(comments, target_id):
                        for comment in comments:
                            if comment["id"] == target_id:
                                comment["comms"].append(new_comment)
                                return True
                            if "comms" in comment and comment["comms"]:
                                result = check_comments(comment["comms"], target_id)
                                if result:
                                    return result
                        return False
                    result = check_comments(post["comms"], parent_comm_id)
                    if not result:
                        print(f"DEBUG: Родительский комментарий {parent_comm_id} не найден")
                        return None
                else:
                    if "comms" not in post:
                        post["comms"] = []
                    post["comms"].append(new_comment)

                # ообновляет счетчик комментариев пользователя
                if str(user_id) in users:
                    if post_id not in users[str(user_id)]["reacted"]["commented_at"]:
                        users[str(user_id)]["reacted"]["commented_at"].append(comment_id)

                save_json(USERS_PATH, users)
                save_json(POSTS_PATH, posts)
                _load_used_ids()

                print(f"DEBUG: Комментарий добавлен с ID {comment_id}")
                return comment_id
        print(f"DEBUG: Пост {post_id} не найден")
        return None
    except Exception as e:
        print(f"Ошибка в add_comment: {e}")
        return None

def delete_comment(post_id, comment_id, user_id):
    try:
        posts = load_json(POSTS_PATH)
        users = load_json(USERS_PATH)
        post_id = int(post_id)
        comment_id = int(comment_id)

        for post in posts:
            if post["id"] == post_id:
                # вообще я этот гений инженерии ввиде рекурсивной функции почти везде использую
                # т.к. сделал умные комменты с возможность вставить вложенные комменты бесконечно
                def check_comments(comments, target_id):
                    for comment in comments:
                        if comment["id"] == target_id:
                            print("Deletion if")
                            comments.remove(comment)
                            return True
                        if "comms" in comment and comment["comms"]:
                            result = check_comments(comment["comms"], target_id)
                            if result:
                                return result
                    return False
                result = check_comments(post["comms"], comment_id)
                if result:
                    if str(user_id) in users:
                        if post_id not in users[str(user_id)]["reacted"]["commented_at"]:
                            users[str(user_id)]["reacted"]["commented_at"].remove(comment_id)
                    save_json(USERS_PATH, users)
                    save_json(POSTS_PATH, posts)
                    _load_used_ids()
                    print(f"DEBUG: Комментарий добавлен с ID {comment_id}")
                    return result
                print(f"DEBUG: комментарий {comment_id} не найден")
                return None
        return False
    except Exception as e:
        print(f"Ошибка в delete_comment: {e}")
        return False

def can_delete_comment(user_id, comment_id, post_id):
    try:
        posts = load_json(POSTS_PATH)
        post_id = int(post_id)
        comment_id = int(comment_id)
        user_id = int(user_id)
        for post in posts:
            if post["id"] == post_id:
                def check_comments(comments, target_id):
                    for comment in comments:
                        if comment["id"] == target_id:
                            return True, comment["user"]
                        if "comms" in comment and comment["comms"]:
                            result, author = check_comments(comment["comms"], target_id)
                            if result:
                                return result, author
                    return False, None
                result, comment_author = check_comments(post.get("comms", []), comment_id)
                if result:
                    return comment_author == user_id or post["author"] == user_id
        return False
    except Exception as e:
        print(f"Ошибка в can_delete_comment: {e}")
        return False

# ========== СИСТЕМА ЛАЙКОВ/ДИЗЛАЙКОВ ==========

def redact_user_rating(user_id, rate):
    try:
        users = load_json(USERS_PATH)
        if str(user_id) in users:
            users[str(user_id)]["rating"] += rate
            save_json(USERS_PATH, users)
            return True
        return False
    except Exception as e:
        print(f"Ошибка в redact_user_rating: {e}")
        return False

def react_to_post(user_id, post_id, reaction_type):
    try:
        posts = load_json(POSTS_PATH)
        user_id = int(user_id)
        post_id = int(post_id)

        for post in posts:
            if post["id"] == post_id:
                current_rating = post["rating"]
                author_id = post["author"]

                currently_up = user_id in post["who_reacted"]["up"]
                currently_down = user_id in post["who_reacted"]["down"]

                if reaction_type == 'up':
                    if currently_up:
                        # Убираем лайк
                        post["who_reacted"]["up"].remove(user_id)
                        current_rating -= 1
                        redact_user_rating(author_id, -1)
                        user_reaction = None
                    else:
                        # Ставим лайк
                        if currently_down:
                            post["who_reacted"]["down"].remove(user_id)
                            current_rating += 1
                            redact_user_rating(author_id, 1)
                        post["who_reacted"]["up"].append(user_id)
                        current_rating += 1
                        redact_user_rating(author_id, 1)
                        user_reaction = 'up'
                else:
                    if currently_down:
                        # Убираем дизлайк
                        post["who_reacted"]["down"].remove(user_id)
                        current_rating += 1
                        redact_user_rating(author_id, 1)
                        user_reaction = None
                    else:
                        # Ставим дизлайк
                        if currently_up:
                            post["who_reacted"]["up"].remove(user_id)
                            current_rating -= 1
                            redact_user_rating(author_id, -1)
                        post["who_reacted"]["down"].append(user_id)
                        current_rating -= 1
                        redact_user_rating(author_id, -1)
                        user_reaction = 'down'

                post["rating"] = current_rating
                save_json(POSTS_PATH, posts)

                users = load_json(USERS_PATH)
                if str(user_id) in users:
                    user_reacted = users[str(user_id)]["reacted"]

                    if user_reaction == 'up':
                        if post_id not in user_reacted["up"]:
                            user_reacted["up"].append(post_id)
                        if post_id in user_reacted["down"]:
                            user_reacted["down"].remove(post_id)
                    elif user_reaction == 'down':
                        if post_id not in user_reacted["down"]:
                            user_reacted["down"].append(post_id)
                        if post_id in user_reacted["up"]:
                            user_reacted["up"].remove(post_id)
                    else:
                        if post_id in user_reacted["up"]:
                            user_reacted["up"].remove(post_id)
                        if post_id in user_reacted["down"]:
                            user_reacted["down"].remove(post_id)

                    save_json(USERS_PATH, users)

                return current_rating, user_reaction

        return None, None
    except Exception as e:
        print(f"Ошибка в react_to_post: {e}")
        return None, None

def react_to_comment(user_id, comment_id, post_id, reaction_type):
    try:
        posts = load_json(POSTS_PATH)
        users = load_json(USERS_PATH)
        user_id = int(user_id)
        comment_id = int(comment_id)
        post_id = int(post_id)

        print(f"DEBUG: Реакция на комментарий - post_id: {post_id}, comment_id: {comment_id}, reaction_type: {reaction_type}")

        for post in posts:
            if post["id"] == post_id:
                print(f"DEBUG: Пост {post_id} найден, ищем комментарий {comment_id}")
                def check_comments(comments, target_id):
                    for comment in comments:
                        if comment["id"] == target_id:
                            return True, comment["user"], comment
                        if "comms" in comment and comment["comms"]:
                            result, author, comment = check_comments(comment["comms"], target_id)
                            if result:
                                return result, author, comment
                    return False, None, None
                result, comment_author, comment = check_comments(post.get("comms", []), comment_id)
                if result:
                    return _process_comment_reaction(comment, user_id, comment_author, reaction_type, posts, users)
                break

        print(f"DEBUG: Комментарий {comment_id} не найден в посте {post_id}")
        return None, None
    except Exception as e:
        print(f"Ошибка в react_to_comment: {e}")
        return None, None

def _process_comment_reaction(comment, user_id, author_id, reaction_type, posts, users):
    try:
        if "who_reacted" not in comment:
            comment["who_reacted"] = {"up": [], "down": []}

        current_rating = comment.get("rating", 0)

        currently_up = user_id in comment["who_reacted"]["up"]
        currently_down = user_id in comment["who_reacted"]["down"]

        print(f"DEBUG: Текущее состояние комментария - up: {currently_up}, down: {currently_down}, rating: {current_rating}")
        print(f"DEBUG: Автор комментария: {author_id}")

        if reaction_type == 'up':
            if currently_up:
                # Убираем лайк
                comment["who_reacted"]["up"].remove(user_id)
                current_rating -= 1
                redact_user_rating(author_id, -1)
                user_reaction = None
                print("DEBUG: Убран лайк с комментария")
            else:
                # Ставим лайк
                if currently_down:
                    comment["who_reacted"]["down"].remove(user_id)
                    current_rating += 1
                    redact_user_rating(author_id, 1)
                    print("DEBUG: Убран дизлайк с комментария перед установкой лайка")
                comment["who_reacted"]["up"].append(user_id)
                current_rating += 1
                redact_user_rating(author_id, 1)
                user_reaction = 'up'
                print("DEBUG: Установлен лайк на комментарий")
        else:
            if currently_down:
                # Убираем дизлайк
                comment["who_reacted"]["down"].remove(user_id)
                current_rating += 1
                redact_user_rating(author_id, 1)
                user_reaction = None
                print("DEBUG: Убран дизлайк с комментария")
            else:
                # Ставим дизлайк
                if currently_up:
                    comment["who_reacted"]["up"].remove(user_id)
                    current_rating -= 1
                    redact_user_rating(author_id, -1)
                    print("DEBUG: Убран лайк с комментария перед установкой дизлайка")
                comment["who_reacted"]["down"].append(user_id)
                current_rating -= 1
                redact_user_rating(author_id, -1)
                user_reaction = 'down'
                print("DEBUG: Установлен дизлайк на комментарий")

        comment["rating"] = current_rating
        print(f"DEBUG: Новый рейтинг комментария: {current_rating}")

        save_json(POSTS_PATH, posts)

        return current_rating, user_reaction
    except Exception as e:
        print(f"Ошибка в _process_comment_reaction: {e}")
        return None, None

def get_user_reaction_to_post(user_id, post_id):
    try:
        posts = load_json(POSTS_PATH)
        user_id = int(user_id)
        post_id = int(post_id)

        for post in posts:
            if post["id"] == post_id:
                if user_id in post["who_reacted"]["up"]:
                    return "up"
                elif user_id in post["who_reacted"]["down"]:
                    return "down"
        return None
    except Exception as e:
        print(f"Ошибка в get_user_reaction_to_post: {e}")
        return None

def get_user_reaction_to_comment(user_id, comment_id, post_id):
    try:
        posts = load_json(POSTS_PATH)
        user_id = int(user_id)
        comment_id = int(comment_id)
        post_id = int(post_id)

        for post in posts:
            if post["id"] == post_id:
                def check_comments(comments, target_id):
                    for comment in comments:
                        if comment["id"] == target_id:
                            return comment
                        if "comms" in comment and comment["comms"]:
                            result = check_comments(comment["comms"], target_id)
                            if result:
                                return result
                    return None
                comment = check_comments(post["comms"], comment_id)
                if comment:
                    if user_id in comment["who_reacted"]["up"]:
                        return "up"
                    elif user_id in comment["who_reacted"]["down"]:
                        return "down"
        return None
    except Exception as e:
        print(f"Ошибка в get_user_reaction_to_comment: {e}")
        return None

def get_user_comments_count(user_id):
    try:
        posts = load_json(POSTS_PATH)
        user_id = int(user_id)
        count = 0

        for post in posts:
            for comment in post.get("comms", []):
                if comment["user"] == user_id:
                    count += 1
                for sub_comment in comment.get("comms", []):
                    if sub_comment["user"] == user_id:
                        count += 1

        return count
    except Exception as e:
        print(f"Ошибка в get_user_comments_count: {e}")
        return 0

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========

def get_user(user_id: int):
    users = load_json(USERS_PATH)
    return users.get(str(user_id))

def get_all_users():
    users = load_json(USERS_PATH)
    return {int(k): v for k, v in users.items()}

def add_user(user_data: dict, user_id: int):
    users = load_json(USERS_PATH)
    users[str(user_id)] = user_data[str(user_id)]
    save_json(USERS_PATH, users)
    _load_used_ids()

def remove_post(post_id: int):
    posts = load_json(POSTS_PATH)
    postiki = []
    for post in posts:
        if post["id"] != post_id:
            postiki.append(post)
    save_json(POSTS_PATH, postiki)
    _load_used_ids()

def get_posts():
    return load_json(POSTS_PATH)

def get_posts_by_author(author_id: int):
    posts = load_json(POSTS_PATH)
    return [p for p in posts if p["author"] == author_id]

def add_post(post_data: dict):
    posts = load_json(POSTS_PATH)
    posts.append(post_data)
    save_json(POSTS_PATH, posts)
    _load_used_ids()

_load_used_ids()
print("✅ Система уникальных ID инициализирована")