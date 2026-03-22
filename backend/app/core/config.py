from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "parking-judge"
    app_host: str = "127.0.0.1"
    app_port: int = 8787
    database_url: str = "sqlite:///./parking_judge.db"
    google_maps_api_key: str = ""
    enable_llm: bool = False
    llm_provider: str = ""
    llm_api_key: str = ""
    cache_ttl_hours: int = 24

    vehicle_name: str = "XC40"
    vehicle_length_mm: int = 4440
    vehicle_width_mm: int = 1875
    vehicle_height_mm: int = 1655

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


settings = Settings()
