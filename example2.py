import serve_figure

import numpy as np
from numpy import ma
from matplotlib import pyplot as plt

n = 30

x = np.linspace(-1.5,1.5,n)

fig = plt.figure()
ax = fig.add_subplot(111)
ax.set_axis_bgcolor("#bdb76b")
ax.plot(x, np.sin(x))
ax.set_title('Without masked values')

serve_figure.serve_figure(fig, port=8888)
