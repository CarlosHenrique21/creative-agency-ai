from pydantic import BaseModel, Field
from core.state import Platform, BrandProfile


class GenerateContentRequest(BaseModel):
    """Content flow — turn a brief into structured copy for one platform."""
    brief: str = Field(..., min_length=10, description="Descrição da campanha")
    platform: Platform = Field(default=Platform.INSTAGRAM_FEED)
    brand_name: str = Field(default="Bússola Fiscal")
    tone: str = Field(default="técnico e confiável")
    extra_instructions: str = Field(default="", description="Direção extra opcional para a copy.")


class GenerateFlyersRequest(BaseModel):
    brief: str = Field(..., min_length=10, description="Descrição da campanha")
    brand: BrandProfile
    platforms: list[Platform] = Field(
        default=[Platform.INSTAGRAM_FEED, Platform.LINKEDIN_POST],
        min_length=1,
    )
    brand_id: str = Field(
        default="",
        description=(
            "ID da marca no RAG. Quando fornecido, os documentos e imagens de referência "
            "previamente ingeridos via /brands/{brand_id}/ingest/* são recuperados e "
            "injetados no contexto dos agentes."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "brief": "Lançamento do novo produto EcoBottle — garrafa sustentável para jovens de 18-30 anos.",
                "brand_id": "ecobottle",
                "brand": {
                    "name": "EcoBottle",
                    "primary_color": "#2D6A4F",
                    "secondary_color": "#FFFFFF",
                    "accent_color": "#95D5B2",
                    "font_style": "modern sans-serif",
                    "tone": "jovem e sustentável",
                    "logo_description": "folha estilizada em verde",
                },
                "platforms": ["instagram_feed", "instagram_story", "linkedin_post"],
            }
        }
    }
