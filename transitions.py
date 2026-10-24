"""Animated transitions for the composite plot (NiceGUI + Plotly).

ui.plotly's plot.update() resends the whole figure and snaps to it, and
Plotly.animate snaps at the end of the transition. So the tweens here run in
the browser with requestAnimationFrame and restyle individual traces; the last
frame always sets the exact target values.

Two transitions:

* animate_traces(...)       tween a trace's y-values to new values (composite)
* show_curve / hide_curve / rescale_curve
                            the hover previews: a preview's height is a multiplier
                            that grows 0 -> 1 on hover and shrinks 1 -> 0 on unhover.
                            Every preview trace has its own state and its own color,
                            so one can shrink away while the next one grows in.

Keep the Python figure in sync yourself (assign fig.data[i].y etc.); these
functions only change what the browser shows. Never call plot.update() while
using them, because it resends the figure and cancels running transitions.
"""

import json
from typing import Mapping, Optional, Sequence

import numpy as np
from nicegui import ui

DEFAULT_DURATION = 500           # composite tween, milliseconds
PREVIEW_DURATION = 200           # preview grow / shrink, milliseconds
DEFAULT_EASING = 'cubic-in-out'  # 'linear', 'quad-in-out', 'cubic-in-out', 'sin-in-out'

_EASINGS_JS = '''
const easings = {
    'linear': t => t,
    'quad-in-out': t => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
    'cubic-in-out': t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
    'sin-in-out': t => -(Math.cos(Math.PI * t) - 1) / 2,
};
'''

# Last target sent per (plot, trace); used to ignore repeated identical requests.
_last_target: dict[tuple[int, int], np.ndarray] = {}


def _floats(values) -> list:
    return np.asarray(values, dtype=float).tolist()


# ---------------------------------------------------------------- composite

_TWEEN_JS = '''
(() => {
    const gd = getHtmlElement(__ID__);
    const traces = __TRACES__;
    const targets = __TARGETS__;
    const froms = __FROMS__;
    const duration = __DURATION__;
''' + _EASINGS_JS + '''
    const ease = easings[__EASING__] || easings['cubic-in-out'];

    // Where each trace is right now: the live tween value if one is running,
    // otherwise the starting values sent from Python.
    const live = gd._tweenCur || {};
    const starts = traces.map((idx, j) => live[idx] || froms[j] || []);

    if (gd._tweenFrame) cancelAnimationFrame(gd._tweenFrame);
    // Record where each trace is NOW, before any frame has been drawn. If another
    // request arrives before this tween's first frame (e.g. select-all), it then
    // starts from what is on screen instead of from an undrawn intermediate target.
    gd._tweenCur = {};
    traces.forEach((idx, j) => { gd._tweenCur[idx] = starts[j]; });

    const t0 = performance.now();
    const step = (now) => {
        const t = Math.min(1, (now - t0) / duration);
        const k = ease(t);
        const ys = targets.map((target, j) =>
            t >= 1 || starts[j].length !== target.length
                ? target   // final frame (or length mismatch): exact target values
                : target.map((v, n) => starts[j][n] + (v - starts[j][n]) * k));
        traces.forEach((idx, j) => { gd._tweenCur[idx] = ys[j]; });
        Plotly.restyle(gd, {y: ys}, traces);
        if (t < 1) {
            gd._tweenFrame = requestAnimationFrame(step);
        } else {
            gd._tweenFrame = null;
            gd._tweenCur = {};
        }
    };
    gd._tweenFrame = requestAnimationFrame(step);
})();
'''


