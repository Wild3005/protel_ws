from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # boleh semua (dev mode)
    allow_credentials=True,
    allow_methods=["*"],  # ini penting (OPTIONS diizinkan)
    allow_headers=["*"],
)

menu_map = {
    "cap cay": [1, 4, 5],
    "nasi goreng": [2, 3, 6]
}

ingredient_map = {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    
    "a": 1,
    "b": 2,
    "c": 3,
    "d": 4,
    "e": 5,
    "f": 6,
}

synonym_map = {
    "capcay": "cap cay",
    "capcai": "cap cay",
    "cap cay": "cap cay",
    "nasi goreng": "nasi goreng",
    "nasgor": "nasi goreng"
}

menu_list = "\n".join(f"- {menu}" for menu in menu_map.keys())

class RequestData(BaseModel):
    message: str


def ask_llm(text: str) -> str:
    prompt = f"""
        You are a strict order extraction system.

        TASK:
        Extract BOTH:
        1. Menu orders
        2. Individual ingredient items (by index or letter)

        AVAILABLE MENU:
        {menu_list}

        AVAILABLE INGREDIENT INDEX:
        1, 2, 3, 4, 5, 6

        LETTER MAPPING:
        a=1, b=2, c=3, d=4, e=5, f=6

        OUTPUT FORMAT:
        {{
        "orders": [
            {{ "menu": "cap cay", "qty": 2 }}
        ],
        "items": [1,2,3]
        }}

        STRICT RULES:
        - Output MUST be JSON
        - DO NOT explain
        - qty MUST be integer
        - If no quantity → qty = 1
        - DO NOT guess menu if not mentioned
        - DO NOT convert ingredient into menu
        - If input unclear → return empty

        LOGIC:
        - If user mentions menu → fill "orders"
        - If user mentions ingredient (number/letter) → fill "items"
        - If both → fill both

        EXAMPLES:

        INPUT: capcay
        OUTPUT:
        {{ "orders": [{{ "menu": "cap cay", "qty": 1 }}], "items": [] }}

        INPUT: 1 2 3
        OUTPUT:
        {{ "orders": [], "items": [1,2,3] }}

        INPUT: bahan a b c
        OUTPUT:
        {{ "orders": [], "items": [1,2,3] }}

        INPUT: capcay dan 1 2
        OUTPUT:
        {{
        "orders": [{{ "menu": "cap cay", "qty": 1 }}],
        "items": [1,2]
        }}

        INPUT: saya mau bahan nasgor 2
        OUTPUT:
        {{ "orders": [{{ "menu": "nasi goreng", "qty": 2 }}], "items": [] }}

        INPUT: ambilkan bahan capcay dan bahan 1 dan 3
        OUTPUT:
        {{
        "orders": [{{ "menu": "cap cay", "qty": 1 }}],
        "items": [1,3]
        }}

        INPUT: halo
        OUTPUT:
        {{ "orders": [], "items": [] }}

        USER INPUT:
        {text}
        """
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0
            }
        }
    )

    data = response.json()
    print("DEBUG LLM:", data)

    return data["response"]

def normalize_input(text: str):
    text = text.lower()

    for key, val in synonym_map.items():
        text = text.replace(key, val)

    return text


@app.post("/chat")
def chat(data: RequestData):
    print("INPUT USER:", data.message)

    clean_text = normalize_input(data.message)
    print("CLEAN TEXT:", clean_text)
    llm_output = ask_llm(clean_text)
    print("LLM OUTPUT RAW:", llm_output)

    try:
        cleaned = llm_output.strip()
        result = json.loads(cleaned)
        # menus = result["menu"]
        orders = result.get("orders", [])
        items_direct = result.get("items", [])
    except Exception:
        return {"error": "LLM parsing error", "raw": llm_output}

    final_items = []

    for order in orders:
        menu = order["menu"].lower().strip()
        qty = int(order["qty"])

        menu = synonym_map.get(menu, menu)

        if menu not in menu_map:
            return {"error": "menu tidak tersedia", "menu": menu}

        for _ in range(qty):
            final_items.extend(menu_map[menu])
            print("MENU FINAL:", menu)

    for item in items_direct:
        try:
            item_int = int(item)
            final_items.append(item_int)
        except:
            pass


    return {
        "items": final_items
    }