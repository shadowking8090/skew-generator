import json
from unittest.mock import Mock, patch

import numpy as np
import pytest
import requests

import plotly.graph_objects as go

import wrapper
from data import Data, weighted_composite
from sampleData import x


def payload(**changes):
    return json.dumps({'curves': [dict(name='Test (synthetic)', trials=20,
                                      rate=0.4, bw=0.06, weight=0.18,
                                      weight_source='About 18% of working adults',
                                      **changes)]})


def test_generate_data_uses_description_and_returns_plot_data():
    response = Mock()
    response.json.return_value = {'reply': payload()}
    with patch.object(wrapper.requests, 'post', return_value=response) as post:
        items = wrapper.generate_data('Model fatigue')
    response.raise_for_status.assert_called_once()
    assert 'Model fatigue' in post.call_args.kwargs['json']['prompt']
    assert 'model' not in post.call_args.kwargs['json']
    assert post.call_args.kwargs['timeout'] == 60
    assert len(items) == 1 and isinstance(items[0], Data)
    assert items[0].name == 'Test'
    np.testing.assert_array_equal(items[0].trace.x, x)
    assert np.all(np.isfinite(items[0].trace.y))
    assert min(items[0].trace.y) >= 0
    assert max(items[0].trace.y) == pytest.approx(0.9)
    assert items[0].weight == pytest.approx(0.18)
    assert '18%' in items[0].weight_source


def test_accepts_json_code_block():
    assert len(wrapper.parse_curves('```json\n' + payload() + '\n```')) == 1


@pytest.mark.parametrize('field,value', [
    ('trials', True), ('trials', 0), ('trials', 1001),
    ('rate', float('nan')), ('rate', 1.1), ('bw', 0),
    ('weight', 0), ('weight', 1.1), ('weight', float('nan')),
    ('weight_source', ''), ('weight_source', 'x' * 121),
    ('name', 'Composite'), ('name', ''),
])
def test_rejects_invalid_parameters(field, value):
    curve = json.loads(payload())
    curve['curves'][0][field] = value
    with pytest.raises(ValueError):
        wrapper.parse_curves(json.dumps(curve))


@pytest.mark.parametrize('reply', ['not json', '{}', '{"curves": []}',
                                   '__import__("os").system("echo unsafe")'])
def test_rejects_invalid_responses(reply):
    with pytest.raises(ValueError):
        wrapper.parse_curves(reply)


@pytest.mark.parametrize('prompt', ['', '   ', '12345', '?!?'])
def test_empty_or_nonverbal_prompt_never_calls_api(prompt):
    with patch.object(wrapper, 'ask') as ask:
        with pytest.raises(wrapper.InvalidProjectPrompt):
            wrapper.generate_project(prompt)
    ask.assert_not_called()


@pytest.mark.parametrize('reply', ['{}', '{"valid": "true"}', 'not json'])
def test_malformed_combined_response_does_not_trigger_another_call(reply):
    with patch.object(wrapper, 'ask', return_value=reply) as ask:
        with pytest.raises(ValueError):
            wrapper.generate_project('How fatigue affects accuracy')
    ask.assert_called_once()


def test_rejected_prompt_explains_what_to_change():
    with patch.object(wrapper, 'ask', return_value='{"valid": false, "reason": "greeting"}'):
        with pytest.raises(wrapper.InvalidProjectPrompt, match='instead of a greeting'):
            wrapper.generate_project('hello')


@pytest.mark.parametrize('error,expected', [
    (requests.Timeout('private details'), 'took too long'),
    (requests.ConnectionError('private details'), 'internet connection'),
    (ValueError('private details'), 'usable project'),
    (RuntimeError('private details'), 'could not create'),
])
def test_errors_have_helpful_messages_without_raw_details(error, expected):
    message = wrapper.project_error_message(error)
    assert expected in message
    assert 'private details' not in message


@pytest.mark.parametrize('status,expected', [(429, 'too many requests'),
                                          (503, 'temporarily unavailable'),
                                          (401, 'API access')])
def test_http_errors_explain_service_failure(status, expected):
    response = requests.Response()
    response.status_code = status
    error = requests.HTTPError('private details', response=response)
    assert expected in wrapper.project_error_message(error)


