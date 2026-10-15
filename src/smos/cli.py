"""
Command line interface for all SMOS products: `smos <product> <command>`,
e.g. `smos l3 download`. See `smos --help`.
"""
import click

from smos.smos_l2.cli import smos_l2
from smos.smos_ic.cli import smos_ic
from smos.smos_l3.cli import smos_l3
from smos.smos_l4.cli import smos_l4


@click.group(short_help="SMOS Command Line Programs.", name="smos")
def smos():
    """
    Download SMOS data and convert it into time series. Each product has
    its own group of commands, see e.g. `smos l3 --help`.
    """
    pass


smos.add_command(smos_l2, name="l2")
smos.add_command(smos_ic, name="ic")
smos.add_command(smos_l3, name="l3")
smos.add_command(smos_l4, name="l4")
