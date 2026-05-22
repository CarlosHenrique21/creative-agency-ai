from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")

    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")
    debug: bool = Field(False, alias="DEBUG")

    output_dir: str = Field("./output/flyers", alias="OUTPUT_DIR")

    max_revision_cycles: int = Field(3, alias="MAX_REVISION_CYCLES")
    default_brand_style: str = Field("modern", alias="DEFAULT_BRAND_STYLE")

    image_model: str = Field("gpt-image-1", alias="IMAGE_MODEL")
    image_quality: str = Field("high", alias="IMAGE_QUALITY")

    chroma_brand_dir: str = Field("./chroma_db/brands", alias="CHROMA_BRAND_DIR")
    chroma_visual_dir: str = Field("./chroma_db/visuals", alias="CHROMA_VISUAL_DIR")


settings = Settings()  # type: ignore[call-arg]
