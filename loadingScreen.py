"""Loading screen: a still panel on the home page and an animated overlay on project pages.

Put the two files exported from Blender in your static folder:

    static/loading/0001.png ...   PNG frame sequence (any number of digits, any count),
                                  played in a loop as the loading animation
    static/loading/panel.webp     still image, fades in on the home page
    static/loading/loading.webp   looping animation, shown on a project page until its
                                  graph is ready (animated WebP, transparent background)

All are optional. With no panel.webp the home page simply has no panel. The loading
screen uses the PNG frames if present, else loading.webp, else a plain spinner, so everything works before the
artwork exists.

Usage:
    home page:     home_panel()                (inside the container the panel sits in)
                   install_home_loader()       (once, near the top of the page function)
    project page:  install_project_loader()    (once, near the top of the page function)

The home panel is frame 0001 and fades in. The overlay on a project page is part of its
first paint and fully visible from the start (no fade-in), showing frame 0001 and then
playing, so the handoff from the still is seamless. On a project page, graph_entrance.py hides it (via window.__skewLoaderHide)
the moment the graph is ready, and the curves then draw in underneath as it fades away.

On the home page the loader only appears when you arrive from a project page (the logo
button, or any other way home). That is detected from the page you came from, so a first
visit or a refresh goes straight to the home page. It fades out once the page is ready.
"""

import json

from nicegui import ui

import theme

ASSET_DIR = 'loading'
PANEL_FILE = f'{ASSET_DIR}/panel.webp'
ANIMATION_FILE = f'{ASSET_DIR}/loading.webp'

FRAME_FPS = 24            # playback speed of the PNG frame sequence
PANEL_HEIGHT = 150        # px: height of the home page panel (width follows the image)
ANIMATION_WIDTH = 320     # px: width of the loading animation (never more than 60% of the screen)
PANEL_FADE_MS = 900       # home panel fade-in
LOADER_FADE_MS = 450      # loading screen fade-out
LEAVE_FADE_MS = 450       # frame 0001 fading in over a page that is being left
MIN_VISIBLE_MS = 900      # show the loader at least this long, so a fast load doesn't flash it
MAX_VISIBLE_MS = 20_000   # safety net: never keep the loader up longer than this

P = theme.PALETTE


def _asset_url(relative: str) -> str | None:
    """URL of a file in the static folder (None if it isn't there).

    The file's modified time is added so a re-exported file isn't served from cache.
    """
    path = theme.STATIC_DIR / relative
    if not path.is_file():
        return None
    return f'/static/{relative}?v={int(path.stat().st_mtime)}'


def _frame_urls() -> list[str]:
    """URLs of the numbered PNG frames (0001.png, 0002.png, ...) in numeric order."""
    folder = theme.STATIC_DIR / ASSET_DIR
    if not folder.is_dir():
        return []
    frames = sorted((f for f in folder.glob('*.png') if f.stem.isdigit()),
                    key=lambda f: int(f.stem))
    return [f'/static/{ASSET_DIR}/{f.name}?v={int(f.stat().st_mtime)}' for f in frames]


_FRAMES_JS = r'''<script>
(() => {
    const frames = __FRAMES__;
    const FPS = __FPS__;
    const img = document.querySelector('#skew-loader img');
    if (!img || frames.length < 2) return;

    // Preload every frame so playback never stalls on the network.
    const loaded = frames.map(src => {
        const image = new Image();
        image.src = src;
        return image;
    });

    let start = null;
    let shown = -1;
    function tick(now) {
        if (start === null) start = now;
        if (!img.isConnected) return;   // loader was removed: stop
        let index = Math.floor((now - start) / 1000 * FPS) % frames.length;
        // Only swap to a frame that has finished loading.
        if (index !== shown && loaded[index].complete && loaded[index].naturalWidth) {
            img.src = frames[index];
            shown = index;
        }
        requestAnimationFrame(tick);
    }
    // Frame 0001 stays up until every frame is ready, then playback starts from the top.
    const ready = Promise.all(loaded.map(image => new Promise(resolve => {
        if (image.complete) return resolve();
        image.addEventListener('load', resolve, {once: true});
        image.addEventListener('error', resolve, {once: true});
    })));
    Promise.race([ready, new Promise(resolve => setTimeout(resolve, 4000))])
        .then(() => requestAnimationFrame(tick));
})();
</script>'''


