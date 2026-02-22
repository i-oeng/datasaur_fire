import os 
import pandas as pd
from sqlalchemy import create_engine
import time
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

if not DATABASE_URL:
    st.error("DATABASE_URL is NOT in .env.local.")
    st.stop()


def load_csv_to_db():
    print("Starting data ingestion...")
    start_time = time.time()

    print("Loading Business Units...")
    df_units = pd.read_csv("C:/Users/user/Desktop/FIRE/data/business_units.csv")
    df_units.columns = df_units.columns.str.strip()
    df_units = df_units.rename(columns={
        "Офис": "office_name",
        "Адрес": "address"
    })
    df_units.to_sql("business_units", con=engine, if_exists="append", index=False)

 
    print("Loading Managers...")
    df_managers = pd.read_csv("C:/Users/user/Desktop/FIRE/data/managers.csv")
    df_managers.columns = df_managers.columns.str.strip()
    df_managers = df_managers.rename(columns={
        "ФИО": "full_name",
        "Должность": "role", 
        "Навыки": "skills",
        "Офис": "unit_name", 
        "Количество обращений в работе": "current_load" 
    })
    df_managers.to_sql("managers", con=engine, if_exists="append", index=False)

    end_time = time.time()
    print(f"Data ingestion complete in {round(end_time - start_time, 2)} seconds!")

if __name__ == "__main__":
    load_csv_to_db()