import os
import base64
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv(".env.local")
my_api_key = os.getenv("OPENAI_API_KEY")
my_base_url = os.getenv("BASE_URL")

if not my_api_key:
    print("WARNING: .env.local failed.")


client = OpenAI(
    base_url = my_base_url,
    api_key = my_api_key,
)

class TicketAnalysis(BaseModel):
    ticket_type: str = Field(
        description="Категория обращения. Строго одно из: Жалоба, Смена данных, Консультация, Претензия, Неработоспособность приложения, Мошеннические действия, Спам"
    )
    sentiment: str = Field(
        description="Эмоциональный фон. Строго одно из: Позитивный, Нейтральный, Негативный"
    )
    priority: int = Field(
        description="Оценка срочности обработки по шкале от 1 до 10. 10 = максимальная срочность."
    )
    language: str = Field(
        description="Язык обращения. Строго одно из: KZ, ENG, RU. Если непонятно, RU."
    )
    summary: str = Field(
        description="Краткая выжимка сути обращения (1 предложение) с учетом текста и прикрепленных скриншотов + дальнейшие этичные рекомендации менеджеру."
    )


def encode_image(image_path):
    # Uses base64 to decode the images and take them into account
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading image {image_path}: {e}")
        return None

def analyze_ticket_text(description_text: str, image_path: str = None) -> dict:
    # Sends the text AND the image (if it exists) to ChatGPT.
    # Now equipped to handle tickets with no text at all.
    system_prompt = """
    Ты — ИИ-ассистент Freedom Bank. 
    Проанализируй текст обращения клиента и прикрепленный скриншот (если есть).
    Выяви суть проблемы, определи категорию, язык и приоритет.
    """

    content = []
    

    if description_text and str(description_text).strip() != "" and str(description_text).lower() != "nan":
        content.append({"type": "text", "text": f"Текст обращения: {description_text}"})
    else:
        content.append({"type": "text", "text": "Текст обращения отсутствует. Проанализируй проблему и заполни данные исключительно по прикрепленному скриншоту."})


    if image_path and os.path.exists(image_path):
        base64_image = encode_image(image_path)
        if base64_image:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
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
        print(f"AI Processing Error: {e}")
        return {
            "ticket_type": "Консультация",
            "sentiment": "Нейтральный",
            "priority": 5,
            "language": "RU",
            "summary": "Ошибка ИИ при анализе."
        }