def animate_traces(
    plot: ui.plotly,
    updates: Mapping[int, Sequence[float]],
    starts: Optional[Mapping[int, Sequence[float]]] = None,
    duration: int = DEFAULT_DURATION,
    easing: str = DEFAULT_EASING,
) -> None:
    """Tween the y-values of the given traces to new values.

    updates: {trace_index: new_y}
    starts:  {trace_index: y_before_the_change}. Pass the values the trace had
             before you changed it. They are used as the starting point unless
             a tween is already running, in which case it continues from where
             that one currently is.

    A request whose target equals the previous one for that trace is ignored,
    so duplicate events do not restart the animation.
    """
    starts = starts or {}
    todo: dict[int, np.ndarray] = {}
    for idx, y in updates.items():
        new = np.asarray(y, dtype=float)
        key = (plot.id, idx)
        last = _last_target.get(key)
        if last is None and idx in starts:
            last = np.asarray(starts[idx], dtype=float)
        _last_target[key] = new
        if last is not None and last.shape == new.shape and np.allclose(last, new, atol=1e-12):
            continue
        todo[idx] = new
    if not todo:
        return

    js = (_TWEEN_JS
          .replace('__ID__', str(plot.id))
          .replace('__TRACES__', json.dumps(list(todo)))
          .replace('__TARGETS__', json.dumps([_floats(y) for y in todo.values()]))
          .replace('__FROMS__', json.dumps([_floats(starts[i]) if i in starts else None for i in todo]))
          .replace('__DURATION__', str(int(duration)))
          .replace('__EASING__', json.dumps(easing)))
    ui.run_javascript(js)


# ------------------------------------------------------------------ preview

_PREVIEW_JS = '''
(() => {
    const gd = getHtmlElement(__ID__);
    const idx = __INDEX__;
    const mode = __MODE__;           // 'show' | 'hide' | 'rescale'
    const duration = __DURATION__;
    const color = __COLOR__;         // line color for 'show', or null to keep it
''' + _EASINGS_JS + '''
    const ease = easings['cubic-in-out'];

    // Each preview trace has its own state, so several can animate at once
    // (one shrinking away while the next one grows in).
    // m = height multiplier (0..1); base = the curve at full height.
    const all = gd._previews || (gd._previews = {});
    const st = all[idx] || (all[idx] = {m: 0, base: [], frame: null});
    const draw = () => Plotly.restyle(gd, {y: [st.base.map(v => v * st.m)]}, [idx]);

    const run = (to) => {
        if (st.frame) cancelAnimationFrame(st.frame);
        const from = st.m, t0 = performance.now();
        const step = (now) => {
            const t = Math.min(1, (now - t0) / duration);
            st.m = t >= 1 ? to : from + (to - from) * ease(t);
            draw();   // reads st.base every frame, so a rescale mid-tween is picked up
            if (t < 1) {
                st.frame = requestAnimationFrame(step);
            } else {
                st.frame = null;
                if (to === 0) Plotly.restyle(gd, {visible: [false]}, [idx]);
            }
        };
        st.frame = requestAnimationFrame(step);
    };

    if (mode === 'show') {
        if (st.frame) cancelAnimationFrame(st.frame);
        st.frame = null;
        st.base = __Y__;
        st.m = 0;
        const props = {x: [__X__], y: [st.base.map(() => 0)], visible: [true]};
        if (color) props['line.color'] = [color];
        Plotly.restyle(gd, props, [idx]);
        run(1);
    } else if (mode === 'hide') {
        if (st.m > 0 || st.frame) run(0);
    } else if (mode === 'rescale') {
        st.base = __Y__;
        if (!st.frame && st.m > 0) draw();
    }
})();
'''


def _preview(plot, index, mode, x=None, y=None, color=None, duration=PREVIEW_DURATION) -> None:
    js = (_PREVIEW_JS
          .replace('__ID__', str(plot.id))
          .replace('__INDEX__', str(int(index)))
          .replace('__MODE__', json.dumps(mode))
          .replace('__DURATION__', str(int(duration)))
          .replace('__COLOR__', json.dumps(color))
          .replace('__X__', json.dumps(_floats(x) if x is not None else []))
          .replace('__Y__', json.dumps(_floats(y) if y is not None else [])))
    ui.run_javascript(js)


def show_curve(plot: ui.plotly, index: int, x: Sequence[float], y: Sequence[float],
               color: Optional[str] = None, duration: int = PREVIEW_DURATION) -> None:
    """Show trace `index` with curve (x, y) in `color`, growing its height from 0 to full."""
    _preview(plot, index, 'show', x, y, color, duration)


def hide_curve(plot: ui.plotly, index: int, duration: int = PREVIEW_DURATION) -> None:
    """Shrink trace `index` to 0 height, then hide it. Other previews are unaffected."""
    _preview(plot, index, 'hide', duration=duration)


def rescale_curve(plot: ui.plotly, index: int, y: Sequence[float]) -> None:
    """Change the full-height curve of a shown trace instantly (e.g. when the
    composite's scale changes), without disturbing a running grow/shrink."""
    _preview(plot, index, 'rescale', y=y)