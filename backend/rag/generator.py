import logging
from typing import Optional
from openai import OpenAI
from backend.models.schemas import SourceChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位拥有20年以上执教经验的网球教练，你的学员覆盖从零基础初学者到职业选手的全部水平。

你的教学风格：
- 耐心、亲切，从不让学员感到沮丧
- 善于用生活中的比喻让复杂的技术变得直观易懂（例如用"端托盘"来描述拍头高度，用"握手"来描述握拍）
- 会根据学员的NTRP水平自动调整讲解深度：对初级学员（2.0-2.5）用简单直接的语言，对高级学员（4.0-4.5）可以使用专业术语
- 习惯在给出建议后用一个问题引导学员思考或追问，保持对话的互动性

你的回答结构（根据问题类型灵活调整，不需要每次都面面俱到）：
1. 先简短确认你理解了学员的问题
2. 分析可能的原因（如果适用）
3. 给出具体的、可操作的建议
4. 用一个问题收尾，引导追问或布置"作业"

你的边界：
- 当被问到超出网球专业范围的问题时，明确说这超出你的专业，并建议咨询合适的专业人士
- 对于伤病问题，你可以描述常见情况和基本护理建议，但必须建议学员去看运动医学医生进行专业诊断
- 当知识库中没有足够信息时，坦诚说你需要更多信息或这个问题超出了你目前的了解范围

语言：使用中文回答，除非学员用其他语言提问。专业英文术语（如NTRP、pronation）可以在中文中保留。
"""

UNCERTAIN_ADDITION = """

注意：知识库中可能没有完全匹配这个问题的内容。如果你觉得信息不够充分，请坦诚告知学员，并询问更多细节帮助你给出更准确的建议。
"""


class ResponseGenerator:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from backend.config import settings
            self._client = OpenAI(
                api_key=settings.ai_builder_token,
                base_url=settings.ai_builder_base_url,
            )
        return self._client

    def generate(
        self,
        user_message: str,
        retrieved_chunks: list[SourceChunk],
        user_level: Optional[str],
        conversation_history: list[dict],
        is_uncertain: bool,
    ) -> str:
        from backend.config import settings

        system = SYSTEM_PROMPT
        if is_uncertain:
            system += UNCERTAIN_ADDITION

        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(
                f"【知识片段 {i}】来源：{chunk.source_file} / {chunk.section_title}"
                f"（适用水平：{chunk.skill_level}）\n{chunk.text}"
            )
        knowledge_context = "\n\n".join(context_parts)

        level_info = f"学员当前NTRP水平：{user_level}" if user_level else "学员水平：未设置"
        context_injection = (
            f"[教练参考信息 - 以下为知识库检索结果，请基于此作答]\n\n"
            f"{level_info}\n\n"
            f"{knowledge_context}\n\n"
            f"[参考信息结束，请用上述内容作为知识基础回答学员的问题]"
        )

        messages = []
        for turn in conversation_history[-(settings.max_conversation_turns * 2):]:
            messages.append(turn)

        messages.append({
            "role": "user",
            "content": f"{context_injection}\n\n学员问题：{user_message}",
        })

        client = self._get_client()
        response = client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system}] + messages,
        )
        return response.choices[0].message.content


generator = ResponseGenerator()
