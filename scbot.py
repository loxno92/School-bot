import logging
import datetime
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

ADMIN_ID = 123  # Замените на ID администратора
print(f"Admin ID: {ADMIN_ID}") # Вывод ID админа
TOKEN = ""  # Замените на токен вашего бота

DATABASE_FILE = "data.json"


def load_data():
    try:
        with open(DATABASE_FILE, "r") as f:
            data = json.load(f)
            if "pending_users" in data:
                data["pending_users"] = {int(k): v for k, v in data["pending_users"].items()}
            if "users" in data:
                data["users"] = [int(user) for user in data["users"]]
            return data

    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "users": [],
            "pending_users": {},
            "schedule": {},
            "homework": {},
            "feedback": [],
            "announcements": [],
        }


def save_data(data):
    data_to_save = data.copy()

    if "pending_users" in data_to_save:
        data_to_save["pending_users"] = {str(k): v for k, v in data_to_save["pending_users"].items()}

    with open(DATABASE_FILE, "w") as f:
        json.dump(data_to_save, f, indent=4)


def initialize_admin():
    data = load_data()
    admin_id = 123  # Замените на ID администратора
    if admin_id not in data["users"]:
        data["users"].append(admin_id)
        save_data(data)
        print("Admin user initialized")
    return data


def start(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        print(f"User ID (start): {user_id}")
        data = load_data()
        if user_id in data["users"]:
            keyboard = [
                ["Расписание"],
                ["Домашнее задание"],
                ["Обратная связь"],
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            context.bot.send_message(
                chat_id=user_id, text="Выберите действие:", reply_markup=reply_markup
            )
        elif user_id in data["pending_users"]:
            context.bot.send_message(chat_id=user_id, text="Ваша заявка на регистрацию ожидает рассмотрения.")
        else:
            context.bot.send_message(
                chat_id=user_id,
                text="Привет! Для регистрации, пожалуйста, введите ваше имя и фамилию в формате 'Имя Фамилия':"
            )
            context.user_data['registration_mode'] = True
    except Exception as e:
        logging.error(f"Error in start: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def button(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        if query:
            query.answer()
            action = query.data
        else:
            action = update.message.text
        user_id = update.effective_user.id
        print(f"User ID (button): {user_id}")
        if action == "Расписание":
            show_schedule(update, context)
        elif action == "Домашнее задание":
            show_homework_menu(update, context)
        elif action == "Обратная связь":
            send_feedback(update, context)
        elif action == "approve_user":
            if user_id == ADMIN_ID:
                show_pending_users(update, context)
        elif action.startswith("approve_"):
            if user_id == ADMIN_ID:
                user_to_approve = int(action.split("_")[1])
                approve_user(update, context, user_to_approve)
        elif action == "add_schedule":
            if user_id == ADMIN_ID:
                context.bot.send_message(chat_id=user_id,
                                         text="Введите день недели и расписание в формате 'понедельник:урок1,урок2,...' :")
                context.user_data['add_schedule_data'] = True
                return
        elif action == "add_homework":
            if user_id == ADMIN_ID:
                context.bot.send_message(
                    chat_id=user_id,
                    text="Введите ДЗ в формате 'день_недели:урок:дз'. Например, 'понедельник:математика:стр. 12 упр. 5'",
                )
                context.user_data['add_homework_data'] = True
                return
        elif action == "send_announcement":
            if user_id == ADMIN_ID:
                context.bot.send_message(chat_id=user_id, text="Введите объявление для всех пользователей:")
                context.user_data['announcement_text'] = True
                return
        elif action == 'view_feedback':
            if user_id == ADMIN_ID:
                show_admin_feedback(update, context)
        elif action.startswith("reply_feedback_"):
            if user_id == ADMIN_ID:
                feedback_id = int(action.split("_")[2])
                context.user_data['replying_to'] = feedback_id
                context.bot.send_message(chat_id=user_id, text="Введите ответ:")
                return 'replying_feedback_text'

        elif action == 'admin_menu':
            if user_id == ADMIN_ID:
                show_admin_menu(update, context)
        elif action.startswith("homework_"):
            parts = action.split("_")
            if len(parts) == 2:
                day = parts[1]
                show_homework_by_day(update, context, day)
            elif len(parts) == 3:
                day, lesson = parts[1], parts[2]
                show_homework_by_lesson(update, context, day, lesson)
    except Exception as e:
        logging.error(f"Error in button handler: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def handle_message(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        text = update.message.text
        data = load_data()
        if context.user_data.get('registration_mode'):
            try:
                name, surname = text.split(" ", 1)
                data["pending_users"][int(user_id)] = {  # Сохраняем ID как int
                    'name': name,
                    'surname': surname,
                }
                save_data(data)
                context.bot.send_message(chat_id=user_id, text="Ваша заявка на регистрацию отправлена администратору.")
                context.user_data.pop('registration_mode', None)
            except ValueError:
                context.bot.send_message(chat_id=user_id,
                                         text="Неверный формат. Введите ваше имя и фамилию в формате 'Имя Фамилия'")

        elif context.user_data.get('add_schedule_data'):
            if user_id == ADMIN_ID:
                try:
                    day, schedule_str = text.split(":", 1)
                    lessons = schedule_str.split(",")
                    data["schedule"][day.lower()] = lessons
                    save_data(data)
                    context.bot.send_message(chat_id=user_id, text="Расписание обновлено")
                except ValueError:
                    context.bot.send_message(chat_id=user_id, text="Неверный формат")
                finally:
                    context.user_data.pop('add_schedule_data', None)
        elif context.user_data.get('add_homework_data'):
            if user_id == ADMIN_ID:
                try:
                    day, lesson, homework = text.split(":", 2)
                    data["homework"].setdefault(day.lower(), {})[lesson.lower()] = homework
                    save_data(data)
                    context.bot.send_message(chat_id=user_id, text="Домашнее задание добавлено")
                except ValueError:
                    context.bot.send_message(chat_id=user_id, text="Неверный формат")
                finally:
                    context.user_data.pop('add_homework_data', None)
        elif context.user_data.get('announcement_text'):
            if user_id == ADMIN_ID:
                data["announcements"].append(text)
                save_data(data)
                for user in data["users"]:
                    context.bot.send_message(chat_id=user, text=f"Новое объявление от администратора:\n{text}")
                context.bot.send_message(chat_id=user_id, text="Объявление отправлено")
                context.user_data.pop('announcement_text', None)

        elif context.user_data.get('replying_to'):
            if user_id == ADMIN_ID:
                feedback_id = context.user_data.get('replying_to')
                feedback_item = next((item for item in data['feedback'] if item['id'] == feedback_id), None)
                if feedback_item:
                    user_to_reply = feedback_item['user_id']
                    context.bot.send_message(chat_id=user_to_reply, text=f"Ответ от администратора:\n{text}")
                    context.bot.send_message(chat_id=user_id, text="Ответ отправлен")
                else:
                    context.bot.send_message(chat_id=user_id, text="Сообщение не найдено")
                context.user_data.pop('replying_to', None)

        elif user_id in data["users"] and context.user_data.get('feedback_mode'):
            new_feedback = {
                'id': len(data['feedback']) + 1,
                'user_id': user_id,
                'text': text,
            }
            data["feedback"].append(new_feedback)
            save_data(data)
            context.bot.send_message(chat_id=user_id, text="Сообщение отправлено администратору")
            context.user_data.pop('feedback_mode', None)


        elif user_id in data["users"] and (
                text == "Расписание" or text == "Домашнее задание" or text == "Обратная связь"):
            button(update, context)
    except Exception as e:
        logging.error(f"Error in message handler: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def admin_command(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        if user_id == ADMIN_ID:
            show_admin_menu(update, context)
        else:
            context.bot.send_message(chat_id=user_id, text="У вас нет прав администратора.")
    except Exception as e:
        logging.error(f"Error in admin_command: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def approve_user(update: Update, context: CallbackContext, user_id):
    try:
        data = load_data()
        if update.effective_user.id == ADMIN_ID:
            if int(user_id) in data["pending_users"]:
                data["users"].append(int(user_id))
                name = data["pending_users"][int(user_id)]['name']
                surname = data["pending_users"][int(user_id)]['surname']
                del data["pending_users"][int(user_id)]
                save_data(data)
                context.bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь {name} {surname} одобрен.")
                context.bot.send_message(chat_id=int(user_id),
                                         text="Ваша заявка на регистрацию одобрена! Теперь вам доступны все функции бота.")
            else:
                context.bot.send_message(chat_id=ADMIN_ID, text="Пользователь не найден в списке ожидания.")
    except Exception as e:
        logging.error(f"Error in approve_user: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id,
                                 text="Произошла ошибка при одобрении. Попробуйте позже")


def show_pending_users(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        if user_id == ADMIN_ID:
            data = load_data()
            if not data["pending_users"]:
                context.bot.send_message(chat_id=user_id, text="Нет новых заявок на регистрацию.")
                return

            for user, user_data in data["pending_users"].items():  # user теперь int
                logging.info(f"Pending user ID: {user}, name: {user_data['name']}, surname: {user_data['surname']}")
                keyboard = [
                    [InlineKeyboardButton("Одобрить", callback_data=f"approve_{user}")]]  # callback_data c int user
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"ID: {user}, Имя: {user_data['name']}, Фамилия: {user_data['surname']}",
                    reply_markup=reply_markup
                )
                logging.info(f"Button callback_data: approve_{user}")

            keyboard = [[InlineKeyboardButton("Назад", callback_data="admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(chat_id=user_id, text="Выберите пользователя для одобрения.",
                                     reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error in show_pending_users: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id,
                                 text="Произошла ошибка при выводе ожидающих пользователей. Попробуйте позже")


def show_schedule(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        data = load_data()
        schedule = data["schedule"]
        if not schedule:
            context.bot.send_message(chat_id=user_id, text="Расписание пока не задано.")
            return

        message = "Расписание на неделю:\n"
        for day, lessons in schedule.items():
            message += f"\n{day.capitalize()}:\n"
            for lesson in lessons:
                message += f"- {lesson}\n"
        context.bot.send_message(chat_id=user_id, text=message)
    except Exception as e:
        logging.error(f"Error in show_schedule: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def show_homework_menu(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        keyboard = []
        data = load_data()
        if not data["homework"]:
            context.bot.send_message(chat_id=user_id, text="Домашнее задание пока не задано.")
            return

        keyboard.append([InlineKeyboardButton("Все ДЗ на неделю", callback_data="homework_all")])
        for day in data["homework"].keys():
            keyboard.append([InlineKeyboardButton(f"ДЗ на {day.capitalize()}", callback_data=f"homework_{day}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=user_id, text="Выберите день:", reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error in show_homework_menu: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def show_homework_by_day(update: Update, context: CallbackContext, day):
    try:
        user_id = update.effective_user.id
        data = load_data()
        homework = data["homework"].get(day)
        if not homework:
            context.bot.send_message(chat_id=user_id, text="Нет ДЗ на этот день")
            return
        message = f"Домашнее задание на {day.capitalize()}:\n"
        for lesson, task in homework.items():
            message += f"- {lesson}: {task}\n"

        keyboard = []
        for lesson in homework.keys():
            keyboard.append(
                [InlineKeyboardButton(f"ДЗ по {lesson.capitalize()}", callback_data=f"homework_{day}_{lesson}")])

        keyboard.append([InlineKeyboardButton("Назад", callback_data='homework')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error in show_homework_by_day: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def show_homework_by_lesson(update: Update, context: CallbackContext, day, lesson):
    try:
        user_id = update.effective_user.id
        data = load_data()
        homework = data["homework"].get(day, {}).get(lesson)
        if not homework:
            context.bot.send_message(chat_id=user_id, text="Нет такого дз")
            return
        message = f"ДЗ на {day.capitalize()} по {lesson.capitalize()}:\n{homework}"
        keyboard = [[InlineKeyboardButton("Назад", callback_data=f'homework_{day}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error in show_homework_by_lesson: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def send_feedback(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        context.bot.send_message(
            chat_id=user_id, text="Напишите ваше сообщение для администратора:"
        )
        context.user_data['feedback_mode'] = True
    except Exception as e:
        logging.error(f"Error in send_feedback: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def show_admin_menu(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        if user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("Одобрить заявки", callback_data="approve_user")],
                [InlineKeyboardButton("Добавить расписание", callback_data="add_schedule")],
                [InlineKeyboardButton("Добавить ДЗ", callback_data="add_homework")],
                [InlineKeyboardButton("Отправить объявление", callback_data="send_announcement")],
                [InlineKeyboardButton("Просмотреть обратную связь", callback_data="view_feedback")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=user_id, text="Админ панель:", reply_markup=reply_markup
            )
        else:
            context.bot.send_message(chat_id=user_id, text="У вас нет прав администратора.")
    except Exception as e:
        logging.error(f"Error in show_admin_menu: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def show_admin_feedback(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        if user_id == ADMIN_ID:
            data = load_data()
            if not data['feedback']:
                context.bot.send_message(chat_id=user_id, text="Нет обратной связи")
                return

            for item in data['feedback']:
                keyboard = [[InlineKeyboardButton("Ответить", callback_data=f"reply_feedback_{item['id']}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(chat_id=user_id,
                                         text=f"ID: {item['id']}\nСообщение от {item['user_id']}:\n{item['text']}",
                                         reply_markup=reply_markup)

            keyboard = [[InlineKeyboardButton("Назад", callback_data="admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(chat_id=user_id, text="Выберите сообщение для ответа", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error in show_admin_feedback: {e}", exc_info=True)
        context.bot.send_message(chat_id=update.effective_user.id, text="Произошла ошибка. Попробуйте позже")


def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler("admin", admin_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    data = initialize_admin()

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
