import click
from datetime import datetime, timedelta
import pandas as pd

from smos.smos_l2.download import SmosDissEoFtp, L2_START_DATE
from smos.smos_l2.reshuffle import swath2ts, extend_ts, _default_variables
from smos.misc import get_first_last_day_images

@click.command(
    "download",
    context_settings={'show_default': True},
    short_help="Download SMOS L2 data from FTP. This requires that the `lftp` "
               "program is installed on your system: https://lftp.yar.ru/")
@click.argument("path", type=click.Path(writable=True))
@click.option(
    '--startdate', '-s',
    type=click.STRING,
    default=str(L2_START_DATE.date()),
    help="Startdate in format YYYY-MM-DD. If not given, "
         "then the first available date of the product is used.")
@click.option(
    '--enddate', '-e',
    type=click.STRING,
    default=None,
    help="Enddate in format YYYY-MM-DD. If not given, "
         "then the last full day on the server is used.")
@click.option(
    "--username",
    type=click.STRING,
    default=None,
    help="The username you use to login at the FTP server. "
         "Required if no .smosapirc file exists in your home directory. "
         "Please create an account at https://eoiam-idp.eo.esa.int")
@click.option(
    "--password",
    type=click.STRING,
    default=None,
    help="The password you use to login at the FTP server. "
         "Required if no .smosapirc file exists in your home directory. "
         "Please create an account at https://eoiam-idp.eo.esa.int")
def cli_download(path,
                 startdate,
                 enddate,
                 username,
                 password,
    ):
    """
    Download SMOS L2 data within a chosen period. NOTE: Before using this
    program, create an account at https://eoiam-idp.eo.esa.int and ideally
    store you credentials in the file $HOME/.smosapirc (to avoid passing them
    as plain text).

    \b
    Required Parameters
    -------------------
    PATH: string (required)
        Path where the downloaded images are stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.

    ftp = SmosDissEoFtp(path, username=username, password=password)

    if enddate is None:
        enddate = ftp.last_available_day() - timedelta(days=1)

    ftp.sync_period(startdate=pd.to_datetime(startdate).to_pydatetime(),
                    enddate=enddate)

@click.command(
    "update_img",
    context_settings={'show_default': True},
    short_help="Extend an existing record by downloading new files. "
               "This requires that the `lftp` program is installed on your "
               "system: https://lftp.yar.ru/")
@click.argument("path",
                type=click.Path(writable=True))
@click.option(
    "--username",
    type=click.STRING,
    default=None,
    help="The username you use to login at the FTP server. "
         "Required if no .smosapirc file exists in your home directory. "
         "Please create an account at https://eoiam-idp.eo.esa.int")
@click.option(
    "--password",
    type=click.STRING,
    default=None,
    help="The password you use to login at the FTP server. "
         "Required if no .smosapirc file exists in your home directory. "
         "Please create an account at https://eoiam-idp.eo.esa.int")
def cli_update_img(path,
                   username,
                   password):
    """
    Extend a locally existing SMOS L2 by downloading new files that
    don't yet exist locally. The last day on the server is usually incomplete
    and therefore ignored.
    NOTE: Before using this program, create an account at
    https://eoiam-idp.eo.esa.int and ideally store you credentials in the
    file $HOME/.smosapirc (to avoid passing them as plain text).
    NOTE: Use the `smos_l2 download` program first do create a local record
    to update with this function.

    \b
    Required Parameters
    -------------------
    PATH: string
        Path where previously downloaded SMOS L2 images are stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.

    ftp = SmosDissEoFtp(path, username=username, password=password)
    enddate = ftp.last_available_day() - timedelta(days=1)
    # in case there are any incomplete days
    ftp.sync_period(startdate=get_first_last_day_images(path)[1],
                    enddate=str(enddate.date()))


@click.command(
    "reshuffle",
    context_settings={'show_default': True},
    short_help="Convert SMOS L2 swath images into time series.")
@click.argument("img_path", type=click.Path(readable=True))
@click.argument("ts_path", type=click.Path(writable=True))
@click.option(
    '--startdate',
    '-s',
    type=click.STRING,
    default=None,
    help="Format YYYY-MM-DD | First day to include in the"
    "time series. [default: Date of the first available image]")
@click.option(
    '--enddate',
    '-e',
    type=click.STRING,
    default=None,
    help="Format YYYY-MM-DD | Last day to include in the"
    "time series. [default: Date of the last available image]")
@click.option(
    '--variables',
    '-v',
    type=click.STRING,
    default=','.join(_default_variables),
    help="List of variables in the swath files to reshuffle. Multiple variables"
         " must be comma-separated.")
@click.option(
    '--memory',
    '-m',
    type=click.INT,
    default=4,
    help="NUMBER | Available memory (in GB) to use to load image data. "
    "A larger buffer means faster processing.")
def cli_reshuffle(img_path, ts_path, startdate, enddate, variables,
                  memory):
    """
    Convert SMOS L2 image data into a (5x5 degrees chunked) time series format
    following CF conventions (Indexed Ragged format).
    This format is preferred for performant location-based reading of SM data
    over the full period. To read the generated time series data, you can then
    use the `smos.smos_l2.interface.SmosL2Ts` or
    `pynetcf.time_series.GriddedNcIndexedRagged` class.

    \b
    Required Parameters
    -------------------
    IMG_PATH: string
        Path where previously downloaded SMOS images are stored. Use the
        `smos_l2 download` command to retrieve image data.
    TS_PATH: string
        Path where the newly created time series files should be stored.
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.
    print(f"Convert image data in {img_path} to time series in {ts_path}")

    variables = [str(v.strip()) for v in variables.split(',')]

    swath2ts(
        img_path,
        ts_path,
        variables=variables,
        startdate=startdate,
        enddate=enddate,
        memory=int(memory))

@click.command(
    "update_ts",
    context_settings={'show_default': True},
    short_help="Extend an existing time series record with "
    "available image data.")
@click.argument("img_path", type=click.Path(readable=True))
@click.argument("ts_path", type=click.Path(writable=True))
def cli_update_ts(img_path, ts_path):
    """
    Extend a locally existing SMOS L2 time series record by appending new data
    from the swath files. This will detect the time range of the time series
    data and compare it against the available image data.
    NOTE: Use the `smos_l2 reshuffle` program first do create a time series
    record to update with this function.

    \b
    Required Parameters
    -------------------
    IMG_PATH: string
        Path where previously downloaded SMOS files are stored.
    TS_PATH: string
        Path where the time series to update are stored
    """
    # The docstring above is slightly different to the normal python one to
    # display it properly on the command line.

    print(f"Extend time series in {ts_path} with image data from {img_path}")
    extend_ts(img_path, ts_path)

@click.group(short_help="SMOS L2 Command Line Programs.",
             name="smos_l2")
def smos_l2():
    pass

smos_l2.add_command(cli_download)
smos_l2.add_command(cli_update_img)
smos_l2.add_command(cli_reshuffle)
smos_l2.add_command(cli_update_ts)
