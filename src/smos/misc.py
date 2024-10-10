import pandas as pd
import os
from datetime import date
import typing as t
import yaml

def _get_first_and_last_file(path: str):
    # Get list of all years (folders) in the path
    years = sorted([folder for folder in os.listdir(path) if folder.isdigit()], key=int)

    if not years:
        return None, None

    # Get the first year and last year
    first_year = years[0]
    last_year = years[-1]

    # Handle the first year
    first_year_path = os.path.join(path, first_year)
    first_months = sorted([folder for folder in os.listdir(first_year_path) if folder.isdigit()], key=int)

    if first_months:
        first_month = first_months[0]
        first_month_path = os.path.join(first_year_path, first_month)
        first_days = sorted([folder for folder in os.listdir(first_month_path) if folder.isdigit()], key=int)

        if first_days:
            first_day = first_days[0]
            first_day_path = os.path.join(first_month_path, first_day)
            first_files = sorted(os.listdir(first_day_path))
            first_file = first_files[0] if first_files else None
        else:
            first_day_path = first_month_path
            first_files = sorted(os.listdir(first_day_path))
            first_file = first_files[0] if first_files else None
    else:
        first_month_path = first_year_path
        first_files = sorted(os.listdir(first_month_path))
        first_file = first_files[0] if first_files else None

    # Handle the last year
    last_year_path = os.path.join(path, last_year)
    last_months = sorted([folder for folder in os.listdir(last_year_path) if folder.isdigit()], key=int, reverse=True)

    if last_months:
        last_month = last_months[0]
        last_month_path = os.path.join(last_year_path, last_month)
        last_days = sorted([folder for folder in os.listdir(last_month_path) if folder.isdigit()], key=int, reverse=True)

        if last_days:
            last_day = last_days[0]
            last_day_path = os.path.join(last_month_path, last_day)
            last_files = sorted(os.listdir(last_day_path))
        else:
            last_day_path = last_month_path
            last_files = sorted(os.listdir(last_day_path))
    else:
        last_month_path = last_year_path
        last_files = sorted(os.listdir(last_month_path))

    return first_file, last_files[-1] if last_files else None


def _get_date(f: str) -> t.Union[date, None]:
    for e in f.split('_'):
        try:
            dt = pd.to_datetime(e).to_pydatetime().date()
            return dt
        except Exception:
            continue
    return None


def get_first_last_day_images(img_path: str) -> \
        (t.Union[date, None], t.Union[date, None]):
    f, l = _get_first_and_last_file(img_path)
    first_day = _get_date(f) if f is not None else f
    last_day = _get_date(l) if l is not None else f

    return first_day, last_day

def read_summary_yml(path: str) -> dict:
    """
    Read image summary and return fields as dict.
    """
    path = os.path.join(path, 'overview.yml')

    with open(path, 'r') as stream:
        props = yaml.safe_load(stream)

    return props