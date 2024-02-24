import sqlite3
import os
from dotenv import load_dotenv
from pymongo import MongoClient
load_dotenv()

def getSQL(table, columns='', filters=''):

    db_path = os.getenv('DB1_PATH')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = f"SELECT {columns} FROM {table}"
    if filters:
        query += f" WHERE {filters}"
    
    cursor.execute(query, (db_path,))
    rows = cursor.fetchall()
    
    notes = [row[0] for row in rows]
    
    conn.close()
    return notes

def getMongoDB(collection_name, query={}, projection=None):
    """
    Fetches documents from a MongoDB collection.

    :param collection_name: The name of the MongoDB collection to query.
    :param query: A dictionary specifying the query conditions.
    :param projection: A dictionary specifying the fields to include or exclude.
    :return: A list of documents matching the query.
    """

    mongo_uri = os.getenv('MONGO_URI')
    mongo_db_name = os.getenv('MONGO_DB_NAME')

    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    collection = db[collection_name]

    documents = collection.find(query, projection)

    results = list(documents)

    client.close()
    return results