def first_frame_url() -> str | None:
    """URL of frame 0001 (None if there are no numbered frames)."""
    frames = _frame_urls()
    return frames[0] if frames else None


# Leaving a page: frame 0001 fades in over it, then the next page loads.

_FADE_NAVIGATE_JS = r'''<script>
(() => {
    if (window.__skewFadeNavigate) return;
    let leaving = false;

    window.__skewFadeNavigate = (url) => {
        if (leaving) return;
        leaving = true;

        const veil = document.createElement('div');
        veil.style.cssText =
            'position:fixed; inset:0; z-index:2147483647; pointer-events:all; ' +
            'display:flex; align-items:center; justify-content:center; ' +
            'background:__PAGE__; opacity:0; transition:opacity __MS__ms ease;';
        // Frame 0001, in the same place and size as the loading animation on the
        // next page, so that page picks up exactly where this one stops.
        const frame = __FRAME__;
        if (frame) {
            const img = document.createElement('img');
            img.src = frame;
            img.alt = '';
            img.draggable = false;
            img.style.cssText = 'width:__W__px; max-width:60vw; height:auto; ' +
                'user-select:none; pointer-events:none;';
            veil.appendChild(img);
        }
        document.body.appendChild(veil);

        const go = () => { window.location.href = url; };
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return go();

        requestAnimationFrame(() => requestAnimationFrame(() => { veil.style.opacity = '1'; }));
        setTimeout(go, __MS__);
    };

    const sameSite = (url) => {
        try { return new URL(url, location.href).origin === location.origin; }
        catch (error) { return false; }
    };

    // Same-page navigations started by the server (ui.navigate.to, used by the logo,
    // the projects drawer, ...) end up in window.open(url, '_self'). Fade first.
    const nativeOpen = window.open.bind(window);
    window.open = (url, target, ...rest) => {
        if (url && (!target || target === '_self') && sameSite(url)
                && new URL(url, location.href).href !== location.href) {
            window.__skewFadeNavigate(new URL(url, location.href).href);
            return null;
        }
        return nativeOpen(url, target, ...rest);
    };

    // Plain links to another page of this site.
    document.addEventListener('click', (event) => {
        const link = event.target.closest && event.target.closest('a[href]');
        if (!link || event.defaultPrevented || event.button !== 0
                || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
                || (link.target && link.target !== '_self') || link.hasAttribute('download')
                || !sameSite(link.href)) return;
        const target = new URL(link.href);
        if (target.pathname === location.pathname && target.search === location.search) return;
        event.preventDefault();
        window.__skewFadeNavigate(target.href);
    });

    // Back/forward cache: start from a clean page.
    window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });
})();
</script>'''


def install_fade_navigate() -> None:
    """Fade frame 0001 in over this page before any navigation to another page of the site.

    Called by both loaders below, so every page that has a loader also fades out.
    Safe to call more than once.
    """
    ui.add_head_html(
        _FADE_NAVIGATE_JS
        .replace('__PAGE__', P['page'])
        .replace('__MS__', str(LEAVE_FADE_MS))
        .replace('__FRAME__', json.dumps(first_frame_url()))
        .replace('__W__', str(ANIMATION_WIDTH)))
    url = first_frame_url()
    if url is not None:
        ui.add_head_html(f'<link rel="preload" as="image" href="{url}">')


def fade_to(url: str) -> None:
    """Fade out, then navigate (call from a server-side handler)."""
    ui.run_javascript(f'window.__skewFadeNavigate({json.dumps(url)})')


# Home page panel

