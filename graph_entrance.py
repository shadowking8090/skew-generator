"""Smooth, sequential entrance animation for NiceGUI Plotly graphs."""

from nicegui import ui


def install_graph_loading(duration_ms: int = 2050) -> None:
    duration_ms = max(350, int(duration_ms))

    ui.add_css('''
        .js-plotly-plot:not([data-skew-entrance-ready])
        .scatterlayer > .trace {
            opacity: 0 !important;
        }
    ''')

    javascript = r'''<script>
    (() => {
        if (window.__skewGraphEntranceInstalled) return;
        window.__skewGraphEntranceInstalled = true;

        const DURATION = __DURATION_MS__;
        const SETTLE_MS = 450;

        const reducedMotion = window.matchMedia(
            '(prefers-reduced-motion: reduce)'
        ).matches;

        function chartIsReady(plot) {
            return Boolean(
                plot._fullLayout &&
                plot.querySelector(
                    '.scatterlayer .trace .js-line, ' +
                    '.scatterlayer .trace .js-fill'
                )
            );
        }

        function animateChart(plot) {
            if (plot.dataset.skewEntranceReady) return;

            const traces = Array.from(
                plot.querySelectorAll('.scatterlayer > .trace')
            ).filter(trace =>
                trace.querySelector('.js-line, .js-fill')
            );

            plot.dataset.skewEntranceReady = 'true';

            if (reducedMotion) return;

            // Linear easing makes both curves draw
            // at a consistent, natural speed.
            const easing = 'linear';

            // Identify curves by their Plotly names.
            const visibleData = (plot._fullData || []).filter(
                data =>
                    data.type === 'scatter' &&
                    data.visible !== false &&
                    data.visible !== 'legendonly'
            );

            const referenceIndex = visibleData.findIndex(
                data => data.name === 'Perfect Normal'
            );

            const compositeIndex = visibleData.findIndex(
                data => data.name === 'Composite'
            );

            const reference = traces[
                referenceIndex >= 0 ? referenceIndex : 1
            ];

            const composite = traces[
                compositeIndex >= 0 ? compositeIndex : 0
            ];

            // ANIMATION TIMING
            //
            // Dotted line starts first.
            // Composite starts when dotted line is 70% done.
            // Composite continues smoothly until the end.

            const referenceDuration = Math.round(
                DURATION * 0.40
            );

            const compositeDelay = Math.round(
                referenceDuration * 0.70
            );

            const compositeDuration =
                DURATION - compositeDelay;

            function draw(trace, delay, duration) {
                if (!trace) return;

                const finalOpacity =
                    getComputedStyle(trace).opacity;

                trace.animate([
                    {
                        opacity: 0,
                        clipPath: 'inset(0 100% 0 0)'
                    },
                    {
                        opacity: finalOpacity,
                        clipPath: 'inset(0 0 0 0)'
                    }
                ], {
                    duration,
                    delay,
                    easing,
                    fill: 'backwards'
                });
            }

            // 1. Dotted Perfect Normal line
            draw(
                reference,
                0,
                referenceDuration
            );

            // 2. Composite distribution
            if (composite !== reference) {
                draw(
                    composite,
                    compositeDelay,
                    compositeDuration
                );
            }

            // 3. Any additional visible curves
            traces.filter(trace =>
                trace !== reference &&
                trace !== composite
            ).forEach((trace, index) => {
                draw(
                    trace,
                    DURATION + index * 70,
                    380
                );
            });
        }

        async function waitForPage() {
            // Wait until the entire page loads.
            if (document.readyState !== 'complete') {
                await new Promise(resolve =>
                    window.addEventListener(
                        'load',
                        resolve,
                        {once: true}
                    )
                );
            }

            // Wait for custom fonts.
            if (document.fonts && document.fonts.ready) {
                await document.fonts.ready;
            }

            let lastChange = performance.now();
            let observer = null;
            let finished = false;

            const begin = performance.now();

            function tryStart() {
                if (finished) return;

                const plots = Array.from(
                    document.querySelectorAll('.js-plotly-plot')
                ).filter(plot =>
                    !plot.dataset.skewEntranceReady
                );

                if (
                    !plots.length ||
                    !plots.every(chartIsReady)
                ) {
                    return;
                }

                // Wait for the page to settle.
                if (
                    performance.now() - lastChange < SETTLE_MS
                ) {
                    return;
                }

                finished = true;

                if (observer) {
                    observer.disconnect();
                }

                // If a loading screen is up (see loading_screen.py), fade it out
                // first, then draw the curves into the revealed page.
                const loaderGone = window.__skewLoaderHide
                    ? window.__skewLoaderHide()
                    : Promise.resolve();

                // Start after two browser rendering frames.
                loaderGone.then(() =>
                    requestAnimationFrame(() =>
                        requestAnimationFrame(() => {
                            plots.forEach(animateChart);
                        })
                    )
                );
            }

            observer = new MutationObserver(() => {
                lastChange = performance.now();
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            const ticker = window.setInterval(() => {
                tryStart();

                if (
                    finished ||
                    performance.now() - begin > 15000
                ) {
                    window.clearInterval(ticker);

                    if (observer) {
                        observer.disconnect();
                    }

                    // Never leave the graph hidden (or the loading screen up).
                    if (!finished) {
                        if (window.__skewLoaderHide) window.__skewLoaderHide();
                        document.querySelectorAll(
                            '.js-plotly-plot'
                        ).forEach(plot => {
                            plot.dataset.skewEntranceReady = 'true';
                        });
                    }
                }
            }, 100);

            tryStart();
        }

        waitForPage();
    })();
    </script>'''

    ui.add_head_html(
        javascript.replace(
            '__DURATION_MS__',
            str(duration_ms)
        )
    )


def animate_graph_loading(
    plot,
    duration_ms: int = 4050
) -> None:
    """Compatibility helper for direct Plotly chart calls."""
    install_graph_loading(duration_ms)