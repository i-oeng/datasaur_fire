import os
import base64
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv(".env.local")
client = OpenAI()


class TicketAnalysis(BaseModel):
    ticket_type: str = Field(
        description="Строго одно из: Жалоба, Смена данных, Консультация, Претензия, Неработоспособность приложения, Мошеннические действия, Спам"
    )
    sentiment: str = Field(
        description="Строго одно из: Позитивный, Нейтральный, Негативный"
    )
    priority: int = Field(
        description="Срочность от 1 до 10. 10 = максимальная."
    )
    language: str = Field(
        description="Строго: KZ, ENG, RU. По умолчанию RU."
    )
    summary: str = Field(
        description="Краткая суть (1 предложение) + рекомендация."
    )


def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        return None


def analyze_ticket_text(description_text: str, image_path: str = None) -> dict:

    system_prompt = "Ты ИИ-ассистент Freedom Bank. Выяви проблему по тексту и/или скриншоту."

    content = []
    
    if description_text and str(description_text).strip() != "" and str(description_text).lower() != "nan":
        content.append({"type": "text", "text": str(description_text)})
    else:
        content.append({"type": "text", "text": "Анализируй только по скриншоту."})

    if image_path and os.path.exists(image_path):
        base64_image = encode_image(image_path)
        if base64_image:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "low" 
                }
            })

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5-mini", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            response_format=TicketAnalysis,
        )
        
        return response.choices[0].message.parsed.model_dump()
        
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "ticket_type": "Консультация",
            "sentiment": "Нейтральный",
            "priority": 1,
            "language": "RU",
            "summary": "Ошибка ИИ."
        }