def home_panel() -> None:
    """Add the still panel, fading in once its image has loaded.

    The panel is positioned against the nearest `position: relative` parent (right edge,
    vertically centered), so it doesn't change the layout of anything else. It is hidden
    on narrow screens.
    """
    # Frame 0001 of the sequence, so the loader on the next page starts on the same image.
    # (panel.webp is only used if there are no frames.)
    frames = _frame_urls()
    url = frames[0] if frames else _asset_url(PANEL_FILE)
    if url is None:
        print(f'[loading] no home panel: put frames in static/{ASSET_DIR}/ (0001.png, ...)')
        return

    ui.add_css(f'''
        .skew-home-panel {{
            position: absolute; right: 0; top: 50%; transform: translateY(-50%);
            height: {PANEL_HEIGHT}px; width: auto; max-width: 45%; object-fit: contain;
            pointer-events: none; user-select: none;
            /* Multiply blends the frame's page-colored background into the tinted band,
               so no box shows around the logo. Dark artwork is unaffected. */
            mix-blend-mode: multiply;
            opacity: 0; transition: opacity {PANEL_FADE_MS}ms ease-out;
        }}
        .skew-home-panel.is-loaded {{ opacity: 1; }}
        @media (max-width: 720px) {{ .skew-home-panel {{ display: none; }} }}
        @media (prefers-reduced-motion: reduce) {{ .skew-home-panel {{ transition: none; }} }}
    ''')
    # Start the fade only once the image has arrived, so a slow download doesn't skip it.
    ui.add_head_html('''<script>
        document.addEventListener('load', event => {
            const el = event.target;
            if (el.classList && el.classList.contains('skew-home-panel'))
                requestAnimationFrame(() => el.classList.add('is-loaded'));
        }, true);
    </script>''')
    ui.element('img').classes('skew-home-panel').props(f'src="{url}" alt="" draggable="false"')


# Loading screen (project pages, and the home page when coming back from a project)

_LOADER_JS = r'''<script>
(() => {
    if (window.__skewLoaderInstalled) return;
    window.__skewLoaderInstalled = true;

    const MODE = __MODE__;                     // 'always' or 'from-project'
    const READY_SELECTOR = __READY_SELECTOR__; // 'from-project' only: element that means "page built"
    const MIN_VISIBLE = __MIN_VISIBLE__;
    const FADE = __FADE__;
    const MAX_VISIBLE = __MAX_VISIBLE__;

    // Did we just come from a project page of this site?
    const fromProject = (() => {
        try {
            if (!document.referrer) return false;
            const previous = new URL(document.referrer);
            return previous.origin === location.origin && previous.pathname.startsWith('/project/');
        } catch (error) { return false; }
    })();
    if (MODE !== 'always' && !fromProject) return;

    // Shows the overlay (hidden by default) from the very first paint.
    document.documentElement.classList.add('skew-loader-on');

    const shownAt = performance.now();
    let hiding = null;

    // Fades the loader out and resolves once it is gone. Safe to call more than once.
    window.__skewLoaderHide = () => {
        if (hiding) return hiding;
        hiding = new Promise(resolve => {
            const wait = Math.max(0, MIN_VISIBLE - (performance.now() - shownAt));
            setTimeout(() => {
                const loader = document.getElementById('skew-loader');
                if (!loader) { resolve(); return; }
                loader.classList.add('skew-loader-hide');
                setTimeout(() => {
                    loader.remove();
                    document.documentElement.classList.remove('skew-loader-on');
                    resolve();
                }, FADE);
            }, wait);
        });
        return hiding;
    };

    // Safety nets, so the loader can never get stuck on screen:
    //  - too long: hide it;
    //  - graph_entrance.py missing from this page: hide it once a curve has been drawn.
    const poll = setInterval(() => {
        if (hiding) { clearInterval(poll); return; }
        const elapsed = performance.now() - shownAt;
        const drawn = document.querySelector('.js-plotly-plot .scatterlayer .trace .js-line');
        if (elapsed > MAX_VISIBLE
                || (MODE === 'always' && !window.__skewGraphEntranceInstalled && drawn && elapsed > 1500)) {
            clearInterval(poll);
            window.__skewLoaderHide();
        }
    }, 200);

    // Pages without a graph: hide it once the page has fully loaded and settled.
    if (MODE !== 'always') {
        (async () => {
            const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
            if (document.readyState !== 'complete')
                await new Promise(resolve => window.addEventListener('load', resolve, {once: true}));
            if (document.fonts && document.fonts.ready) {
                try { await document.fonts.ready; } catch (error) {}
            }
            const start = performance.now();
            while (!document.querySelector(READY_SELECTOR) && performance.now() - start < 8000)
                await sleep(50);
            const pending = Array.from(document.images)
                .filter(image => !image.complete && !image.closest('#skew-loader'))
                .map(image => new Promise(resolve => {
                    image.addEventListener('load', resolve, {once: true});
                    image.addEventListener('error', resolve, {once: true});
                }));
            await Promise.race([Promise.all(pending), sleep(5000)]);
            await sleep(250);
            window.__skewLoaderHide();
        })();
    }
})();
</script>'''


