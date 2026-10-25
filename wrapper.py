import requests

WORKER_URL = "https://my-hackathon-proxy.shadowking8090.workers.dev"

# Just send your prompt!
payload = {
    "prompt": "Tell me a 1-sentence hackathon joke."
}

response = requests.post(WORKER_URL, json=payload)
data = response.json()

if "reply" in data:
    print("Gemini:", data["reply"])
else:
    print("Error:", data)