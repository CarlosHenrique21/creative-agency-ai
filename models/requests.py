from pydantic import BaseModel, Field
from core.state import Platform, BrandProfile


class GenerateFlyersRequest(BaseModel):
    brief: str = Field(..., min_length=10, description="Descrição da campanha")
    brand: BrandProfile
    platforms: list[Platform] = Field(
        default=[Platform.INSTAGRAM_FEED, Platform.LINKEDIN_POST],
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "brief": "Lançamento do novo produto EcoBottle — garrafa sustentável para jovens de 18-30 anos.",
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
