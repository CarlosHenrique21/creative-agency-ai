"""
Application-wide singletons for both RAG stores.
Import `brand_store` and `visual_store` anywhere in the codebase.
"""
from .brand_store import BrandStore
from .visual_store import VisualStore
from core.config import settings

brand_store = BrandStore(persist_dir=settings.chroma_brand_dir)
visual_store = VisualStore(persist_dir=settings.chroma_visual_dir)
