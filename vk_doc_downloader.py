from pathlib import Path
import requests
from requests import Session
from sys import stdout
import re
import json

DOC_URL_RE = re.compile(r'"docUrl"\s*:\s*("(?:[^"\\]|\\.)*")')
HREF_RE = re.compile(r'docs_no_preview_download_btn_container.*?href="([^"]+)"', re.S)

def extract_direct_url(page: bytes):
    '''
    Достаём прямую ссылку на файл из HTML-заглушки VK
    '''
    # Страница в cp1251, но ссылка ASCII, поэтому кодировка не важна
    text = page.decode('utf-8', errors='ignore')
    match = DOC_URL_RE.search(text)
    if match:
        return json.loads(match.group(1))  # json.loads снимает экранирование \/
    match = HREF_RE.search(text)
    return match.group(1) if match else None


def get_response_without_stubs(session, doc):
    '''
    Возвращает ответ с реальным файлом, проходя через заглушки VK
    '''
    url = doc['url']
    is_html_doc = doc.get('ext', '').lower() in ('.html', '.htm')

    for _ in range(3):
        response = session.get(url, stream=True, timeout=(10, 60))
        response.raise_for_status()
        content_type = response.headers.get('content-type', '').lower()

        if is_html_doc or 'text/html' not in content_type:
            return response  # это настоящий файл

        page = response.content
        url = extract_direct_url(page)
        if not url:
            raise Exception('Пришла заглушка VK, ссылку на файл найти не удалось')

    raise Exception('Слишком много заглушек подряд')


def get_docs(token: str):
    '''
    Получаем список документов из ВК в виде json
    '''
    try: 
        response = requests.post(f'https://api.vk.ru/method/docs.get', params={'v': '5.199', 'access_token': token})
        docs = response.json()['response']['items']
    except Exception:
        try:
            error = response.json()['error']
            print(error['error_msg'])
            if error['error_code'] == 5 or error['error_code'] == 15:
                print('Вставьте валидный токен, его можно получить через https://vkhost.github.io/')
        except KeyError:
            return None
        return None
    return docs


def save_docs(documents : list[dict], save_path: Path | None = None, only_extetions: list[str] | None = None):
    '''
    Скачиваем и сохраняем документы в папку
    '''
    if not documents:
        return
    
    # Сохранять в папку рядом, если не указано явно
    if save_path is None:
        save_path = Path(__file__).parent / 'savefolder'
    else:
        save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)

    # Если doc_types не указан, скачиваются все файлы
    if only_extetions:
        docs_with_selected_types = [doc for doc in documents if doc.get("ext") in only_extetions]
        documents = docs_with_selected_types

    session = requests.session()
    doc_count = len(documents)
    downloaded = 0
    crushed = []
    for doc in documents:
        show_download_progress(downloaded, doc_count, crushed)
        try:
            download_doc(session, doc, save_path)
            downloaded += 1
        except Exception as e:
            crushed.append(f'{doc['title']}: {e}')
        raise_cariage()

    # Итоги загрузки
    show_download_progress(downloaded, doc_count, crushed)
    show_crushed(crushed)


def show_download_progress(got, total, crushed):
    print(f'✓ Скачано: {got}/{total} ', end='')
    if crushed:
        print(f'| С ошибкой: {len(crushed)} ✗', end='')
    print()


def show_crushed(crushed):
    if not crushed:
        return
    print('Не удалось скачать следующие документы:')
    for doc in crushed:
        print(doc, end="\n")


def download_doc(session: Session, doc: dict, path: Path):
    response = get_response_without_stubs(session, doc)
    response.raise_for_status()
    file_path = get_safe_file_path(path, doc)
    expected_size = doc.get("size")

    clear_line()
    with open(file_path, mode='wb') as file:
        chunks_got = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # фильтруем keep-alive chunks
                file.write(chunk)
                chunks_got+= len(chunk)
            clear_line()
            if expected_size:
                progress = (chunks_got / expected_size) * 100
            print(f'{doc['title']} – {progress:.1f}%', end='\r')
    response.close()

    if expected_size and chunks_got != expected_size:
        raise Exception(f'Размер {chunks_got} не совпал с ожидаемым {expected_size}')


def get_safe_file_path(parent_path: Path, doc: dict):
    # Определяем имя и конечный путь для сохранения документа
    file_path = parent_path / Path(sanitize_filename(doc['title']))
    if file_path.suffix != ('.' + doc['ext']):
        suffix = '.' + doc['ext']
        file_path = file_path.with_suffix(suffix)
    file_path = get_unique_filename(file_path)
    return file_path


def get_unique_filename(filepath: Path):
    path = Path(filepath)
    if not path.exists():
        return path
    stem = path.stem  # Имя без расширения
    suffix = path.suffix  # Расширение
    parent = path.parent  # Папка
    
    counter = 1
    while True:
        # Создаём новое имя с номером
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        
        if not new_path.exists():
            return new_path
        counter += 1


def sanitize_filename(filename: str):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def clear_line():
    stdout.write('\033[K')
    stdout.flush()


def raise_cariage():
    stdout.write('\033[1A')
    stdout.flush()


def main():
    # Вставьте сюда свой токен, его можно получить через https://vkhost.github.io/
    token = ''
    if not token:
        token = input('Введите свой access-token:')
    docs = get_docs(token)

    # Перечислите в only_extetions конкретные расширения, файлы с которыми хотите скачать
    # only_extetions = ["mp4", "gif", "png", "jpg", "pdf"] # Формат расширений - без точки
    save_docs(docs)


if __name__ == '__main__':
    main()