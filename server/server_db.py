import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DB =================

def get_conn():
    return psycopg2.connect(
        dbname="vending_test",
        user="postgres",
        password="1234",
        host="localhost"
    )

def get_all_menus():
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT name FROM menus")
        results = cur.fetchall()

        cur.close()
        conn.close()

        return [row[0] for row in results]

    except Exception as e:
        return []


def get_menu_items(menu_name):
    conn = get_conn()
    cur = conn.cursor()

    query = """
    SELECT items.id
    FROM menus
    JOIN menu_items ON menus.id = menu_items.menu_id
    JOIN items ON items.id = menu_items.item_id
    WHERE LOWER(menus.name) = %s
    """

    cur.execute(query, (menu_name,))
    results = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in results]


def is_valid_item(item_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None


def get_all_item_ids():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM items")
    results = cur.fetchall()

    cur.close()
    conn.close()

    return [str(r[0]) for r in results]


# ================= LLM =================

synonym_map = {
    "capcay": "cap cay",
    "capcai": "cap cay",
    "cap cay": "cap cay",
    "nasi goreng": "nasi goreng",
    "nasgor": "nasi goreng"
}


class RequestData(BaseModel):
    message: str


def ask_llm(text: str) -> str:
    menus = get_all_menus()
    item_ids = ", ".join(get_all_item_ids())

    menu_list = "\n".join(f"- {menu}" for menu in menus)

    # prompt = f"""
    #     You are a strict order extraction system.

    #     AVAILABLE MENU:
    #     {menu_list}

    #     AVAILABLE INGREDIENT INDEX:
    #     {item_ids}

    #     LETTER MAPPING:
    #     a=1, b=2, c=3, d=4, e=5, f=6

    #     OUTPUT FORMAT:
    #     {{
    #     "orders": [{{ "menu": "cap cay", "qty": 2 }}],
    #     "items": [1,2,3]
    #     }}

    #     STRICT RULES:
    #     - Output MUST be JSON
    #     - DO NOT explain
    #     - qty MUST be integer
    #     - If no quantity → qty = 1
    #     - If unclear → return empty

    #     USER INPUT:
    #     {text}
    #     """

    prompt = f"""
        You are a strict order extraction system.

        TASK:
        Extract BOTH:
        1. Menu orders
        2. Individual ingredient items (by index or letter)

        AVAILABLE MENU:
        {menu_list}

        AVAILABLE INGREDIENT INDEX:
        {item_ids}

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
        - Only choose menu from AVAILABLE MENU
        - Only choose items from AVAILABLE INGREDIENT INDEX

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

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3:8b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            }
        )

        data = response.json()
        return data["response"]

    except:
        return '{"orders": [], "items": []}'


# ================= MAIN =================

def normalize_input(text: str):
    text = text.lower()
    for key, val in synonym_map.items():
        text = text.replace(key, val)
    return text


@app.post("/chat")
def chat(data: RequestData):
    clean_text = normalize_input(data.message)

    llm_output = ask_llm(clean_text)

    try:
        result = json.loads(llm_output.strip())
        orders = result.get("orders", [])
        items_direct = result.get("items", [])
    except:
        return {"error": "LLM parsing error", "raw": llm_output}

    final_items = []

    # ===== MENU → DB =====
    for order in orders:
        menu = order.get("menu", "").lower().strip()

        try:
            qty = max(1, int(order.get("qty", 1)))
        except:
            qty = 1

        items_from_db = get_menu_items(menu)

        if not items_from_db:
            return {"error": "menu tidak tersedia", "menu": menu}

        for _ in range(qty):
            final_items.extend(items_from_db)

    # ===== DIRECT ITEMS =====
    for item in items_direct:
        try:
            item_int = int(item)
            if is_valid_item(item_int):
                final_items.append(item_int)
        except:
            pass

    return {"items": final_items}

@app.post("/manual-checkout")
def manual_checkout(data: dict):
    items = data.get("items", [])

    if not items:
        return {"error": "keranjang kosong"}

    conn = get_conn()
    cur = conn.cursor()

    valid_items = []

    for item_id in items:
        cur.execute(
            "SELECT stock_quantity FROM items WHERE id = %s",
            (item_id,)
        )
        result = cur.fetchone()

        if not result:
            continue

        stock = result[0]

        if stock > 0:
            valid_items.append(item_id)

    cur.close()
    conn.close()

    return {"items": valid_items}