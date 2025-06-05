#!/bin/python3
import sys
import requests

from dotenv import load_dotenv
import os

argv = sys.argv
if len(argv) < 2:
    print('You need to specify a action.')
    print(f'usage: {argv[0]} <cpu|upload|get|reload|upload-hook>')
    sys.exit(-1)

load_dotenv()

username = os.getenv('PYTHONANYWHERE_USER')
token = os.getenv('PYTHONANYWHERE_API_TOKEN', '')
host = os.getenv('PYTHONANYWHERE_HOST', 'https://www.pythonanywhere.com/') + 'api'
webhost = os.getenv('PYTHONANYWHERE_WEBHOST', username + '.pythonanywhere.com')

site_path = os.getenv('PYTHONANYWHERE_SITE_PATH', 'mysite')
base_server_file = f'/home/{username}/{site_path}'

def cpu_info():
    url = host + '/v0/user/{username}/cpu/'.format(username=username) 
    response = requests.get(
        url,
        headers={'Authorization': 'Token {token}'.format(token=token)}
    )
    if response.status_code == 200:
        print('CPU quota info:')
        data = response.json()
        for key in data:
            print(f"{key}: {data[key]}")
    else:
        print('Got unexpected status code {}: {!r}'.format(response.status_code, response.content))

def upload_file():
    if len(sys.argv) != 3:
        print('You need to specify a file path')
        print(f'Usage: {sys.argv[0]} <fileName>')
        sys.exit(-1)

    file_path = sys.argv[2]

    url = host + '/v0/user/{username}/files/path/{base_path}/{path}'.format(
            username=username, 
            base_path=base_server_file,
            path=file_path) 

    with open(file_path, 'rb') as f:
        files = {
                "content": f,
        }

        res = requests.post(url,
                            headers={'Authorization': 'Token {token}'.format(token=token)},
                            files=files)
    if res.status_code == 200:
        print(f"File '{file_path}' was updated.")
    else:
        print(f"File '{file_path}' was created.")

def get_file():
    if len(argv) != 3:
        print('You need to specify a file path')
        print(f'Usage: {argv[0]} {argv[1]} <fileName>')
        sys.exit(-1)


    file_path = sys.argv[2]

    url = host + '/v0/user/{username}/files/path/{base_path}/{path}'.format(
            username=username, 
            base_path=base_server_file,
            path=file_path) 

    res = requests.get(url,
                        headers={'Authorization': 'Token {token}'.format(token=token)})
    print("Código de estado:", res.status_code)

    headers = res.headers
    content = res.text

    if headers['Content-Type'] == 'application/json':
        files = res.json()
        if 'detail' in files:
            print(files['detail'])
        else:
            for file in files:
                d = files[file]['type'] == 'directory'

                if d:
                    print('󰉋 ', end='')
                else:
                    print('󰈔 ', end='')
                print(file)
    else:
        dir_i = file_path.rfind('/')
        if dir_i != -1:
            dir = file_path[:dir_i]
            os.makedirs(dir, exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(content)
            print(content)

def remove_file():
    if len(argv) != 3:
        print('You need to specify a file path')
        print(f'Usage: {argv[0]} {argv[1]} <fileName>')
        sys.exit(-1)

    file_path = sys.argv[2]
    if input(f"Are you sure you want to delete the file '{file_path}'? Y/N (N) ") == 'Y':
        url = host + '/v0/user/{username}/files/path/{base_path}/{path}'.format(
                username=username, 
                base_path=base_server_file,
                path=file_path) 

        res = requests.delete(url,
                            headers={'Authorization': 'Token {token}'.format(token=token)})
        if res.status_code == 204:
            print(f"The file '{file_path}' was deleted.")
        else:
            message = res.json()['message']
            print(f'ERROR: {message}')


def reload_page():
    url = host + '/v0/user/{username}/webapps/{domain_name}/reload/'.format(
        username=username,
        domain_name=webhost
        )
    res = requests.post(url,
        headers={'Authorization': 'Token {token}'.format(token=token)}).json()
    if 'status' in res:
        print(f"Status: {res['status']}")

def set_pre_commit():
    hook_code = f"""#!/bin/bash
staged_files=$(git diff --cached --name-only)

for file in $staged_files; do
    {argv[0]} upload "$file"
done"""
    os.makedirs('.git/hooks')
    with open('.git/hooks/pre-commit', 'a') as file:
        file.write(hook_code)

cmd = argv[1]
if cmd == 'cpu':
    cpu_info()
elif cmd == 'get':
    get_file()
elif cmd == 'upload':
    upload_file()
elif cmd == 'reload':
    reload_page()
elif cmd == 'remove':
    remove_file()
elif cmd == 'upload-hook':
    set_pre_commit()
else:
    print(f"Uknown action '{cmd}'")
