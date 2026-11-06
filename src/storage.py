# storage.py

import logging
from .models import DatasetInfo

logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        """Store a copy of the data and return a new integer ID."""
        self._counter += 1
        dataset_id = self._counter
        self._store[dataset_id] = {"df": df.copy(), "filename": filename}
        logger.debug(f"Stored dataset {dataset_id}: {filename}")
        return dataset_id

    def get(self, dataset_id):
        """Return a copy of the stored DataFrame, or None."""
        df = self._store.get(dataset_id)
        if df is None:
            return None
        logger.debug(f"Returned dataframe {dataset_id}")
        return df["df"].copy()

    def get_metadata(self, dataset_id):
        """Return the dataset metadata, or None."""
        dict = self._store.get(dataset_id)
        if dict is None:
            return None

        logger.debug(f"Returned metadata for dataset {dataset_id}")
        return DatasetInfo(
            id=dataset_id,
            filename=dict["filename"],
            rows=dict["df"].shape[0],
            columns=dict["df"].shape[1],
            column_names=dict["df"].columns.tolist()
        )

    def update(self, dataset_id, df):
        """Replace an existing dataset; return True, or False if missing."""
        entry = self._store.get(dataset_id)
        if entry is None:
            logger.debug(f"Missing ID: {dataset_id}")
            return False
        
        entry["df"] = df.copy()

        logger.debug(f"Replaced existing dataset {dataset_id}")
        return True


    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0
        logger.debug(f"Cleared all info and reset counter")
