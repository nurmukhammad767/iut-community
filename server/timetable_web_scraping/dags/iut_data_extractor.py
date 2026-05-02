from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from timetable_extractor import fetch_complete_timetable
from available_rooms_extractor import  extract_free_rooms
from occupied_rooms import extract_occupied_rooms

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="iut_data_extractor",
    description="Extracts timetable, available and occupied rooms data from IUT Edupage in parallel",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["iut", "timetable", "scraping"],
) as dag:

    extract_timetable = PythonOperator(
        task_id="extract_timetable",
        python_callable=fetch_complete_timetable,
    )

    extract_available_rooms_task = PythonOperator(
        task_id="extract_available_rooms_task",
        python_callable=extract_free_rooms,
    )

    extract_occupied_rooms_task = PythonOperator(
        task_id="extract_occupied_rooms_task",
        python_callable=extract_occupied_rooms,
    )

    [extract_timetable, extract_available_rooms_task, extract_occupied_rooms_task]