def test_unavailable_model_is_reported_as_configuration_problem():
    response = requests.Response()
    response.status_code = 503
    response._content = b'{"error":"models/gemini-1.5-pro is not found for API version v1beta"}'
    error = requests.HTTPError(response=response)
    assert 'Update the Gemini model in the Cloudflare Worker' in wrapper.project_error_message(error)


def test_disabled_api_explains_how_to_enable_it():
    response = requests.Response()
    response.status_code = 403
    response._content = b'{"error":"Gemini API has not been used in project 123 before or it is disabled."}'
    message = wrapper.project_error_message(requests.HTTPError(response=response))
    assert 'Enable the Generative Language API' in message
    assert 'wait a few minutes' in message


<<<<<<< Updated upstream
@pytest.mark.parametrize('code,status,expected', [
    ('timeout', 504, 'took too long'),
    ('incomplete', 502, 'incomplete'),
    ('blocked', 422, 'neutral wording'),
    ('model_unavailable', 404, 'Update MODELS'),
    ('configuration', 500, 'settings checked'),
    ('connection', 502, 'could not reach Gemini'),
])
def test_worker_failure_codes_have_specific_messages(code, status, expected):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({'code': code, 'error': 'private upstream detail'}).encode()
    message = wrapper.project_error_message(requests.HTTPError(response=response))
    assert expected in message
    assert 'private upstream detail' not in message
=======
def test_weighted_composite_keeps_unclaimed_share_on_the_baseline():
    base = np.array([1.0, 1.0])
    factor = Data(go.Scatter(x=[0, 1], y=[0.0, 4.0]), 'Age', 'red', weight=0.25)
    mixed = weighted_composite(base, [factor])
    # Curves are mixed as densities (area 1): base [1, 1] has area 1, the factor area 2.
    np.testing.assert_allclose(mixed, 0.75 * base + 0.25 * np.array([0.0, 2.0]))


def test_weighted_composite_mixes_by_area_not_peak_height():
    grid = np.linspace(0, 1, 601)
    base = np.ones_like(grid)
    narrow = Data(go.Scatter(x=grid, y=np.exp(-0.5 * ((grid - 0.3) / 0.02) ** 2)), 'N', 'red', weight=0.2)
    wide = Data(go.Scatter(x=grid, y=np.exp(-0.5 * ((grid - 0.7) / 0.10) ** 2)), 'W', 'blue', weight=0.2)
    mixed = weighted_composite(base, [narrow, wide])
    left, right = mixed[grid < 0.5], mixed[grid >= 0.5]
    # Same share means the same number of people on each side, whatever the width.
    excess = lambda part: np.sum(part - 0.6) * (grid[1] - grid[0])
    np.testing.assert_allclose(excess(left), excess(right), atol=0.01)   # peak-mixing is ~5x off
    np.testing.assert_allclose(np.sum((mixed[1:] + mixed[:-1]) / 2) * (grid[1] - grid[0]), 1.0, atol=1e-6)


def test_factor_contribution_is_that_factors_slice_of_the_composite():
    from data import factor_contribution
    base = np.array([1.0, 1.0])
    a = Data(go.Scatter(x=[0, 1], y=[2.0, 0.0]), 'A', 'red', weight=0.3)
    b = Data(go.Scatter(x=[0, 1], y=[0.0, 2.0]), 'B', 'blue', weight=0.2)
    mixed = weighted_composite(base, [a, b])
    np.testing.assert_allclose(factor_contribution(a, [a, b]), 0.3 * np.array([2.0, 0.0]))
    np.testing.assert_allclose(
        mixed, 0.5 * base + factor_contribution(a, [a, b]) + factor_contribution(b, [a, b]))


def test_weighted_composite_renormalizes_when_shares_exceed_one():
    base = np.array([10.0, 10.0])
    a = Data(go.Scatter(x=[0, 1], y=[2.0, 0.0]), 'A', 'red', weight=0.6)
    b = Data(go.Scatter(x=[0, 1], y=[0.0, 2.0]), 'B', 'blue', weight=0.6)
    mixed = weighted_composite(base, [a, b])
    np.testing.assert_allclose(mixed, 0.5 * np.array([2.0, 0.0]) + 0.5 * np.array([0.0, 2.0]))
>>>>>>> Stashed changes
