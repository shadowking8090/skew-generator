import plotly.graph_objects as go


class Data:
    def __init__(self, trace: go.Scatter | go.Figure, name: str, color: str):
        self.trace = trace
        self.name = name
        self.color = color