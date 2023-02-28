# ImageOcean
###### ImageOcean is a Django-based web application that shares browsable API created with django rest framework. API allows users to authorize, create thumbnails and fetch link to binary images that that expires after a number of seconds (user can specify any number between 300 and 30000)

## To run and test the application, you must follow these steps:

###### Build the container command: docker-compose -f docker-compose.yml build

###### Run the container command: docker-compose -f docker-compose.yml up

###### Crete superuser command: docker-compose run --rm web sh -c "python manage.py createsuperuser"

###### Login as suoeruser in admin UI and set the user tier in: Users -> created superuser -> User tier

## Endpoints:

## Admin UI:
###### Access to the Django Admin UI
###### endpoint: http://127.0.0.1:8000/api/admin


## Auth:
###### Allows to obtain a TokenAuthentication
###### endpoint: http://127.0.0.1:8000/api/auth/

    json={'username': username, 'password': password}
    
###### sample request POST:
    auth_response = requests.post(auth_endpoint, json=json)
Responses: 
###### HTTP 200 OK
###### RESPONSE EXAMPLE
    {
        'token': 'SAMPLE_TokenAuthentication'
    }
###### HTTP 400 Bad Request
###### RESPONSE EXAMPLE
    {
        'non_field_errors': ['Unable to log in with provided credentials.']
    }

## Upload / List Images:
###### endpoint: http://127.0.0.1:8000/api/images/
Allows to upload and list uploaded images

    headers = {'Authorization': f'Bearer {TokenAuthentication}'}
    files = {'image_url': image_file}

###### sample request GET: 
    get_response = requests.get(endpoint, headers=headers)
Responses:

###### sample request POST: 
    get_response = requests.post(endpoint, headers=headers, files=files)
Responses:
###### HTTP 200 OK
###### RESPONSE EXAMPLE
    [
        {
            "id": 1,
            "thumbnails_urls": [
                "{'200px': 'http://127.0.0.1:8000/api/images/1/thumbnail_view/200/Avatar.jpg'}",
                "{'400px': 'http://127.0.0.1:8000/api/images/1/thumbnail_view/400/Avatar.jpg'}"
            ],
            "image_url": "http://127.0.0.1:8000/static/media/images/Avatar.jpg"
        }
    ]
###### HTTP 201 CREATED
###### RESPONSE EXAMPLE
    {
        "id": 2,
        "thumbnails_urls": [
            "{'200px': 'http://127.0.0.1:8000/api/images/2/thumbnail_view/200/Logo.png'}",
            "{'400px': 'http://127.0.0.1:8000/api/images/2/thumbnail_view/400/Logo.png'}"
        ],
        "image_url": "http://127.0.0.1:8000/static/media/images/Logo.png"
    }
###### HTTP 400 Bad Request
###### RESPONSE EXAMPLE
    {
        "image_url": [
            "Invalid file extension allowed extensions are .JPG and .PNG"
        ]
    }
## Single image details:
###### endpoint: http://127.0.0.1:8000/api/images/<'pk'>
###### Allows to view details of single uploaded image

###### <'pk'> is primary key of uploaded image
    headers = {'Authorization': f'Bearer {TokenAuthentication}'}

###### sample request GET: 
    get_response = requests.get(endpoint, headers=headers)
Responses:
###### HTTP 200 OK
###### RESPONSE EXAMPLE
    {
        "id": 2,
        "thumbnails_urls": [
            "{'200px': 'http://127.0.0.1:8000/api/images/2/thumbnail_view/200/Logo.png'}",
            "{'400px': 'http://127.0.0.1:8000/api/images/2/thumbnail_view/400/Logo.png'}"
        ],
        "image_url": "http://127.0.0.1:8000/static/media/images/Logo.png"
    }
###### HTTP 404 Not Found
###### RESPONSE EXAMPLE
    {
        'detail': 'Not found.'
    }
JSON with thumbnails urls and link to original image (depends on user tier)

## Fetch link to binary image: 
###### endpoint: http://127.0.0.1:8000/api/images/<'pk'>/binary
###### Allows to fetch a link to binary image that expires after a number of seconds (user can specify any number between 300 and 30000)

    headers = {'Authorization': f'Bearer {TokenAuthentication}'}
    params = {"expiration_seconds": expiration_seconds(integer)}

###### sample request GET: 
    get_response = requests.get(endpoint, headers=headers, params=params)
Responses:
###### HTTP 200 OK
###### RESPONSE EXAMPLE
    {
        "url": "http://127.0.0.1:8000/api/images/1/binary_image_view/2023-02-28T14:32:35/Krzyk_E7m1m2f.jpg",
        "expiration_seconds": 300
    }
###### HTTP 400 Bad Request
###### RESPONSE EXAMPLE
    {
        "error": "Expiration time must be between 300 and 30000 seconds"
    }
###### HTTP 404 Not Found
###### RESPONSE EXAMPLE
    {
        'detail': 'Not found.'
    }
