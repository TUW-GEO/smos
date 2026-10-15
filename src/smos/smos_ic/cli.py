import click
import pandas as pd

from smos.smos_ic.download import SmosIcHttp, IC_START_DATE, IC_ORBITS
from smos.smos_ic.reshuffle_ic import reshuffle
from smos.grid import EASE25CellGrid
from smos.misc import read_summary_yml, get_first_last_day_images


def _parse_orbits(orbits):
    return [o.strip().upper() for o in orbits.split(',')]


@click.command(
    "download",
    context_settings={'show_default': True},
    short_help="Download SMOS IC data from the CATDS server. This requires "
    "that the `lftp` program is installed on your system: "
    "https://lftp.yar.ru/")
@click.argument("path", type=click.Path(writable=True))
@click.option(
    '--startdate',
    '-s',
    type=click.STRING,
    default=str(IC_START_DATE.date()),
    help="Startdate in format YYYY-MM-DD. If not given, "
    "then the first available date of the product is used.")
@click.option(
    '--enddate',
    '-e',
    type=click.STRING,
    default=None,
    help="Enddate in format YYYY-MM-DD. If not given, "
    "then the last available day on the server is used.")
@click.option(
    '--orbits',
    '-o',
    type=click.STRING,
    default=','.join(IC_ORBITS),
    help="Overpasses to download, ASC and/or DES. Multiple orbits "
    "must be comma-separated.")
def cli_download(
    path,
    startdate,
    enddate,
    orbits,
):
    """
    Download SMOS IC data within a chosen period. No account is required.
    Data for each orbit is stored in a separate subfolder (ASC, DES).

    \b
    Required Parameters
    -------------------
    PATH: string (required)
        Path where the downloaded images are stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.

    http = SmosIcHttp(path, orbits=_parse_orbits(orbits))

    if enddate is None:
        enddate = http.last_available_day()

    http.sync_period(
        startdate=pd.to_datetime(startdate).to_pydatetime(), enddate=enddate)


@click.command(
    "update_img",
    context_settings={'show_default': True},
    short_help="Extend an existing record by downloading new files. "
    "This requires that the `lftp` program is installed on your "
    "system: https://lftp.yar.ru/")
@click.argument("path", type=click.Path(writable=True))
@click.option(
    '--orbits',
    '-o',
    type=click.STRING,
    default=','.join(IC_ORBITS),
    help="Overpasses to update, ASC and/or DES. Multiple orbits "
    "must be comma-separated.")
def cli_update_img(path, orbits):
    """
    Extend a locally existing SMOS IC record by downloading new files that
    don't yet exist locally.
    NOTE: SMOS IC is not an operational product, i.e. new data is only
    available after a new version was released.
    NOTE: Use the `smos ic download` program first do create a local record
    to update with this function.

    \b
    Required Parameters
    -------------------
    PATH: string
        Path where previously downloaded SMOS IC images are stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.

    http = SmosIcHttp(path, orbits=_parse_orbits(orbits))
    startdate = read_summary_yml(path)['last_day']
    if startdate is None:
        raise ValueError(f"No local data found in {path}. "
                         f"Use `smos ic download` first.")
    enddate = http.last_available_day()
    http.sync_period(startdate=startdate, enddate=enddate)


@click.command(
    "reshuffle",
    context_settings={'show_default': True},
    short_help="Convert SMOS IC images into time series.")
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
def cli_reshuffle(img_path, ts_path, startdate, enddate, parameters, bbox,
                  only_land, imgbuffer):
    """
    Convert SMOS IC image data of one orbit into a (5x5 degrees chunked)
    time series format. To read the generated time series data, use the
    `smos.interface.SMOSTs` class.

    \b
    Required Parameters
    -------------------
    IMG_PATH: string
        Path to the downloaded images of one orbit (with yearly subfolders),
        e.g. /path/to/smos_ic/ASC
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
        parameters=parameters)


@click.group(short_help="SMOS IC Command Line Programs.", name="ic")
def smos_ic():
    pass


smos_ic.add_command(cli_download)
smos_ic.add_command(cli_update_img)
smos_ic.add_command(cli_reshuffle)
