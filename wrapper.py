import requests

# Put your JavaScript worker URL here:
WORKER_URL = "https://my-hackathon-proxy.shadowking8090.workers.dev/"

# The data you want to send:
payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "user", "content": "Tell me a 1-sentence hackathon joke."}
    ]
}

# Send the request
response = requests.post(WORKER_URL, json=payload)

# Print the result
data = response.json()
print(data["choices"][0]["message"]["content"])