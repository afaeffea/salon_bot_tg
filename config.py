from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str = ""        # "123456789,987654321" — через запятую
    TIMEZONE: str = "Europe/Berlin"
    DB_PATH: str = "salon.db"
    CONTACT_INFO: str = "📍 Адрес: ул. Примерная, 1\n📞 Телефон: +7 (999) 123-45-67"

    @property
    def admin_ids(self) -> List[int]:
        """Parse comma-separated ADMIN_IDS into list of ints."""
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
