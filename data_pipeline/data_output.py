# src/data_output.py
import logging
from pathlib import Path
from .utils import validate_input


logger = logging.getLogger(__name__)


def save_data(df, filepath):
    
    outpath = Path(filepath)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(outpath, index=False)

    logger.debug(f"Saved {len(df)} rows to {outpath}")

    return outpath
    