import click
import pandas as pd

from smos.smos_l4.reshuffle_l4 import reshuffle
from smos.grid import EASE25CellGrid
from smos.misc import get_first_last_day_images


@click.command(
    "reshuffle",
    context_settings={'show_default': True},
    short_help="Convert SMOS L4 RZSM images into time series.")
@click.argument("img_path", type=click.Path(readable=True))
@click.argument("ts_path", type=click.Path(writable=True))
@click.option(
    '--startdate',
    '-s',
    type=click.STRING,
    default=None,
    help="Format YYYY-MM-DD | First day to include in the "
    "time series. [default: Date of the first available image]")
@click.option(
    '--enddate',
    '-e',
    type=click.STRING,
    default=None,
    help="Format YYYY-MM-DD | Last day to include in the "
    "time series. [default: Date of the last available image]")
@click.option(
    '--parameters',
    '-v',
    type=click.STRING,
    default=None,
    help="Variables in the image files to reshuffle. Multiple variables "
    "must be comma-separated. [default: all variables]")
@click.option(
    '--quality_range',
    '-q',
    type=click.FLOAT,
    nargs=2,
    default=(0, 1),
    help="LOWER UPPER | Only keep observations where the quality variable "
    "(QUAL for the scientific product: 0-1, 1 is the highest quality; "
    "Quality for the operational product: -1 missing, 0 not "
    "recommended, 1 OK) is within this range (thresholds included). "
    "The default only removes missing data, use e.g. 1 1 to only keep "
    "the best quality.")
@click.option(
    '--bbox',
    type=click.FLOAT,
    nargs=4,
    default=None,
    help="min_lon min_lat max_lon max_lat. Bounding Box (lower left and "
    "upper right corner) of the area to reshuffle. [default: global]")
@click.option('--only_land', is_flag=True, help="Only reshuffle land points.")
@click.option(
    '--imgbuffer',
    '-b',
    type=click.INT,
    default=100,
    help="Number of images to read into memory before writing time series. "
    "A larger buffer means faster processing but more memory usage.")
def cli_reshuffle(img_path, ts_path, startdate, enddate, parameters,
                  quality_range, bbox, only_land, imgbuffer):
    """
    Convert SMOS L4 RZSM image data (scientific or operational product, this
    is detected from the files) into a (5x5 degrees chunked) time series
    format. To read the generated time series data, use the
    `smos.interface.SMOSTs` class.

    \b
    Required Parameters
    -------------------
    IMG_PATH: string
        Path to the SMOS L4 images (with yearly subfolders)
    TS_PATH: string
        Path where the newly created time series files should be stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.
    first_day, last_day = get_first_last_day_images(img_path)
    startdate = pd.to_datetime(startdate or first_day).to_pydatetime()
    enddate = pd.to_datetime(enddate or last_day).to_pydatetime()
    if parameters is not None:
        parameters = [str(v.strip()) for v in parameters.split(',')]

    print(f"Convert image data in {img_path} to time series in {ts_path}")
    grid = EASE25CellGrid(
        bbox=tuple(bbox) if len(bbox or []) == 4 else None,
        only_land=only_land)
    reshuffle(
        img_path,
        ts_path,
        startdate,
        enddate,
        imgbuffer=imgbuffer,
        grid=grid,
        parameters=parameters,
        read_flags=tuple(quality_range))


@click.group(short_help="SMOS L4 RZSM Command Line Programs.", name="l4")
def smos_l4():
    pass


smos_l4.add_command(cli_reshuffle)
