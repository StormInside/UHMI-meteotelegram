import os
from datetime import timedelta, datetime, time
from pymongo import MongoClient
from mongo_db.mongo_tools import MongoDb
from telegram_decode.telegram_factory import TelegramFactory
from logger import setup_logger


logger = setup_logger(__name__)

mongo_user = os.getenv('MONGO_USER')
mongo_pass = os.getenv('MONGO_PASSWORD')
connection_url = f"mongodb://{mongo_user}:{mongo_pass}@mongo:27017/"


def download_and_process_telegrams(country_code, start_date=None, end_date=None):
    if not start_date:
        start_date = datetime.combine(datetime.now().date() - timedelta(days=1), time(0, 0))
    if not end_date:
        end_date = datetime.combine(datetime.now().date() - timedelta(days=1), time(21, 0))
    processor = TelegramFactory.create_processor(country_code=country_code, start_date=start_date, end_date=end_date)
    df_result = processor.process_telegrams()
    # Перетворюємо DataFrame у список словників для збереження в MongoDB
    documents = df_result.to_dict('records')

    db_manager = MongoDb(connection_url).db_manager

    for document in documents:
        id_telegram = document["id_telegram"]
        data_for_mongo = {"id_telegram": id_telegram, "data": document}
        data_for_mongo["data"].pop("id_telegram", None)
        # Створення або отримання колекції для країни
        collection = db_manager.get_or_create_collection(country_code)
        # Збереження або оновлення документа у MongoDB
        db_manager.insert_or_update_document(collection, data_for_mongo)
        logger.info(f"Processed telegrams for {country_code}: {len(documents)} records")


if __name__ == '__main__':
    download_and_process_telegrams('ua')
    download_and_process_telegrams('bel')
    download_and_process_telegrams('rus')
    pass