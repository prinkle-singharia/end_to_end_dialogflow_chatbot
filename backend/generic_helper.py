import re

def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string
    return ""

def get_string_from_food_dict(food_dict: dict):
    return ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])


if __name__ == "__main__":
    print(extract_session_id("projects/chotu-chatbot-xieg/agent/sessions/a00ffc8d-6143-ac05-4617-f8dfa4933d78/contexts/__system_counters__"))
    