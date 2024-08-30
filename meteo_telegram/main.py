import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
from pymongo import MongoClient

from mongo_db.mongo_tools import MongoDb
from telegram_decode.telegram_factory import TelegramFactory

logging.basicConfig(level=logging.ERROR, filename='app.log', filemode='a',
                    format='%(name)s - %(levelname)s - %(message)s')



MONGO_URL='mongodb://mongo:27017/'
client = MongoClient(MONGO_URL)
db = client["telegram"]

def clean_data(data):
    """Замінює несумісні з JSON значення."""
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = clean_data(value)
    elif isinstance(data, list):
        data = [clean_data(item) for item in data]
    elif isinstance(data, float) and (data == float("inf") or data == float("-inf") or data != data):
        data = None
    return data


def send_telegram_post(type_telegram):
    # Дані для POST-запиту
    data = {
        "typeTelegram": type_telegram,
        "indexStation": "string",
        "numberMessages": "string",
        "dateStartingInput": "string",
        "dateFinishInput": "string",
        "timeStartingInput": "string",
        "timeFinishInput": "string"
    }    
    # Виконання POST-запиту до /telegram
    response = requests.post('http://localhost:8000/selenium_telegram', json=data)
    return response

def download_and_process_telegrams(country_code):
    processor = TelegramFactory.create_processor(country_code=country_code)
    df_result = processor.process_telegrams()

    # Перетворюємо DataFrame у список словників для збереження в MongoDB
    documents = df_result.to_dict('records')

    db_manager = MongoDb().db_manager

    for document in documents:
        id_telegram = document["id_telegram"]
        data_for_mongo = {"id_telegram": id_telegram, "data": document}
        data_for_mongo["data"].pop("id_telegram", None)
        # Створення або отримання колекції для країни
        collection = db_manager.get_or_create_collection(country_code)
        print(data_for_mongo)
        # Збереження або оновлення документа у MongoDB
        db_manager.insert_or_update_document(collection, data_for_mongo)
        print(f"Processed telegrams for {country_code}: {len(documents)} records")


# Створення планувальника задач
scheduler = BackgroundScheduler()

# Додавання задач до планувальника з використанням CronTrigger
# Додавання задачі для білорусі
scheduler.add_job(download_and_process_telegrams, args=['bel'],
                  trigger=CronTrigger(hour='0,3,6,9,12,15,18,21', minute=15, second=0, day_of_week='*'))

# Додавання задачі для росії
scheduler.add_job(download_and_process_telegrams, args=['rus'],
                  trigger=CronTrigger(hour='0,3,6,9,12,15,18,21', minute=20, second=0, day_of_week='*'))

# Додавання задачі для України
scheduler.add_job(download_and_process_telegrams, args=['ua'],
                  trigger=CronTrigger(hour='0,3,6,9,12,15,18,21', minute=25, second=0, day_of_week='*'))

# Запуск планувальника
scheduler.start()

class TypeTelegram(BaseModel):
    typeTelegram: str
    indexStation: Optional[str] = None
    numberMessages: Optional[str] = None
    dateStartingInput: Optional[str] = None
    dateFinishInput: Optional[str] = None
    timeStartingInput: Optional[str] = None
    timeFinishInput: Optional[str] = None

    @validator('*')
    def check_string_fields(cls, v):
        return None if v == 'string' else v

    @validator('typeTelegram')
    def check_typeTelegram(cls, v):
        allowed_values = ["hydro", "meteo"]
        if v not in allowed_values:
            raise ValueError(f'typeTelegram must be one of {allowed_values}')
        return v
    
class PostTelegrame(BaseModel):
    typeTelegram: Optional[str]
    indexStation: Optional[str]
    date: Optional[str]
    time: Optional[str]



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/download_telegrams")
def download_telegrams(country_code: str):
    try:
        download_and_process_telegrams(country_code)
        return {"message": f"Successfully started downloading telegrams for {country_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/telegram")
def post_data(post_request:PostTelegrame):
    collection_name = post_request.typeTelegram
    index_station = post_request.indexStation
    date = post_request.date
    time = post_request.time
    id_teleg = index_station+date+time
    collection = db[collection_name]
    data = collection.find_one({"id_telegram": id_teleg}, {"_id": False})
    if data is None:
        return {"message": "Дані за цей період відсутні"}
    else:
        data['data'] = str(data['data'])
        return data

@app.get("/telegram/{collection_name}/{id_teleg}")
def get_data_from_collection(collection_name: str, id_teleg: str):
    collection = db[collection_name]
    data = collection.find_one({"id_telegram": id_teleg}, {"_id": False})
    if data is None:
        return {"message": "Дані за цей період відсутні"}
    else:
        cleaned_data = clean_data(data)
        return JSONResponse(content=cleaned_data)

@app.delete("/telegram/{collection_name}/{id_teleg}")
def delete_data_from_collection(collection_name: str, id_teleg: str):
    collection = db[collection_name]
    result = collection.delete_one({"id_telegram": id_teleg})
    if result.deleted_count == 1:
        return {"message": "Дані успішно видалено"}
    else:
        return {"message": "Дані за цей id не знайдені"}
    

@app.put("/telegram/{collection_name}/{id_teleg}")
def update_data_in_collection(collection_name: str, id_teleg: str, dynamic_updates: dict):
    collection = db[collection_name]
    dynamic_updates = {}
    update_fields = {
    f"data.$[item].{field}": value
    for field, value in dynamic_updates.items()}
    result = collection.update_one(
                       {"id_telegram": id_teleg},
                       {"$set": update_fields})
    
    if result.modified_count == 1:
        return {"message": "Дані успішно оновлено"}
    else:
        return {"message": "Дані за цей id не знайдені"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, root_path="/", log_level="info")




