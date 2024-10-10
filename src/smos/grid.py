# -*- coding: utf-8 -*-
import os

from pygeogrids.grids import CellGrid, BasicGrid, lonlat2cell
from pygeogrids.netcdf import load_grid

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

        self.subset_shape = (len(np.unique(self.activearrlat)),
                             len(np.unique(self.activearrlon)))

    def cut(self) -> CellGrid:
        # create a new grid from the active subset
        return BasicGrid(lon=self.activearrlon, lat=self.activearrlat,
                         gpis=self.activegpis, subset=None,
                         shape=self.subset_shape).to_cell_grid(self.cellsize)


ISEA_GRID_FILE = path_config = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "../grid_definition_files/SMOSL2_grid.nc"
)


class ISEA4h9CellGrid:
    """ CellGrid version of ISEA 4h9 Grid as used in SMOS L2 """

    def __init__(self, isea_grid_file=ISEA_GRID_FILE, bbox=None):

        if isea_grid_file is None:
            # use formula of grid definition
            raise NotImplementedError(
                "Here a formula for the ISEA 4h9 grid could be passed, to avoid"
                " relaying on the grid file."
            )

        else:
            self.isea_cellgrid = load_grid(isea_grid_file)

        self.bbox = bbox
        if self.bbox:
            sgpis = self.get_bbox_grid_points(
                latmin=self.bbox[1], latmax=self.bbox[3],
                lonmin=self.bbox[0], lonmax=self.bbox[2])

            self.isea_cellgrid = self.subgrid_from_gpis(sgpis)

        self.subset_shape = (
            len(np.unique(self.activearrlat)),
            len(np.unique(self.activearrlon))
        )

    def __getattr__(self, attr):
        # inherit the attributes of the cellgrid directly, so they can be
        # called from the main instance
        return getattr(self.isea_cellgrid, attr)

    def cut(self) -> CellGrid:
        # create a new grid from the active subset
        return self.isea_cellgrid
