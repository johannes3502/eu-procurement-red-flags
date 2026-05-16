"""
CPI download module — fetches the Corruption Perceptions Index CSV
from the Humanitarian Data Exchange (HDX).
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
CPI_URL = (
    "https://data.humdata.org/dataset/"
    "fb4adde0-93d5-4ff9-befc-4a6916c1181b/resource/"
    "a6a4e225-50bb-4abf-958c-c37e3c3b380b/download/global-cpi-all.csv"
)
CPI_DIR = Path("data") / "raw" / "cpi"
CPI_FILENAME = "cpi_raw.csv"
REQUEST_TIMEOUT = 60
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


def download_cpi(force: bool = False) -> bool:
    """
    Download the global CPI CSV from HDX.

    Parameters
    ----------
    force : bool
        Re-download even if the file exists.

    Returns
    -------
    bool
        True on success (or file already exists). False on any error.
    """
    dest_dir = CPI_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / CPI_FILENAME

    if dest.exists() and not force:
        logger.info("CPI already exists – skipped (%s)", dest)
        return True

    session = _create_session()
    logger.info("Downloading CPI from HDX …")

    try:
        resp = session.get(CPI_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("CPI download failed: %s", exc)
        return False

    dest.write_bytes(resp.content)
    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info("CPI saved – %.2f MB → %s", size_mb, dest)
    return True
