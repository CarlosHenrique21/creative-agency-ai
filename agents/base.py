from __future__ import annotations
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from core.config import settings
from core.state import CampaignState, AgentMessage
import structlog

logger = structlog.get_logger()


class BaseAgent(ABC):
    name: str
    role: str

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.log = structlog.get_logger().bind(agent=self.name)

    @abstractmethod
    async def run(self, state: CampaignState) -> dict:
        ...

    async def _chat(self, system: str, user: str, model: str = "gpt-4o") -> str:
        self.log.info("llm_call", model=model)
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content or ""
        return content

    def _message(self, content: str) -> list[AgentMessage]:
        return [AgentMessage(agent=self.name, content=content)]
