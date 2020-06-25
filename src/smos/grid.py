# -*- coding: utf-8 -*-

from pygeogrids.grids import CellGrid, BasicGrid, lonlat2cell
from ease_grid import EASE2_grid
import numpy as np


class EASE25CellGrid(CellGrid):
    """ CellGrid version of EASE25 Grid as used in SMOS IC """

    def __init__(self, bbox=None):
        """
        Parameters
        ----------
        bbox: tuple, optional (default: None)
            (min_lon, min_lat, max_lon, max_lat)
            Bounding box to create subset for, if None is passed a global
            grid is used.
        """

        ease25 = EASE2_grid(25000)
        lons, lats = ease25.londim, ease25.latdim

        lons, lats = np.meshgrid(lons, lats)
        assert lons.shape == lats.shape
        shape = lons.shape

        lats = np.flipud(lats)  # flip lats, so that origin in bottom left
        lons, lats = lons.flatten(), lats.flatten()

        globgrid = BasicGrid(lons, lats, shape=shape)
        sgpis = globgrid.activegpis

        self.bbox = bbox
        if self.bbox:
            sgpis = globgrid.get_bbox_grid_points(
                latmin=self.bbox[1], latmax=self.bbox[3],
                lonmin=self.bbox[0], lonmax=self.bbox[2])

        self.cellsize = 5.

        super(EASE25CellGrid, self).__init__(lon=globgrid.arrlon,
                                             lat=globgrid.arrlat,
                                             subset=sgpis,
                                             cells=lonlat2cell(globgrid.arrlon,
                                                               globgrid.arrlat,
                                                               self.cellsize),
                                             shape=shape)

        self.subset_shape = (len(np.unique(self.activearrlon)),
                             len(np.unique(self.activearrlat)))

    def cut(self) -> CellGrid:
        # create a new grid from the active subset
        return BasicGrid(lon=self.activearrlon, lat=self.activearrlat,
                         gpis=self.activegpis, subset=None,
                         shape=self.subset_shape).to_cell_grid(self.cellsize)
