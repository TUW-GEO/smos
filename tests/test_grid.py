# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2019,TU Wien
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
Tests for the EASE2 25km grid as used in the SMOS data
    origin=BottomLeft=(-179.870, -83.5171)
'''

import numpy.testing as nptest
from smos.grid import EASE25CellGrid
import numpy as np


def test_EASE25CellGrid():
    grid = EASE25CellGrid()
    gpis, lons, lats, cells = grid.get_grid_points()
    nptest.assert_almost_equal(np.array([gpis[0], lons[0], lats[0]]),
                               np.array([0, -179.8703, -83.5171]), 4)
    assert grid.activegpis.size == (584 * 1388)
    assert grid.activegpis[316922] == 316922
    nptest.assert_almost_equal(grid.activearrlat[316922], -12.55398284007352, 5)
    nptest.assert_almost_equal(grid.activearrlon[316922], -61.08069164265129, 5)
    assert grid.activearrcell[316922] == 843
