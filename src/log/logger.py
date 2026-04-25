import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logger(
    name: str = __name__,
    log_dir: str = "src/logs",
    log_file: str = "app.log",
    max_bytes: int = 20 * 1024 * 1024,   # 20 MB
    backup_count: int = 2,               # max. 2 Dateien (app.log, app.log.1)
    console_level: int = logging.DEBUG,
    file_level: int = logging.DEBUG,
) -> logging.Logger:
    """
    Richtet einen Logger mit Konsolen- und Dateiausgabe ein.
    - Logrotation: max. 20 MB pro Datei, maximal 2 Dateien.
    - Format: dateiname:funktion LEVEL nachricht
    - Alle Parameter sind konfigurierbar.
    """
    project_root = Path(__file__).resolve().parents[2]
    resolved_log_dir = Path(log_dir)
    if not resolved_log_dir.is_absolute():
        resolved_log_dir = project_root / resolved_log_dir

    # Log-Verzeichnis erstellen, falls nicht vorhanden
    os.makedirs(resolved_log_dir, exist_ok=True)
    file_path = os.path.join(resolved_log_dir, log_file)

    # Logger holen (oder neu anlegen)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Gesamtlevel – Handler filtern später

    # Bestehende Handler entfernen, um doppelte Ausgabe zu vermeiden
    if logger.hasHandlers():
        logger.handlers.clear()

    # Gemeinsames Format: dateiname:funktion LEVEL nachricht
    formatter = logging.Formatter("%(filename)s:%(funcName)s %(levelname)s %(message)s")

    # Datei-Handler mit Rotation
    file_handler = RotatingFileHandler(
        file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    # Konsolen-Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # Handler zum Logger hinzufügen
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger