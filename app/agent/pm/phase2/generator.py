"""Phase 2: Per-section PRD content generator."""

from collections.abc import AsyncGenerator

from loguru import logger

from app.config import config
from app.core.llm_factory import llm_factory


class SectionGenerator:

    def __init__(self):
        self.model = llm_factory.create_chat_model(
            model=config.llm_model,
            temperature=0.3,
            streaming=True,
        )

    async def generate(
        self,
        section: dict,
    ) -> AsyncGenerator[str, None]:
        """Generate content for a single PRD section.

        Args:
            section: Section dict with 'title', 'prompt'

        Yields:
            Content string chunks (tokens)
        """
        logger.info(f"Generating section: {section['title']}")
        full_prompt = (
            f"Write the following PRD section in professional Markdown.\n"
            f"Section title: {section['title']}\n\n"
            f"{section['prompt']}\n\n"
            f"Output only the section content in Markdown. Start with the "
            f"section heading `## {section['title']}`."
        )

        async for chunk in self.model.astream(full_prompt):
            content = getattr(chunk, 'content', '')
            if content:
                yield content


_section_generator: SectionGenerator | None = None


def get_section_generator() -> SectionGenerator:
    global _section_generator
    if _section_generator is None:
        _section_generator = SectionGenerator()
    return _section_generator
