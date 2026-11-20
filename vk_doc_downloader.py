from pathlib import Path
import requests
from requests import Session
from sys import stdout


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


def save_docs(documents : list[dict], save_path: Path | None = None, only_types: list[str] | None = None):
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
    if only_types:
        docs_with_selected_types = [doc for doc in documents if get_safe_file_path("", doc).suffix in only_types]
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
    print('Не удалось скачать следующие документы:')
    for doc in crushed:
        print(doc, end="\n")


def download_doc(session: Session, doc: dict, path: Path):
    response = session.get(doc["url"], stream=True, timeout=30)
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
            progress = (chunks_got / expected_size) * 100
            print(f'{doc['title']} – {progress:.1f}%', end='\r')


def get_safe_file_path(parent_path: Path, doc: dict):
    # Определяем имя и конечный путь для сохранения документа
    file_path = parent_path / Path(sanitize_filename(doc['title']))
    if not file_path.suffix:
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

    # Если нужно скачать все файлы, оставьте None
    only_types = None
    # only_types = [".mp4", ".gif"]
    save_docs(docs, only_types=only_types)


if __name__ == '__main__':
    main()