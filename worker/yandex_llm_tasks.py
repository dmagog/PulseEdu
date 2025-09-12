"""
YandexGPT LLM tasks for PulseEdu based on notebook research.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from celery import Celery
from yandex_cloud_ml_sdk import YCloudML

from celery_ingest import celery_app

logger = logging.getLogger("worker.yandex_llm")

# Initialize Yandex Cloud ML SDK
try:
    folder_id = os.getenv("YANDEX_CLOUD_FOLDER_ID")
    api_key = os.getenv("YANDEX_CLOUD_API_KEY")
    
    if folder_id and api_key:
        sdk = YCloudML(
            folder_id=folder_id,
            auth=api_key,
        )
        
        # Initialize models
        yandexgpt_model = sdk.models.completions("yandexgpt")
        yandexgpt_lite_model = sdk.models.completions("yandexgpt-lite")
        
        logger.info("Yandex Cloud ML SDK initialized successfully")
    else:
        logger.warning("Yandex Cloud ML SDK credentials not found in environment variables")
        sdk = None
        yandexgpt_model = None
        yandexgpt_lite_model = None
        
except Exception as e:
    logger.error(f"Failed to initialize Yandex Cloud ML SDK: {e}")
    sdk = None
    yandexgpt_model = None
    yandexgpt_lite_model = None


# Course roadmap from notebook
COURSE_ROADMAP = """
Название курса: Онлайн-курс от замысла до воплощения
Ниже тебе будет дано описание курса в формате JSON.

# Формат элемента массива (JSON)
```json
{
"Тема": "Изучаемая тема или модуль",
"Что изучаем": "Описание того, что будет изучено внутри модуля",
"Задания": "Описание домашних заданий и требований к студентам"
}
```

Описание структуры курса в формате JSON:
```json
[
{
"Тема": "Модуль 1. Проектируем онлайн-курс: какой, зачем, для кого?",
"Что изучаем": "Понимаем задачу: что и зачем мы делаем?; Определяем целевую аудиторию курса; Анализируем рынок, выбираем тематику и фокус; Разбираемся с типами онлайн-курсов; Команда курса: кто эти люди?; Изучаем этапы производства онлайн-курса",
"Задания": "Домашнее задание: Замысел курса, целевая аудитория, обоснование актуальности; Требования: Документ не длиннее 1 страницы."
},
{
"Тема": "Модуль 2. Педагогический дизайн курса: контент и структура",
"Что изучаем": "Ставим цели; Формулируем образовательные результаты; Собираем структуру курса; Структурируем лекцию; Делаем контент доступным и понятным; Проектируем дополнительные материалы; Не забываем об авторских правах",
"Задания": "Домашнее задание: Цели, результаты и структура курса.; Требования: Таблица, в которой отражены модули и лекции: название, порядок, 1-2 предложения о содержании."
},
{
"Тема": "Модуль 3. Создание видеоконтента: продакшн и постпродакшн",
"Что изучаем": "Готовимся к съемке в студии: что надеть, что делать и чего не делать?; Психологически настраиваемся на съемку; Привыкаем к камере; Почему важна тестовая съемка?; Знакомимся с вариантами нестудийной съемки; Видео снято: что дальше?; Как не надо делать: учимся на наших антипримерах",
"Задания": "Домашнее задание: Сценарный план вводной лекции курса с графикой; Требования: Полный текст лекции – если лектор работает по суфлёру; указан тайминг (по хрономеру). развёрнутый план лекции – если без суфлёра."
},
{
"Тема": "Модуль 4. Если не видео, то что? Варианты образовательных форматов",
"Что изучаем": "Изучаем основы геймификации; Знакомимся с основами дизайна онлайн-курсов; Осваиваем образовательные форматы: лонгрид, подкаст, карточки; Знакомимся с некоторыми возможностями нейросетей; Собираем и редактируем лонгрид, написанный нейросетью; Выбираем форматы исходя из задач и особенностей ЦА",
"Задания": "Домашнее задание: нет"
},
{
"Тема": "Модуль 5. Оценочные средства и измерение образовательных результатов",
"Что изучаем": "Вспоминаем уровни усвоения знаний; Учимся проектировать упражнения; Разрабатываем тесты и задания; Проводим рефлексию по итогам курса; Собираем и анализируем обратную связь по итогам курса",
"Задания": "Домашнее задание: нет; Факультативно: если хотите, вы можете попрактиковаться в создании тестов и заданий разных видов для вашего курса. И обсудить их в чате курса с коллегами и преподавателями."
},
{
"Тема": "Итоговое задание",
"Что изучаем": "Задание включает все элементы, разработанные слушателями за время обучения на курсе: Замысел курса, название, целевая аудитория, фокус, актуальность; Цель курса и ожидаемый образовательный результат; Структура курса: названия модулей и лекций; Сценарный план вводной лекции курса",
"Задания": "Итоговое задание: Развернутый план онлайн-курса. Вам нужно собрать три задания, которые вы уже выполнили, в один связный документ. Ничего дополнительного создавать не надо. Важно, чтобы было понятно: 1. Почему курс нужен: кто и зачем будет его проходить? 2. Как он устроен, из чего состоит? 3. Как выглядит типовая лекция курса?"
}
]
```
""".strip()


# System prompts from notebook
SYSTEM_TEXT_STUDENT_FEEDBACK = """
# Система оценки успеваемости студентов

