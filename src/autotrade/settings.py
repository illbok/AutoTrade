# src/autotrade/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict  # ← NEW
from pydantic import BaseModel, Field
import os  # ← NEW
import yaml


class StrategyCfg(BaseModel):
    name: str
    params: dict
    symbols: list[str]


class ApiCfg(BaseModel):
    key: str | None = None
    secret: str | None = None


class ExchangeCfg(BaseModel):
    name: str = "upbit"
    base_url: str = "https://api.upbit.com/v1"
    timeout_s: int = 10


class Settings(BaseSettings):
    env: str = "dev"
    api: ApiCfg = ApiCfg()
    exchange: ExchangeCfg = ExchangeCfg()
    strategy: StrategyCfg
    data: dict = Field(default_factory=lambda: {"interval": "1m", "window": 60})
    risk: dict = Field(default_factory=dict)

    paper: bool = True
    live: bool = False

    # ✅ Pydantic v2 스타일 설정: 알 수 없는(.env) 키는 무시, .env 자동 로드, 중첩 구분자
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ← 핵심: 모르는 환경변수는 무시
        env_nested_delimiter="__",  # 예: API__KEY 형태 지원
    )

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # ✅ .env 오버레이: 환경변수 → YAML 설정에 주입
        ek = os.getenv("UPBIT_ACCESS_KEY")
        es = os.getenv("UPBIT_SECRET_KEY")
        if ek or es:
            cfg.setdefault("api", {})
            if ek:
                cfg["api"]["key"] = ek
            if es:
                cfg["api"]["secret"] = es

        # 원한다면 중첩 키도 지원(API__KEY 등). 이미 model_config에 env_nested_delimiter 설정했으니,
        # 나중에 cls() 생성으로도 읽을 수 있지만, 현재는 YAML을 주로 쓰므로 오버레이가 가장 확실합니다.

        return cls.model_validate(cfg)  # 모델 검증 및 생성
