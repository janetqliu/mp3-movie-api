# src/data_validator.py
import logging
import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """
    missing = [col for col in required_columns if col not in df.columns]
    
    if missing:
        logger.error(f"Missing {len(missing)} column(s)")
        for col in missing:
            logger.error(f"Missing column: {col}")
        raise ValueError("Must contain all required columns")

    before = len(df)

    for col in numeric_columns:
        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    logger.warning(f"Value cannot be converted to a float: index {i}")
                    invalid_rows.append(i)
        
        
        df = df.drop(index=invalid_rows)
        #convert to a numeric data type
        df[col] = pd.to_numeric(df[col])

    logger.debug(f"Valid rows: {len(df)} | Removed rows: {before - len(df)}")

    return df