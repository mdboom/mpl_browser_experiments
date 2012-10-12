import serve_figure

import numpy as np
from numpy import ma
from matplotlib import pyplot as plt

n = 12

x = np.linspace(-1.5,1.5,n)
y = np.linspace(-1.5,1.5,n*2)
X,Y = np.meshgrid(x,y);
Qx = np.cos(Y) - np.cos(X)
Qz = np.sin(Y) + np.sin(X)
Qx = (Qx + 1.1)
Z = np.sqrt(X**2 + Y**2)/5;
Z = (Z - Z.min()) / (Z.max() - Z.min())

# The color array can include masked values:
Zm = ma.masked_where(np.fabs(Qz) < 0.5*np.amax(Qz), Z)

fig = plt.figure()
ax = fig.add_subplot(121)
ax.set_axis_bgcolor("#bdb76b")
ax.pcolormesh(Qx,Qz,Z, shading='gouraud')
ax.set_title('Without masked values')

ax = fig.add_subplot(122)
ax.set_axis_bgcolor("#bdb76b")
col = ax.pcolormesh(Qx,Qz,Zm,shading='gouraud')
ax.set_title('With masked values')

serve_figure.serve_figure(fig, port=8888)
