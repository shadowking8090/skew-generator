import json
from unittest.mock import Mock, patch

import numpy as np
import pytest

import wrapper
from data import Data
from sampleData import x


def payload(**changes):
    return json.dumps({'curves': [dict(name='Test (synthetic)', trials=20,
                                      rate=0.4, bw=0.06, **changes)]})


def test_generate_data_uses_description_and_returns_plot_data():
    response = Mock()
    response.json.return_value = {'reply': payload()}
    with patch.object(wrapper.requests, 'post', return_value=response) as post:
        items = wrapper.generate_data('Model fatigue')
    response.raise_for_status.assert_called_once()
    assert 'Model fatigue' in post.call_args.kwargs['json']['prompt']
    assert post.call_args.kwargs['timeout'] == 60
    assert len(items) == 1 and isinstance(items[0], Data)
    assert items[0].name == 'Test'
    np.testing.assert_array_equal(items[0].trace.x, x)
    assert np.all(np.isfinite(items[0].trace.y))
    assert min(items[0].trace.y) >= 0
    assert max(items[0].trace.y) == pytest.approx(0.9)


def test_accepts_json_code_block():
    assert len(wrapper.parse_curves('```json\n' + payload() + '\n```')) == 1


@pytest.mark.parametrize('field,value', [
    ('trials', True), ('trials', 0), ('trials', 1001),
    ('rate', float('nan')), ('rate', 1.1), ('bw', 0),
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
