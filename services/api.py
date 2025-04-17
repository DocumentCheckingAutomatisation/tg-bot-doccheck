import requests
from config import API_URL
from logger import logger


def get_doc_options():
    try:
        response = requests.get(f"{API_URL}/api/documents/options")
        response.raise_for_status()
        logger.debug("Получены доступные типы документов.")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при получении типов документов: {e}")
        return None


def get_rules(doc_type: str):
    try:
        response = requests.get(f"{API_URL}/api/rules/{doc_type}")
        response.raise_for_status()
        logger.debug(f"Получены правила для документа {doc_type}.")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при получении правил: {e}")
        return None


def change_rule(doc_type: str, rule_key: str, new_value: str):
    try:
        response = requests.post(
            f"{API_URL}/api/rules/update",
            data={"doc_type": doc_type, "rule_key": rule_key, "new_value": new_value}
        )
        response.raise_for_status()
        logger.info(f"Изменено правило {rule_key} для {doc_type} на {new_value}.")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при изменении правила: {e}")
        return None

def change_rule_for_all(rule_key: str, new_value: str) -> dict | None:
    try:
        response = requests.post(
            f"{API_URL}/api/rules/update/all",
            params={"rule_key": rule_key, "new_value": new_value}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"message": f"Ошибка {response.status_code}", "details": response.text}
    except Exception as e:
        return {"message": "Ошибка при подключении к API", "details": str(e)}

# добавить остальные
