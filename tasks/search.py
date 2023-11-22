# This is a solution to the search task from aidevs2 course
# See https://zadania.aidevs.pl/ for details
#
# Additional dependecies:
# pip install qdrant-client
#
# The overall goal is to:
# 1. Get a token from aidevs
# 2. Get the task from aidevs
# SOLUTION:
# 3. download the remote file with links. Skip download if it exists locally.
# 3. connect to qdrant
# 4. check if aidevs_search collection exists. If not, create it with size = 1536.
# 5. check if the remote document with links was downloaded. If not, download it.
# 6. check if each
# 4. Send the answer to aidevs
# 5. Profit!

import requests
import json
import yaml
import os
from uuid import uuid4
import qdrant_client
from qdrant_client.models import Distance, VectorParams, PointStruct

def load_apikey():
    """Loads the aidevs API key from ~/.aidevs2"""
    with open(os.path.expanduser('~/.aidevs2'), 'r') as file:
        api_key = yaml.safe_load(file)
    return api_key['APIKEY']

def load_openai_key():
    """Loads the openai API key from ~/.aidevs2"""
    with open(os.path.expanduser('~/.aidevs2'), 'r') as file:
        api_key = yaml.safe_load(file)
    return api_key['OPENAI_KEY']

BASE_URL = 'https://zadania.aidevs.pl'
APIKEY = load_apikey()
OPENAI_KEY = load_openai_key()
TASK = 'search'

# STEP 1: Get the token from aidevs
url = BASE_URL + '/token/' + TASK
print(f'aidevs: Getting {url}, sending {APIKEY}')
response1 = requests.post(url, json={ "apikey": APIKEY })
data = json.loads(response1.text)
token = data['token']
print(f"aidevs: My token is {token}")

# STEP 2: Get the task from aidevs
url = BASE_URL + '/task/' + token
query={  }
print(f"aidevs: Sending {query} to {url}")
response2 = requests.post(url, data=query)
data2 = json.loads(response2.text)
print(f"aidevs: response body: {data2}")

# STEP 3 - first need to download the file (if not present locally)
file_remote = 'https://unknow.news/archiwum.json'
file_local = 'data/archiwum.json'

if not os.path.exists(file_local):
    print(f'Downloading {file_remote} to {file_local}')
    os.makedirs(os.path.dirname(file_local), exist_ok=True)
    page = requests.get(file_remote)
    with open(file_local, 'wb') as f:
        f.write(page.content)
else:
    print(f"File {file_local} already exists, skipping download")

# STEP 4 - connect to qdrant
QDRANT_URL = "http://localhost:6333"

client = qdrant_client.QdrantClient(url=QDRANT_URL)
try:
    col = client.get_collection("aidevs_search")
    print("qdrant: Collection 'aidevs_search' exists, skipping creation")
except qdrant_client.http.exceptions.UnexpectedResponse:

    print("qdrant: Collection 'aidevs_search' does not exist, creating it")
    col = client.create_collection(
        collection_name="aidevs_search",
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )


# STEP 5 - check if there are any vectors in the collection
LIMIT_VECTORS = 3
collection_info = client.get_collection("aidevs_search")
if collection_info.vectors_count == 0:
    print("qdrant: Collection is empty, adding vectors")
    with open(file_local, 'r') as f:
        data = json.load(f)
        cnt = 0
        for item in data:
            cnt = cnt + 1
            print(f"qdrant: Adding item {cnt} of {len(data)}: {item}")

            uuid = uuid4()

            url = 'https://api.openai.com/v1/embeddings'
            headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {OPENAI_KEY}' }
            body = { "input": item['title'], "model": "text-embedding-ada-002"}
            print(f'OpenAI, step 1: Getting {url}, using {OPENAI_KEY}')
            page = requests.post(url, json=body, headers=headers)
            data = json.loads(page.text)
            print(f"OpenAI, step 1: Response body: {len(page.text)} chars")
            embeddings = data['data'][0]['embedding']

            result = client.upsert(collection_name="aidevs_search",
                                   points=[
                                       PointStruct(
                                        id=cnt,
                                        vector = embeddings,
                                        payload = item
                                       )
                                    ])
            print(f"qdrant: Inserted item {cnt}: result={result}, {item['title']}")

            if cnt >= LIMIT_VECTORS:
                print(f"qdrant: Limit of {LIMIT_VECTORS} vectors reached, stopping")
                break

# system_prompt = 'Twoim zdaniem jest odganięcie osoby, o której mowa. Użytkownik będzie podawał kolejne podpowiedzi. Jeżeli nie wiesz, o jaką osobę chodzi, to powiedz nie wiem. Jeżeli jesteś pewien, powiedz tylko imię i nazwisko, nic więcej.'


# attempt = 1

# hints = []

# while attempt < 10:
#     url = BASE_URL + '/task/' + token
#     query={  }
#     print(f"aidevs: Sending {query} to {url}")
#     response2 = requests.post(url, data=query)
#     data2 = json.loads(response2.text)
#     hint = data2['hint']
#     if hint not in hints:
#         hints.append(hint)
#     else:
#         print("aidevs: Hint already provided, sleeping for 5 seconds, retrying")
#         sleep(5)
#         continue
#     print(f"aidevs: the hint {attempt} is {hint}")

#     lmbd = lambda x: { 'role': 'user', 'content': x }


#     url = 'https://api.openai.com/v1/chat/completions'
#     headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {OPENAI_KEY}' }
#     body = { "messages": [{ "role": "system", "content": system_prompt}] + list(map(lmbd, hints)), "model": "gpt-3.5-turbo"}

#     print(f"Iteration {attempt}, sending {body}")

#     attempt = attempt + 1


#     print(f'OpenAI, attempt {attempt}: Getting {url}, using {OPENAI_KEY}')
#     page = requests.post(url, json=body, headers=headers)
#     data = json.loads(page.text)
#     print(f"OpenAI, step 1: Response body: {data}")
#     answer = data['choices'][0]['message']['content']
#     print(f"OpenAI answer: the answer is {answer}")

#     if answer.lower().find("nie wiem") == -1:
#         # STEP 4: Send the answer
#         url = BASE_URL + '/answer/' + token
#         print(f'aidevs: Getting {url}, sending {answer}')
#         response3 = requests.post(url, json = { "answer": answer })
#         data3 = json.loads(response3.text)
#         print(f"aidevs: /answer/token returned {data3}")

#         sys.exit(0)
