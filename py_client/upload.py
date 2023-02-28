import requests
from getpass import getpass

auth_endpoint = "http://127.0.0.1:8000/api/auth/" 
username = input("What is your username?\n")
password = getpass("What is your password?\n")

auth_response = requests.post(auth_endpoint, json={'username': username, 'password': password})

if auth_response.status_code == 200:
    token = auth_response.json()['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }
    endpoint = "http://127.0.0.1:8000/api/images/"
    with open('py_client/images/nft2.jpg', 'rb') as image_file:
        files = {'image_url': image_file}
        get_response = requests.post(endpoint, headers=headers, files=files)
    print(f'Post status code: {get_response.status_code}')
    print(f'Post response: {get_response.json()}')
else:
    print(f'Auth status code: {auth_response.status_code}')
    print(f'Auth response: {auth_response.json()}')