Ты - ассистент в системе оценки успеваемости студентов. Твоя задача: проанализировать данные об успеваемости отдельного студента и предоставить ему обратную связь о его академических успехах.

## Критерии оценки

Будучи ассистентом ты должен проанализировать успехи и потенциальные риски студента, связанные с освоением курса. Оцени вовлеченность студента, то, насколько хорошо он выполняет домашние задания и выполняет ли он их в срок. Также оцени, насколько много студенту нужно поработать в оставшееся время до конца семестра, чтобы была возможность успешно освоить дисциплины. Можешь подумать над советами, которые можно дать студенту, непосредственно связанные с тем курсом, который он осваивает. Старайся быть объективным и честной оценивай каждого студента.

Выдай ответ в формате JSON:
```json
{
"activity": "Балл от 0 до 10 за успеваемость студента. Выбирай балл в соответствии с успеваемостью студента.",
"homework": "Балл от 0 до 10 за выполнение домашних заданий. Учитывай то, насколько хорошо студент выполнил домашнее задание и сделал ли он это в срок. Учитывай только те задания, по которым прошел дедлайн.",
"tests": "Балл от 0 до 10 за прохождение тестов. Учитывай то, насколько хорошо студент выполняет тесты и делает ли он это в срок. Учитывай только те тесты, которые были проведены.",
"advice": "Дай небольшую рекомендацию студенту, укажи ему на его недостатки и дай совет как их исправить, либо похвали его за хорошую успеваемость. Будь объективным, не хвали студентов, у которых все плохо, иначе они рискуют получить незачет по данному курсу. (2-3 предложения)"
}
```
""".strip()


@celery_app.task(bind=True)
def generate_student_feedback(self, student_id: str, student_data: List[Dict[str, Any]], model_type: str = "yandexgpt") -> Optional[Dict[str, Any]]:
    """
    Generate personalized feedback for a student based on their performance data.
    
    Args:
        student_id: Student ID
        student_data: List of student performance records
        model_type: Model to use ("yandexgpt" or "yandexgpt-lite")
        
    Returns:
        Dict with activity, homework, tests scores and advice
    """
    logger.info(f"Generating student feedback for {student_id} using {model_type}")
    
    if not sdk or not yandexgpt_model:
        logger.error("Yandex Cloud ML SDK not initialized")
        return None
    
    try:
        # Select model
        model = yandexgpt_model if model_type == "yandexgpt" else yandexgpt_lite_model
        
        # Build student data block
        student_main_block = (
            f"Сегодня: {datetime.now().strftime(format='%m.%d.%y %H:%M')} (Дата указана в формате %m.%d.%y %H:%M)\n"
            + """
Ниже тебе будет дано описание успеваемости студента в виде массива в формате JSON.

# Формат элемента массива (JSON)
```json
{
"Название": "Название блока. Это может быть домашнее задание, лекция, тест или другой блок.",
"Статус": "Информация о прохождении студентом данного блока.",
"Время выполнения": "Время, когда студент выполнил данный блок",
"Дедлайн": "Время, до которого нужно обязательно пройти данный блок. (Если стоит прочерк, значит дедлайн не установлен. Также это поле может отсутствовать в принципе, в таком случае также стоит считать, что дедлайна не было.)"
}
```

Успеваемость студента в формате JSON:
""".strip()
        )
        
        student_description = json.dumps(student_data, indent=0, ensure_ascii=False)
        
        # Build messages
        messages = [
            {"role": "system", "text": SYSTEM_TEXT_STUDENT_FEEDBACK + '\n\n' + COURSE_ROADMAP},
            {"role": "user", "text": student_main_block + '\n' + student_description},
        ]
        
        # Make request
        result = model.run(messages=messages)
        
        # Parse response
        response_text = result.alternatives[0].text
        
        # Try to extract JSON from response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text.strip()
        
        # Parse JSON response
        feedback = json.loads(json_text)
        
        logger.info(f"Generated feedback for student {student_id}: {feedback}")
        return feedback
        
    except Exception as e:
        logger.error(f"Failed to generate student feedback for {student_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def test_yandex_connection(self) -> Dict[str, Any]:
    """
    Test connection to Yandex Cloud ML SDK.
    
    Returns:
        Dict with connection status and test results
    """
    logger.info("Testing Yandex Cloud ML SDK connection")
    
    result = {
        "sdk_initialized": sdk is not None,
        "models_available": {
            "yandexgpt": yandexgpt_model is not None,
            "yandexgpt_lite": yandexgpt_lite_model is not None,
        },
        "test_message": "Test message",
        "timestamp": datetime.now().isoformat()
    }
    
    if not sdk or not yandexgpt_model:
        result["error"] = "Yandex Cloud ML SDK not initialized"
        return result
    
    try:
        # Test with simple message
        test_messages = [
            {"role": "system", "text": "Ты помощник. Отвечай кратко на русском языке."},
            {"role": "user", "text": "Привет! Как дела?"},
        ]
        
        response = yandexgpt_model.run(messages=test_messages)
        result["test_response"] = response.alternatives[0].text
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
        logger.error(f"Yandex Cloud ML SDK test failed: {e}")
    
    return result
