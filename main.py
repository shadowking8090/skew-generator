from nicegui import ui

ui.label('Hackathon Project')

ui.button('Click Me', on_click=lambda: ui.notify('Hello World!'))

ui.run()
