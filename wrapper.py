import requests

WORKER_URL = "https://my-hackathon-proxy.shadowking8090.workers.dev"


def ask(prompt: str) -> str:
    """Send a prompt to the Cloudflare Worker and return Gemini's reply."""
    response = requests.post(WORKER_URL, json={"prompt": prompt})
    data = response.json()

    if "reply" in data:
        return data["reply"]
    raise RuntimeError(data.get("error", data) if isinstance(data, dict) else data)


if __name__ == "__main__":
    # Just send your prompt!
    print("Gemini:", ask("Tell me a 1-sentence hackathon joke."))
