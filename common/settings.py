import yaml

class Settings:
    def __init__(self, path="config.yaml"):
        with open(path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.db_settings = self.config.get("pip", {}).get("delegation_db", {})
        self.pdp_settings = self.config.get("pdp", {})

    def get_pdp_mode(self):
        return self.pdp_settings.get("default_behaviour", "permit_override")

    def get_database_url(self):
        db_type = self.db_settings.get("db_type")
        user = self.db_settings.get("username")
        password = self.db_settings.get("password")
        database = self.db_settings.get("database")
        host = self.db_settings.get("host")
        port = self.db_settings.get("port")

        return f"{db_type}://{user}:{password}@{host}:{port}/{database}"

    def get_table_name(self):
        return self.db_settings.get("table", "delegations")