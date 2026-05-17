import yaml


class SchemaRegistry:
    def __init__(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def get_resource_types(self):
        return list(self.config['types'].keys())

    def get_attributes_for_type(self, res_type):
        return list(self.config['types'].get(res_type, {}).get('attributes', {}).keys())

    def get_primary_key_for_type(self, res_type):
        return self.config['types'].get(res_type, {}).get('primary_key')

    def get_mapping(self, res_type):
        return self.config['types'].get(res_type)


class SourceRegistry:
    def __init__(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self._sources = yaml.safe_load(f).get('attribute_sources', {})

    def get_config(self, source_name: str) -> dict:
        config = self._sources.get(source_name)
        if not config:
            raise ValueError(f"Source '{source_name}' has not been defined.")
        return config