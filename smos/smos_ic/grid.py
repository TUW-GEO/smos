# -*- coding: utf-8 -*-

from pygeogrids import BasicGrid
from ease_grid import EASE2_grid
import numpy as np

def EASE25CellGrid():
    ease25 = EASE2_grid(25000)
    lons, lats = np.meshgrid(ease25.londim, ease25.latdim)
    lats = np.flipud(lats) # flip lats, so that origin in bottom left
    grid = BasicGrid(lons.flatten(), lats.flatten(),
                     shape=(ease25.londim.size, ease25.latdim.size)).to_cell_grid(5., 5.)

    return grid
