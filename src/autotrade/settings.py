from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
import yaml
from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드(없어도 무방)


class StrategyCfg(BaseModel):
    name: str
    params: dict
    symbols: list[str]


class ApiCfg(BaseModel):
    # 환경변수명: UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY 를 추천
    key: str | None = None
    secret: str | None = None


class ExchangeCfg(BaseModel):
    name: str = "upbit"  # upbit 고정(확장 여지)
    base_url: str = "https://api.upbit.com/v1"
    timeout_s: int = 10  # 요청 타임아웃(초)


class Settings(BaseSettings):
    env: str = "dev"
    api: ApiCfg = ApiCfg()
    exchange: ExchangeCfg = ExchangeCfg()
    strategy: StrategyCfg
    data: dict = Field(default_factory=lambda: {"interval": "1m", "window": 60})
    risk: dict = Field(default_factory=dict)
    paper: bool = True  # 기본: 페이퍼(드라이런)
    live: bool = False  # CLI에서 --live 1로만 실거래 허용

    class Config:
        # 환경변수 → Settings 주입 (예: UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cls.model_validate(cfg)
