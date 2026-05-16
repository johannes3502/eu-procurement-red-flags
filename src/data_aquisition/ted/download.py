"""
TED download module — fetches TED CSV files from the EU data portal.

For each year, a ZIP archive containing a single CSV is downloaded,
extracted, and saved as data/raw/ted/ted_<YYYY>.csv.
"""

from __future__ import annotations

import io
import logging
import time
import zipfile
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
# Project root, resolved from this module (src/data_aquisition/ted/download.py):
#   4 × .parent → project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

TED_URLS: dict[int, str] = {
    2014: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2014.zip",
    2015: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2015.zip",
    2016: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2016.zip",
    2017: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2017.zip",
    2018: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2018.zip",
    2019: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2019.zip",
    2020: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2020.zip",
    2021: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2021.zip",
    2022: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2022.zip",
    2023: "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-2023.zip",
}

TED_DIR = _PROJECT_ROOT / "data" / "raw" / "ted"
TED_TIMEOUT = 120
DOWNLOAD_DELAY = 1.5

# HTTP retry
RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]


def _create_session() -> requests.Session:
    """Return a ``requests.Session`` with retry logic baked in."""
    session = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_FORCELIST,
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _download_and_extract_zip(
    session: requests.Session,
    year: int,
    url: str,
    dest_dir: Path,
    force: bool,
) -> bool:
    """
    Download a TED ZIP archive for one year, extract the CSV inside,
    save as ted_<YYYY>.csv.

    Returns True on success (or if already exists). False on any error.
    """
    dest = dest_dir / f"ted_{year}.csv"

    if dest.exists() and not force:
        logger.info("TED %d already exists – skipped", year)
        return True

    # Download ZIP
    logger.info("Downloading TED %d ZIP from %s …", year, url)
    try:
        resp = session.get(url, timeout=TED_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("TED %d download failed: %s", year, exc)
        return False

    size_mb = len(resp.content) / (1024 * 1024)
    logger.info("TED %d ZIP downloaded – %.2f MB", year, size_mb)

    # Extract CSV from ZIP
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                logger.warning("TED %d ZIP contains no CSV", year)
                return False
            if len(csv_names) > 1:
                logger.info(
                    "TED %d ZIP contains %d CSVs – using first: %s",
                    year, len(csv_names), csv_names[0],
                )
            csv_content = zf.read(csv_names[0])
    except (zipfile.BadZipFile, OSError) as exc:
        logger.warning("TED %d ZIP extraction failed: %s", year, exc)
        return False

    dest.write_bytes(csv_content)
    saved_mb = dest.stat().st_size / (1024 * 1024)
    logger.info("TED %d saved – %.2f MB → %s", year, saved_mb, dest)
    return True


def download_ted(
    force: bool = False,
    years: range = range(2014, 2024),
) -> bool:
    """
    Download TED CSV files for the specified years.

    Parameters
    ----------
    force : bool
        Re-download even if files exist.
    years : range
        Year range, e.g. range(2014, 2024). Years without a configured URL
        are silently skipped.

    Returns
    -------
    bool
        True if ALL configured years were processed successfully.
        False if ANY year failed.
    """
    dest_dir = TED_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    session = _create_session()
    all_ok = True

    for year in years:
        url = TED_URLS.get(year)
        if url is None:
            logger.debug("TED %d has no configured URL – skipping", year)
            continue

        ok = _download_and_extract_zip(session, year, url, dest_dir, force)
        if not ok:
            all_ok = False
        time.sleep(DOWNLOAD_DELAY)

    return all_ok
