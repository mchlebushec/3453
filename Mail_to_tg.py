import imaplib
import email
from email.header import decode_header
import time
import requests
from bs4 import BeautifulSoup

# --- КОНФИГ ---

IMAP_SERVER = 'imap.mail.ru'  # сервер почты(IMAP)
IMAP_PORT = 993  # Порт(IMAP)

MAIL_USERNAME = 'ultra.all@mail.ru'  # Почта
MAIL_PASSWORD = '5ssrR7nI4tV1F6byHGkK'  # Пароль от почты(IMAP)

MAIL_FOLDER = 'Zakaz sayt'  # Имя папки

TELEGRAM_BOT_TOKEN = '8069056826:AAHwdG7ikDBlqZpfn3Rmy9cPXu4U6bHCAOw'  # ID бота
TELEGRAM_CHAT_ID = '-1002567442319'  # ID группы, куда отправлять

POLL_INTERVAL = 60  # проверять почту каждую минуту

def clean_text(text):
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            return text.decode('latin1')
    return text

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_payload(decode=True)
                return clean_text(body)
    else:
        body = msg.get_payload(decode=True)
        return clean_text(body)
    return ""

def extract_parts_from_text(text):
    lines = text.splitlines()
    def safe_cut(i, pos, suffix=''):
        if len(lines) > i:
            line = lines[i]
            return line[pos:] + suffix if len(line) > pos else suffix.strip()
        return suffix.strip()

    # Выделение нужной части сообщения
    parts = [
        safe_cut(1, 14),
        safe_cut(2, 40),
        safe_cut(3, 67),
        safe_cut(4, 13),
        safe_cut(6, 20, ' чел.')
    ]
    return '\n'.join(parts)  # Если нужно будет через запятую, изменить /n на ,

def send_telegram_message(token, chat_id, message):
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': message,
    }
    response = requests.post(url, data=data)
    try:
        resp_json = response.json()
    except Exception:
        resp_json = {'error': 'cannot parse json response'}
    print('Ответ Telegram API:', resp_json)
    return response.ok

# Выбор папки
def process_mail():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(MAIL_USERNAME, MAIL_PASSWORD)
        mail.select(f'"{MAIL_FOLDER}"')

        # Уведомление о ошибке
        status, messages = mail.search(None, '(UNSEEN)')
        if status != 'OK':
            print('Не удалось получить письма')
            return

        # Уведомление о новом письме
        mail_ids = messages[0].split()
        print(f'Найдено {len(mail_ids)} новых писем в "{MAIL_FOLDER}".')

        # Уведомление о ошибке
        for mail_id in mail_ids:
            status, msg_data = mail.fetch(mail_id, '(RFC822)')
            if status != 'OK':
                print(f'Не удалось получить письмо id {mail_id}')
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    subject, encoding = decode_header(msg.get('Subject'))[0]
                    if isinstance(subject, bytes):
                        try:
                            subject = subject.decode(encoding or 'utf-8')
                        except Exception:
                            subject = subject.decode('latin1')
                    from_ = msg.get('From')

                    body = get_email_body(msg)  # Получаем тело письма

                    print(body)

                    extracted_text = extract_parts_from_text(body)

                    message = f'{extracted_text}'

                    sent = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
                    if sent:
                        print(f'Отправлено сообщение для письма id {mail_id.decode()}')
                    else:
                        print(f'Ошибка отправки для письма id {mail_id.decode()}')

        mail.logout()

    except Exception as e:
        print('Ошибка при обработке почты:', e)

def main():
    print('Запуск пересылки писем в телеграм...')
    while True:
        process_mail()
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
