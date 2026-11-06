# main.py

import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import setup_logging, DatasetInfo, DatasetStorage, HealthResponse, ProcessConfig, ProcessingReport, log_requests
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = DatasetStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""

    filename = Path(file.filename or "")
    if filename.suffix.lower() != ".csv":
        logger.warning(f"File extension {filename.suffix} not accepted")
        raise HTTPException(status_code=400, detail="Must be CSV file")

    contents = await file.read()
    
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError,pd.errors.ParserError,UnicodeDecodeError) as error:
        logger.warning(f"Cannot read CSV: {error}")
        raise HTTPException(status_code=400, detail="Cannot read the uploaded CSV")

    dataset_id = storage.save(df, filename.name)
    logger.info(f"Saved dataset {dataset_id}: {filename.name}, {df.shape[0]} rows")

    return DatasetInfo(
        id=dataset_id,
        filename=filename.name,
        rows=df.shape[0],
        columns=df.shape[1],
        column_names=df.columns.tolist()
    )



@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)
    if df is None:
        logger.warning(f"Dataset ID {dataset_id} not found")
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = json.loads(df.head(limit).to_json(orient="records"))

    logger.info(f"Returned {len(records)} rows from dataset {dataset_id}") 
    
    return {"id": dataset_id,
            "data": records,
            "total_rows": len(df)}


@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    data = storage.get(dataset_id)
    if data is None:
        logger.warning(f"Dataset ID {dataset_id} not found")
        raise HTTPException(status_code=404, detail="Dataset not found")
    logger.info(f"Dataset {dataset_id} loaded successfully")

    process_config = config.model_dump()
    required_columns = process_config["validation"]["required_columns"]
    numeric_columns = process_config["validation"]["numeric_columns"]

    missing = [col for col in numeric_columns if col not in data.columns]
    if missing:
        logger.warning(f"Dataset {dataset_id} missing numeric columns: {missing}")
        raise HTTPException(status_code=400, detail=f"Numeric columns not found")

    try:
        df_before = data.copy()
        df = validate_dataframe(data, required_columns, numeric_columns)

        logger.info(f"Dataset {dataset_id} rows before validating: {len(df_before)} | Rows after: {len(df)}")
        df_validated = df.copy()
        rows_removed = len(df_before) - len(df_validated)

        df_processed = process_data(df, process_config)
        logger.info(f"Dataset {dataset_id} pocessing complete: {len(df_validated)} -> {len(df_processed)} rows")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    report = create_cleaning_report(df_validated, df_processed)

    storage.update(dataset_id, df_processed)
    logger.info(f"Updated dataset {dataset_id} successfully")

    return {
        "id": dataset_id,
        "validation_rows_removed": rows_removed,
        "cleaning_report": report
    }