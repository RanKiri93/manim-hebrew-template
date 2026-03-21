from manim import Scene, Axes, Create, Dot

import numpy as np

class AxesScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-2, 2, 0.5],
            y_range=[-4, 4, 1],
            x_length=4,
            y_length=5,
            axis_config={"include_tip": True},
        )

        def f0(x):
            return x**2
        graph0 = axes.plot(f0, color="#d4a84b")
        def f1(x):
            return x+1
        graph1 = axes.plot(f1, color="#d4a84b")
        dot0 = Dot(axes.c2p(1, 0), color="#e55555", radius=0.08)
        self.play(Create(axes))
        self.play(Create(graph0))
        self.play(Create(graph1))
        self.play(Create(dot0))