def _install_loader(mode: str, ready_selector: str = '') -> None:
    install_fade_navigate()   # fade out when leaving this page, too
    frames = _frame_urls()
    url = frames[0] if frames else _asset_url(ANIMATION_FILE)
    if url is None:
        print(f'[loading] no animation: put PNG frames (0001.png, ...) in static/{ASSET_DIR}/ '
              f'(showing a spinner)')
        picture = '<div class="skew-spinner"></div>'
    else:
        picture = f'<img src="{url}" alt="" draggable="false">'

    ui.add_css(f'''
        #skew-loader {{
            display: none;
            position: fixed; inset: 0; z-index: 10000;
            align-items: center; justify-content: center;
            background: {P['page']}; opacity: 1;
            transition: opacity {LOADER_FADE_MS}ms ease;
        }}
        /* No fade-in: the loader is fully visible from the first paint. */
        html.skew-loader-on #skew-loader {{ display: flex; }}
        #skew-loader.skew-loader-hide {{ opacity: 0; pointer-events: none; }}
        #skew-loader img {{
            width: {ANIMATION_WIDTH}px; max-width: 60vw; height: auto;
            user-select: none; pointer-events: none;
        }}
        .skew-spinner {{
            width: 40px; height: 40px; border-radius: 50%;
            border: 3px solid {P['border']}; border-top-color: {P['ink']};
            animation: skew-spin 0.9s linear infinite;
        }}
        @keyframes skew-spin {{ to {{ transform: rotate(360deg); }} }}
    ''')
    if url is not None:
        ui.add_head_html(f'<link rel="preload" as="image" href="{url}">')
    ui.add_head_html(
        _LOADER_JS
        .replace('__MODE__', json.dumps(mode))
        .replace('__READY_SELECTOR__', json.dumps(ready_selector))
        .replace('__MIN_VISIBLE__', str(MIN_VISIBLE_MS))
        .replace('__FADE__', str(LOADER_FADE_MS))
        .replace('__MAX_VISIBLE__', str(MAX_VISIBLE_MS)))
    # Added to the page's own HTML (not built later by the UI), so it is there from the first paint.
    ui.add_body_html(f'<div id="skew-loader" role="status" aria-label="Loading">{picture}</div>')
    if len(frames) > 1:
        # After the overlay element, so the script can find its <img>.
        ui.add_body_html(_FRAMES_JS
                         .replace('__FRAMES__', json.dumps(frames))
                         .replace('__FPS__', str(FRAME_FPS)))


def install_project_loader() -> None:
    """Cover the project page with the loading animation until the graph is ready."""
    _install_loader('always')


def install_home_loader() -> None:
    """Cover the home page with the loading animation when arriving from a project page."""
    _install_loader('from-project', ready_selector='.new-band')