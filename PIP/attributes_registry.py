from sqlalchemy.exc import DBAPIError

from common.registry import SchemaRegistry, SourceRegistry
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os


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
            except DBAPIError as e:
                if isinstance(resource_id, str) and resource_id.isdigit():
                    result = await conn.execute(query, {"id": int(resource_id)})
                    row = result.fetchone()

            if not row:
                return {}

            row_dict = row._mapping
            return {
                logic_name: row_dict[phys_name] for logic_name, phys_name in columns_to_fetch.items()
            }

    async def close_connections(self):
        """Zamyka wszystkie otwarte pule połączeń."""
        for engine in self._engines.values():
            await engine.dispose()
