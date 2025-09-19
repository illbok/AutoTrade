from pydantic_settings import BaseSettings
from pydantic import BaseModel
import yaml

class StrategyCfg(BaseModel):
    name: str
    params: dict
    symbols: list[str]

class ApiCfg(BaseModel):
    key: str | None = None
    secret: str | None = None

class Settings(BaseSettings):
    env: str = "dev"
    api: ApiCfg = ApiCfg()
    strategy: StrategyCfg
    data: dict
    risk: dict = {}
    paper: bool = True

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cls.model_validate(cfg)
