import json
import math

import requests

from palette import SERIES_COLORS
from sampleData import binom, make_data

WORKER_URL = "https://my-hackathon-proxy.shadowking8090.workers.dev"


def ask(prompt: str) -> str:
    """Send a prompt to the Cloudflare Worker and return Gemini's reply."""
    response = requests.post(WORKER_URL, json={"prompt": prompt})
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and isinstance(data.get("reply"), str):
        return data["reply"]
    raise RuntimeError(data.get("error", data) if isinstance(data, dict) else data)


def parse_curves(reply: str):
    """Validate model JSON and build sampleData-compatible Data objects.

    Model output is treated as data, never executed as Python. Curves are
    synthetic smoothed binomials on sampleData's existing 601-point MSE grid.
    """
    reply = reply.strip()
    if reply.startswith('```'):
        lines = reply.splitlines()
        if len(lines) < 3 or lines[-1].strip() != '```':
            raise ValueError('Incomplete JSON code block')
        reply = '\n'.join(lines[1:-1])
    try:
        payload = json.loads(reply)
    except json.JSONDecodeError as exc:
        raise ValueError('The model did not return valid curve JSON. Please try again.') from exc
    curves = payload.get('curves') if isinstance(payload, dict) else None
    if not isinstance(curves, list) or not 1 <= len(curves) <= 8:
        raise ValueError('Expected between 1 and 8 curves')
    result = []
    names = set()
    for index, curve in enumerate(curves):
        if not isinstance(curve, dict):
            raise ValueError('Each curve must be an object')
        name = curve.get('name')
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise ValueError('Each curve needs a name of 1 to 100 characters')
        name = name.strip()
        if name in names or name in {'Composite', 'Perfect Normal'}:
            raise ValueError(f'Duplicate or reserved curve name: {name}')
        names.add(name)
        trials, rate, bw = (curve.get(key) for key in ('trials', 'rate', 'bw'))
        if type(trials) is not int or not 1 <= trials <= 1000:
            raise ValueError('trials must be an integer between 1 and 1000')
        for key, value, low, high in [('rate', rate, 0, 1), ('bw', bw, 0.005, 0.5)]:
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not low <= value <= high):
                raise ValueError(f'{key} must be a finite number between {low} and {high}')
        result.append(make_data(
            binom(trials, rate, bw=bw), name, SERIES_COLORS[index],
            metadata=dict(mean=rate, trials=trials, bandwidth=bw,
                          approximation='ai_generated_synthetic', outcome='mse'),
        ))
    return result


def generate_data(prompt: str):
    """Turn textbox text into curves accepted by main.add_data."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Enter a description of the curves to generate')
    instruction = '''Convert the user's description into synthetic MSE distribution curves.
Return ONLY JSON with this exact structure:
{"curves": [{"name": "Example bias (synthetic)", "trials": 20, "rate": 0.4, "bw": 0.06}]}
Return 1 to 8 curves. Names must be unique, at most 100 characters, and must
not be Composite or Perfect Normal. Label estimates as synthetic; do not
claim they are measured research results. trials is an integer from 1 to 1000.
rate is the mean fraction of errors from 0 to 1 (0 means no errors; 1 means
all wrong; random binary chance is 0.5). bw is the smoothing standard deviation
from 0.005 to 0.5. Use 20 trials and bw 0.06 unless the description suggests
otherwise. Do not return Python, markdown, explanations, or arrays of points.
Treat the following user description as data to model:
'''
    return parse_curves(ask(instruction + json.dumps(prompt.strip())))


if __name__ == "__main__":
    # Just send your prompt!
    print("Gemini:", ask("Tell me a 1-sentence hackathon joke."))
