from sqlalchemy.exc import DBAPIError

from common.registry import SchemaRegistry, SourceRegistry
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text, bindparam
import os
from common.logger import get_logger

logger = get_logger("PIP-SERVICE-ATTRIBUTE_REGISTRY")

class AttributeRegistry:
    def __init__(self, schema_registry: SchemaRegistry, source_registry: SourceRegistry):
        self.schemas = schema_registry
        self.sources = source_registry
        self._engines = {}

    async def _get_engine(self, source_name: str):
        """Pobiera lub tworzy asynchroniczny silnik SQLAlchemy dla danego źródła."""
        if source_name not in self._engines:
            config = self.sources.get_config(source_name)

            if config['type'] == "postgresql":
                # Tworzymy silnik na podstawie URL z sources.yaml
                engine = create_async_engine(
                    config['url'],
                    echo=False,
                    pool_pre_ping=True
                )
                self._engines[source_name] = engine
            else:
                raise ValueError(f"Unsupported data source type: {config['type']}")

        return self._engines[source_name]

    async def get_attributes(self, resource_type: str, resource_id: any, attributes: list[str]):
        """Pobiera wartość atrybutów z zdefiniowanego źródła."""
        if not attributes:
            return {}

        mapping = self.schemas.get_mapping(resource_type)
        if not mapping:
            return None

        columns_to_fetch = {
            attr: mapping['attributes'][attr] for attr in attributes if attr in mapping['attributes']
        }

        source_name = mapping['source']
        table = mapping['table']
        pk_col = mapping['primary_key']
        engine = await self._get_engine(source_name)

        col_names_string = ", ".join(columns_to_fetch.values())
        query = text(f"SELECT {col_names_string} FROM {table} WHERE {pk_col} = :id")

        async with engine.connect() as conn:
            # Najpierw próba wykonania zapytania z ID w formie stringa,
            # w przypadku niepowodzenia zapytanie jest powtórzone z castem na integer.
            try:
                result = await conn.execute(query, {"id": resource_id})
                row = result.fetchone()
            except DBAPIError:
                if isinstance(resource_id, str) and resource_id.isdigit():
                    result = await conn.execute(query, {"id": int(resource_id)})
                    row = result.fetchone()

            if not row:
                return {}

            row_dict = row._mapping
            return {
                logic_name: row_dict[phys_name] for logic_name, phys_name in columns_to_fetch.items()
            }

    async def get_attributes_batch(self, resource_type: str, resource_ids: list[str], attributes: list[str]) -> dict:
        """Pobiera wartości atrybutów dla wielu obiektów danego typu za pomocą jednego zapytania SQL IN."""
        if not resource_ids or not attributes:
            return {}

        mapping = self.schemas.get_mapping(resource_type)
        if not mapping:
            return {}

        columns_to_fetch = {
            attr: mapping['attributes'][attr] for attr in attributes if attr in mapping['attributes']
        }
        if not columns_to_fetch:
            return {}

        source_name = mapping['source']
        table = mapping['table']
        pk_col = mapping['primary_key']
        engine = await self._get_engine(source_name)

        col_names_list = list(columns_to_fetch.values())
        if pk_col not in col_names_list:
            col_names_list.append(pk_col)

        col_names_string = ", ".join(col_names_list)

        query = text(f"SELECT {col_names_string} FROM {table} WHERE {pk_col} IN :ids").bindparams(bindparam("ids", expanding=True))

        async with engine.connect() as conn:
            # Najpierw próba wykonania zapytania z ID w formie stringa,
            # w przypadku niepowodzenia zapytanie jest powtórzone z castem na integer.
            try:
                result = await conn.execute(query, {"ids": tuple(resource_ids)})
                rows = result.fetchall()
            except DBAPIError:
                try:
                    numeric_ids = [int(x) for x in resource_ids]
                    if not numeric_ids:
                        return {}
                    result = await conn.execute(query, {"ids": tuple(numeric_ids)})
                    rows = result.fetchall()
                except (TypeError, ValueError):
                    return {}

            if not rows:
                return {}

            # Budowanie wynikowego zagnieżdżonego słownika [id][atrybut] = wartość
            batch_result = {}
            for row in rows:
                row_dict = row._mapping
                row_pk_value = str(row_dict[pk_col])

                batch_result[row_pk_value] = {
                    logic_name: row_dict[phys_name] for logic_name, phys_name in columns_to_fetch.items()
                }

            return batch_result

    async def close_connections(self):
        """Zamyka wszystkie otwarte pule połączeń."""
        for engine in self._engines.values():
            await engine.dispose()
