import plotly.graph_objects as go

class Data:
    def __init__(self, histogram: go.Figure, name: str, color: str):
        self.histogram = histogram
        self.name = name
        self.color = color

    

