import os
import requests
from typing import Dict, Any, Optional
from .config import settings

class SimpleSupabaseClient:
    """Simple Supabase client for database operations only."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'apikey': key
        }

    def table(self, table_name: str):
        return SupabaseTable(self.url, table_name, self.headers)

class SupabaseTable:
    """Simple table operations for Supabase."""

    def __init__(self, base_url: str, table_name: str, headers: Dict[str, str]):
        self.base_url = base_url
        self.table_name = table_name
        self.headers = headers

    def select(self, columns: str = '*'):
        return SupabaseQuery(self.base_url, self.table_name, self.headers, columns)

    def upsert(self, data: Dict[str, Any], **kwargs):
        on_conflict = kwargs.get('onConflict', '')
        return SupabaseUpsertQuery(self.base_url, self.table_name, self.headers, data, on_conflict)

class SupabaseQuery:
    """Simple query builder for Supabase."""

    def __init__(self, base_url: str, table_name: str, headers: Dict[str, str], columns: str):
        self.base_url = base_url
        self.table_name = table_name
        self.headers = headers
        self.columns = columns
        self.filters = []

    def eq(self, column: str, value: Any):
        self.filters.append(f"{column}=eq.{value}")
        return self

    def single(self):
        return SupabaseSingleQuery(self.base_url, self.table_name, self.headers, self.columns, self.filters)

class SupabaseSingleQuery:
    """Single record query for Supabase."""

    def __init__(self, base_url: str, table_name: str, headers: Dict[str, str], columns: str, filters: list):
        self.base_url = base_url
        self.table_name = table_name
        self.headers = headers
        self.columns = columns
        self.filters = filters

    def execute(self):
        url = f"{self.base_url}/rest/v1/{self.table_name}"
        if self.filters:
            url += "?" + "&".join(self.filters)

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list) and len(data) == 1:
            return {"data": data[0], "error": None}
        elif isinstance(data, list) and len(data) == 0:
            return {"data": None, "error": None}
        else:
            return {"data": data, "error": None}

class SupabaseUpsertQuery:
    """Upsert query for Supabase."""

    def __init__(self, base_url: str, table_name: str, headers: Dict[str, str], data: Dict[str, Any], on_conflict: str):
        self.base_url = base_url
        self.table_name = table_name
        self.headers = headers
        self.data = data
        self.on_conflict = on_conflict

    def execute(self):
        url = f"{self.base_url}/rest/v1/{self.table_name}"
        if self.on_conflict:
            url += f"?on_conflict={self.on_conflict}"

        response = requests.post(url, headers=self.headers, json=self.data)
        response.raise_for_status()

        return {"data": response.json(), "error": None}

# Create simple Supabase clients
supabase = SimpleSupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
supabase_anon = SimpleSupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
