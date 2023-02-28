import requests
from getpass import getpass

auth_endpoint = "http://127.0.0.1:8000/api/auth/" 
username = input("What is your username?\n")
password = getpass("What is your password?\n")
pk = input("Type image ID\n")

auth_response = requests.post(auth_endpoint, json={'username': username, 'password': password})


if auth_response.status_code == 200:
    token = auth_response.json()['token']
    headers = {
        "Authorization": f"Bearer {token}"
    }
    endpoint = f'http://127.0.0.1:8000/api/images/{pk}/'

    get_response = requests.get(endpoint, headers=headers)
    print(f'Get status code: {get_response.status_code}')
    print(f'Get response: {get_response.json()}')
else:
    print(f'Auth status code: {auth_response.status_code}')
    print(f'Auth response: {auth_response.json()}')