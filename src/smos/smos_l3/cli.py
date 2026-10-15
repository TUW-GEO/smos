import os
import click
import pandas as pd

from smos.smos_l3.download import (SmosL3Ftp, L3_START_DATE, L3_ORBITS,
                                   L3_PRODUCTS, product_folder,
                                   local_campaigns)
from smos.smos_l3.reshuffle import img2ts, extend_ts
from smos.misc import read_summary_yml


def _split(s):
    return [e.strip().upper() for e in s.split(',')]


@click.command(
    "download",
    context_settings={'show_default': True},
    short_help="Download SMOS L3 data from the CATDS FTP server. This "
    "requires that the `lftp` program is installed on your "
    "system: https://lftp.yar.ru/")
@click.argument("path", type=click.Path(writable=True))
@click.option(
    '--product',
    '-p',
    type=click.Choice(list(L3_PRODUCTS.keys()), case_sensitive=False),
    default='CLF3S',
    help="SMOS L3 product to download. CLF3S: daily SM, CLF31: daily "
    "retrieval (all variables), CLF33: 3-day aggregate, CLF3E: 3-day "
    "dielectric constant, CLF3D: 10-day aggregate, CLF3M: monthly "
    "aggregate.")
@click.option(
    '--startdate',
    '-s',
    type=click.STRING,
    default=str(L3_START_DATE.date()),
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
    default=','.join(L3_ORBITS),
    help="Overpasses to download, ASC and/or DES. Multiple orbits "
    "must be comma-separated.")
@click.option(
    '--campaigns',
    '-c',
    type=click.STRING,
    default=None,
    help="Processing campaigns to download, e.g. RE07 (reprocessed, "
    "2010-2021) and/or OPER (operational, since 2021). Multiple "
    "campaigns must be comma-separated. Data is stored in the same "
    "folder. If not given, all campaigns on the server are downloaded.")
def cli_download(path, product, startdate, enddate, orbits, campaigns):
    """
    Download SMOS L3 data within a chosen period. The public CATDS account
    is used. Data for each product and orbit is stored in a separate
    subfolder (e.g. MIR_CLF3SA). The downloaded .tgz archives are extracted.

    \b
    Required Parameters
    -------------------
    PATH: string (required)
        Path where the downloaded images are stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.

    ftp = SmosL3Ftp(
        path,
        product=product,
        orbits=_split(orbits),
        campaigns=None if campaigns is None else _split(campaigns))

    if enddate is None:
        enddate = ftp.last_available_day()

    ftp.sync_period(
        startdate=pd.to_datetime(startdate).to_pydatetime(), enddate=enddate)


@click.command(
    "update_img",
    context_settings={'show_default': True},
    short_help="Extend an existing record by downloading new files. "
    "This requires that the `lftp` program is installed on your "
    "system: https://lftp.yar.ru/")
@click.argument("path", type=click.Path(writable=True))
@click.option(
    '--product',
    '-p',
    type=click.Choice(list(L3_PRODUCTS.keys()), case_sensitive=False),
    default='CLF3S',
    help="SMOS L3 product to update.")
@click.option(
    '--orbits',
    '-o',
    type=click.STRING,
    default=','.join(L3_ORBITS),
    help="Overpasses to update, ASC and/or DES. Multiple orbits "
    "must be comma-separated.")
def cli_update_img(path, product, orbits):
    """
    Extend a locally existing SMOS L3 record by downloading new files that
    don't yet exist locally. All processing campaigns on the server are
    checked. If there is a campaign that is not in the local record yet
    (e.g. a new reprocessing), it is downloaded for the whole period of the
    local record (and the reader then uses the files with the highest
    version).
    NOTE: Use the `smos l3 download` program first do create a local record
    to update with this function.

    \b
    Required Parameters
    -------------------
    PATH: string
        Path where previously downloaded SMOS L3 images are stored (i.e. the
        parent folder of the product folders, e.g. MIR_CLF3SA).
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.
    orbits = _split(orbits)
    first_days, last_days, local = [], [], []
    for o in orbits:
        folder = os.path.join(path, product_folder(product, o))
        if not os.path.isfile(os.path.join(folder, 'overview.yml')):
            raise ValueError(f"No local data found in {folder}. "
                             f"Use `smos l3 download` first.")
        props = read_summary_yml(folder)
        first_days.append(props['first_day'])
        last_days.append(props['last_day'])
        # overview files written by older versions don't list the campaigns
        local.append(
            set(props['campaigns']) if 'campaigns' in
            props else set(local_campaigns(folder)))
    if any(d is None for d in last_days):
        raise ValueError(f"No local data found in {path}. "
                         f"Use `smos l3 download` first.")

    ftp = SmosL3Ftp(path, product=product, orbits=orbits)
    enddate = ftp.last_available_day()
    available = ftp.campaigns
    new = [c for c in available if not all(c in lc for lc in local)]
    known = [c for c in available if c not in new]

    if len(known) > 0:
        ftp.campaigns = known
        ftp.sync_period(startdate=min(last_days), enddate=enddate)
    if len(new) > 0:
        click.echo(f"New processing campaign(s) on the server: "
                   f"{', '.join(new)}. Downloading them from "
                   f"{min(first_days)} to {enddate.date()}.")
        ftp.campaigns = new
        ftp.sync_period(startdate=min(first_days), enddate=enddate)


@click.command(
    "reshuffle",
    context_settings={'show_default': True},
    short_help="Convert SMOS L3 images into time series.")
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
    Convert SMOS L3 image data of one product and orbit into a
    (5x5 degrees chunked) time series format. To read the generated time
    series data, use the `smos.smos_l3.interface_l3.SMOSL3Ts` class.

    \b
    Required Parameters
    -------------------
    IMG_PATH: string
        Path to the downloaded images of one product and orbit,
        e.g. /path/to/MIR_CLF3SA
    TS_PATH: string
        Path where the newly created time series files should be stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.
    print(f"Convert image data in {img_path} to time series in {ts_path}")

    if parameters is not None:
        parameters = [str(v.strip()) for v in parameters.split(',')]

    img2ts(
        img_path,
        ts_path,
        startdate=startdate,
        enddate=enddate,
        parameters=parameters,
        bbox=bbox if len(bbox or []) == 4 else None,
        only_land=only_land,
        imgbuffer=imgbuffer)


@click.command(
    "update_ts",
    context_settings={'show_default': True},
    short_help="Extend an existing time series record with "
    "available image data.")
@click.argument("img_path", type=click.Path(readable=True))
@click.argument("ts_path", type=click.Path(writable=True))
def cli_update_ts(img_path, ts_path):
    """
    Extend a locally existing SMOS L3 time series record by appending new
    data from the image files (with the same parameters and spatial subset).
    NOTE: Use the `smos l3 reshuffle` program first do create a time series
    record to update with this function.

    \b
    Required Parameters
    -------------------
    IMG_PATH: string
        Path to the downloaded images of one product and orbit,
        e.g. /path/to/MIR_CLF3SA
    TS_PATH: string
        Path where the time series to update are stored
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.
    print(f"Extend time series in {ts_path} with image data from {img_path}")
    extend_ts(img_path, ts_path)


@click.group(short_help="SMOS L3 Command Line Programs.", name="l3")
def smos_l3():
    pass


smos_l3.add_command(cli_download)
smos_l3.add_command(cli_update_img)
smos_l3.add_command(cli_reshuffle)
smos_l3.add_command(cli_update_ts)
