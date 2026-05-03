from pathlib import Path
import requests
from sys import stdout


def get_docs(token):
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


def save_docs(documents, savefolder_path=None):
    '''
    Скачиваем и сохраняем документы в папку
    '''
    # Сохранять в папку рядом, если не указано явно
    if not documents:
        return
    
    if savefolder_path is None:
        savefolder_path = Path(__file__).parent / 'savefolder'
    else:
        savefolder_path = Path(savefolder_path)
    savefolder_path.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    crushed = []
    for doc in documents:
        try:
            response = requests.get(doc["url"], stream=True, timeout=30)
            response.raise_for_status()
            file_path = get_safe_file_path(savefolder_path, doc)
            total_size = int(response.headers.get('content-length', 0))

            clear_line()
            print(f'✓ Скачано: {downloaded}/{len(documents)} ', end='')
            if crushed:
                print(f'| С ошибкой: {len(crushed)} ✗', end='')
            print()

            with open(file_path, mode='wb') as file:
                chunks_got = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # фильтруем keep-alive chunks
                        file.write(chunk)
                        chunks_got+= len(chunk)

                    if total_size == 0:
                        raise Exception('Файл пустой')
                    clear_line()
                    progress = (chunks_got / total_size) * 100
                    print(f'{doc['title']} – {progress:.1f}%', end='\r')
                raise_cariage()
            downloaded += 1


        except Exception as e:
            crushed.append(f'{doc['title']}: ({e}\n')
    

    # Итоги загрузки
    print(f'✓ Скачано {downloaded} / {len(documents)}')
    if crushed:
        print('Не удалось скачать следующие документы:')
        for doc in crushed:
            print(doc)


def get_safe_file_path(parent_path, doc):
    # Определяем имя и конечный путь для сохранения документа
    file_path = parent_path / Path(sanitize_filename(doc['title']))
    if not file_path.suffix:
        suffix = '.' + doc['ext']
        file_path = file_path.with_suffix(suffix)
    file_path = get_unique_filename(file_path)
    return file_path

def get_unique_filename(filepath):
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


def sanitize_filename(filename):
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
    save_docs(docs)


if __name__ == '__main__':
    main()