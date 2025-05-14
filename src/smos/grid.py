# -*- coding: utf-8 -*-

from pygeogrids.grids import CellGrid, BasicGrid, lonlat2cell
from ease_grid import EASE2_grid
import numpy as np
from netCDF4 import Dataset
import os


class EASE25CellGrid(CellGrid):
    """ CellGrid version of EASE25 Grid as used in SMOS IC """

    def __init__(self, bbox=None, only_land=False):
        """
        Parameters
        ----------
        bbox: tuple, optional (default: None)
            (min_lon, min_lat, max_lon, max_lat)
            Bounding box to create subset for, if None is passed a global
            grid is used.
        only_land: bool, optional (default: False)
            If True, restrict the grid to land points only.
        """

        ease25 = EASE2_grid(25000)
        glob_lons, glob_lats = ease25.londim, ease25.latdim

        lons, lats = np.meshgrid(glob_lons, glob_lats)
        assert lons.shape == lats.shape
        shape = lons.shape

        lats = np.flipud(lats)  # flip lats, so that origin in bottom left

        globgrid = BasicGrid(lons.flatten(), lats.flatten(), shape=shape)

        self.bbox = bbox
        self.cellsize = 5.

        # Start with global grid
        grid = globgrid
        sgpis = globgrid.activegpis
        params = {'subset': sgpis}
        land_mask = None

        # Get land mask if needed
        if only_land:
            mask_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 
                                   "Grid_Point_Mask_USGS.nc")
            with Dataset(mask_path) as ds:
                land_mask = ds.variables["USGS_Land_Flag"][:].flatten().filled() == 0.0

        # Special handling when both land-only and bbox are specified
        if only_land and self.bbox:
            # Get land points from global grid
            land_points = np.ma.masked_array(globgrid.get_grid_points()[0], land_mask)
            land_sgpis = globgrid.activegpis[~land_points.mask]

            # Get bbox points from global grid
            bbox_sgpis = globgrid.get_bbox_grid_points(
                latmin=self.bbox[1],
                latmax=self.bbox[3],
                lonmin=self.bbox[0],
                lonmax=self.bbox[2]
            )

            # Create intersection of land points and bbox points
            # (points that are both on land AND within bbox)
            intersection = np.intersect1d(land_sgpis, bbox_sgpis)

            # Use global grid with the intersection as subset
            grid = globgrid
            sgpis = intersection
            params = {'subset': sgpis}
            shape = (len(sgpis),)

        # Apply original land mask if only_land is True but no bbox is specified
        elif only_land:
            land_points = np.ma.masked_array(globgrid.get_grid_points()[0], land_mask)
            grid = globgrid.subgrid_from_gpis(land_points[~land_points.mask].filled())
            sgpis = grid.activegpis
            shape = grid.shape
            params = {}

        # Apply original bbox filter if only bbox is specified (no land mask)
        elif self.bbox:
            bbox_sgpis = grid.get_bbox_grid_points(
                latmin=self.bbox[1],
                latmax=self.bbox[3],
                lonmin=self.bbox[0],
                lonmax=self.bbox[2]
            )
            sgpis = bbox_sgpis
            params = {'subset': sgpis}

        # Set final grid parameters
        self.grid = grid
        self.subset = sgpis
        self.shape = shape

        super().__init__(lon=grid.arrlon,
                         lat=grid.arrlat,
                         cells=lonlat2cell(grid.arrlon, grid.arrlat,
                                           self.cellsize),
                         shape=shape,
                         **params)

        if only_land:
            self.subset_shape = shape
        else:
            self.subset_shape = (len(np.unique(self.activearrlat)),
                                 len(np.unique(self.activearrlon)))


    def cut(self) -> CellGrid:
        # create a new grid from the active subset
        return BasicGrid(lon=self.activearrlon,
                         lat=self.activearrlat,
                         gpis=self.activegpis,
                         subset=None,
                         shape=self.subset_shape).to_cell_grid(self.cellsize)
