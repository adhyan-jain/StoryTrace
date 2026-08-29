import os
import clickhouse_connect
from pydantic import BaseModel
from typing import List, Any

class ClickHouseClient:
    def __init__(self):
        host = os.environ.get("CLICKHOUSE_HOST", "localhost")
        port = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
        user = os.environ.get("CLICKHOUSE_USER", "default")
        password = os.environ.get("CLICKHOUSE_PASSWORD", "")
        database = os.environ.get("CLICKHOUSE_DB", "storytrace")
        
        self.client = clickhouse_connect.get_client(
            host=host, port=port, user=user, password=password, database=database
        )

    def insert_scenes(self, scenes: List[BaseModel]):
        if not scenes:
            return
            
        data = [
            [
                s.scene_id, s.screenplay_id, s.number, s.heading, 
                s.raw_text, s.page_start, s.page_end
            ]
            for s in scenes
        ]
        
        self.client.insert(
            'scenes',
            data,
            column_names=['id', 'screenplay_id', 'number', 'heading', 'text', 'start_page', 'end_page']
        )
