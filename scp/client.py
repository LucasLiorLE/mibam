import os
import html
import re
import time
import json
import random
import atexit
import logging
import argparse
import websocket
from collections import deque
from difflib import get_close_matches
from dotenv import load_dotenv
from discordws import DiscordWS

curses = True
try: import curses
except ImportError: curses = False

# Global stats (across all sessions)
count = 0
credits = 0
scp = 0
buttons = 0
trivia_scp = 0
trivia = 0
trivia_answered = 0
gold_bars = 0
sniped_gold = 0
coinflips = 0
coinflips_success = 0
coinflips_scp = 0

# Session stats (current run only)
session_count = 0
session_credits = 0
session_scp = 0
session_buttons = 0
session_trivia_scp = 0
session_trivia = 0
session_trivia_answered = 0
session_gold_bars = 0
session_sniped_gold = 0
session_coinflips = 0
session_coinflips_success = 0
session_coinflips_scp = 0

def save_stats():
    """Add session stats to global and save to stats.json."""
    global count, credits, scp, buttons, trivia_scp, trivia, trivia_answered, gold_bars, sniped_gold, coinflips, coinflips_success, coinflips_scp
    global session_count, session_credits, session_scp, session_buttons, session_trivia_scp, session_trivia, session_trivia_answered, session_gold_bars, session_sniped_gold, session_coinflips, session_coinflips_success, session_coinflips_scp
    
    count += session_count
    credits += session_credits
    scp += session_scp
    buttons += session_buttons
    trivia_scp += session_trivia_scp
    trivia += session_trivia
    trivia_answered += session_trivia_answered
    gold_bars += session_gold_bars
    sniped_gold += session_sniped_gold
    coinflips += session_coinflips
    coinflips_success += session_coinflips_success
    coinflips_scp += session_coinflips_scp
    
    stats = {
        "count": count,
        "credits": credits,
        "scp": scp,
        "buttons": buttons,
        "trivia_scp": trivia_scp,
        "trivia": trivia,
        "trivia_answered": trivia_answered,
        "gold_bars": gold_bars,
        "sniped_gold": sniped_gold,
        "coinflips": coinflips,
        "coinflips_success": coinflips_success,
        "coinflips_scp": coinflips_scp,
    }
    try:
        with open("stats.json", "w") as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        print(f"Failed to save stats: {e}")

def load_stats():
    """Load all global statistics from stats.json."""
    global count, credits, scp, buttons, trivia_scp, trivia, trivia_answered, gold_bars, sniped_gold, coinflips, coinflips_success, coinflips_scp
    try:
        if os.path.exists("stats.json"):
            with open("stats.json", "r") as f:
                stats = json.load(f)
                count = stats.get("count", 0)
                credits = stats.get("credits", 0)
                scp = stats.get("scp", 0)
                buttons = stats.get("buttons", 0)
                trivia_scp = stats.get("trivia_scp", 0)
                trivia = stats.get("trivia", 0)
                trivia_answered = stats.get("trivia_answered", 0)
                gold_bars = stats.get("gold_bars", 0)
                sniped_gold = stats.get("sniped_gold", 0)
                coinflips = stats.get("coinflips", 0)
                coinflips_success = stats.get("coinflips_success", 0)
                coinflips_scp = stats.get("coinflips_scp", 0)
    except Exception as e:
        print(f"Failed to load stats: {e}")

grind_scp = True
grind_trivia = True
snipe = True
gamble = False

def save_settings():
    settings = {
        "grind_scp": grind_scp,
        "grind_trivia": grind_trivia,
        "snipe": snipe,
        "gamble": gamble,
    }
    try:
        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Failed to save settings: {e}")

def load_settings():
    global grind_scp, grind_trivia, snipe, gamble
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                settings = json.load(f)
                grind_scp = settings.get("grind_scp", True)
                grind_trivia = settings.get("grind_trivia", True)
                snipe = settings.get("snipe", True)
                gamble = settings.get("gamble", False)
    except Exception as e:
        print(f"Failed to load settings: {e}")

def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip().lower()

def load_trivia_bank() -> list[dict]:
    trivia_path = os.path.join(os.path.dirname(__file__), "trivia.json")
    try:
        with open(trivia_path, "r") as f:
            trivia_bank = json.load(f)
            return trivia_bank if isinstance(trivia_bank, list) else []
    except Exception as e:
        print(f"Failed to load trivia bank: {e}")
        return []

def save_trivia_bank(trivia_bank: list[dict]) -> None:
    trivia_path = os.path.join(os.path.dirname(__file__), "trivia.json")
    try:
        with open(trivia_path, "w") as f:
            json.dump(trivia_bank, f, indent=4)
    except Exception as e:
        print(f"Failed to save trivia bank: {e}")

TRIVIA_BANK = load_trivia_bank()

def upsert_trivia_bank(question: str, correct_answer: str) -> None:
    normalized_question = normalize_text(question)
    normalized_answer = normalize_text(correct_answer)

    for entry in TRIVIA_BANK:
        if normalize_text(entry.get("question", "")) == normalized_question:
            entry["question"] = html.unescape(question).strip()
            entry["correct_answer"] = normalized_answer
            save_trivia_bank(TRIVIA_BANK)
            return

    TRIVIA_BANK.append({
        "question": html.unescape(question).strip(),
        "correct_answer": normalized_answer,
    })
    save_trivia_bank(TRIVIA_BANK)

def load_persistents():
    """Load all persistent data (stats and settings)."""
    load_stats()
    load_settings()

def save_persistents():
    """Save all persistent data (stats and settings)."""
    save_stats()
    save_settings()

class Client(DiscordWS):
    def __init__(self, token: str):
        super().__init__(token)
        self.user_id = None
        self.user_name = None

        self.message = "Glory to the CCP!"
        self.holger_id = "1050445714825695242"
        self.grind_id = "1236718074959364171"
        # self.chat_id = "1238539845731745883"
        self.bot_c_id = "1346671299262546013"
        self.guild_id = "820093197933740062"

        self.queue_logs = deque(maxlen=10) # (eventType, eventTime: time.time(), kwargs: dict)
        self.event_logs = deque(maxlen=20) # (message, color)

        self.callbacked = True
        self.button = False
        self.check_gold = False
        self.gamble = False
        self.snipe_amount = 0
        self.check_gold_time = 0  # Track when check_gold was set
        self.current_gamble_amount = 0  # Track the amount for the current gamble
        self.trivia_state = None

    def find_trivia_entry(self, question: str):
        normalized_question = normalize_text(html.unescape(question))
        normalized_bank = [normalize_text(entry.get("question", "")) for entry in TRIVIA_BANK]
        
        matches = get_close_matches(normalized_question, normalized_bank, n=1, cutoff=0.7)
        if not matches:
            return None

        best_match = matches[0]
        index = normalized_bank.index(best_match)
        return TRIVIA_BANK[index]

    def start_trivia(self, msg_data: dict, embed: dict) -> None:
        global session_trivia

        question = embed.get('description', '')
        answers = []
        for field in embed.get('fields', []):
            if field.get('name', '').startswith("Option"):
                answers.append(normalize_text(field.get('value', '')))

        if not answers:
            self.add_event("Trivia embed had no answers.", "ORANGE")
            return

        trivia_entry = self.find_trivia_entry(question)
        known_answer = normalize_text(trivia_entry.get('correct_answer', '')) if trivia_entry else None
        if known_answer and known_answer not in answers:
            known_answer = None

        self.trivia_state = {
            "question": html.unescape(question).strip(),
            "normalized_question": normalize_text(question),
            "channel_id": msg_data.get('channel_id'),
            "message_id": msg_data.get('id'),
            "guild_id": msg_data.get('guild_id'),
            "answers": answers,
            "candidates": list(answers),
            "known_answer": known_answer,
        }
        session_trivia += 1
        self.add_event(f"Trivia received: {self.trivia_state['question']}", "MAGENTA")
        self.add_queue(
            "TRIVIA_REPLY",
            self.random_time(2),
            {
                "channel_id": msg_data.get('channel_id'),
                "message_id": msg_data.get('id'),
            },
        )

    def narrow_trivia_candidates(self, content: str) -> None:
        if not self.trivia_state:
            return

        normalized_content = normalize_text(content)
        if not normalized_content:
            return

        candidates = self.trivia_state.get("candidates", [])
        if normalized_content not in candidates:
            return

        remaining = [candidate for candidate in candidates if candidate != normalized_content]
        if len(remaining) != len(candidates):
            self.trivia_state["candidates"] = remaining
            self.add_event(f"Trivia option eliminated: {normalized_content}", "ORANGE")

    def resolve_trivia_reply(self) -> str | None:
        if not self.trivia_state:
            return None

        known_answer = self.trivia_state.get("known_answer")
        candidates = self.trivia_state.get("candidates", [])
        if known_answer and known_answer in candidates:
            return known_answer
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            return random.choice(candidates)
        return None

    def handle_trivia_result(self, embed: dict) -> None:
        global session_trivia_answered, session_trivia_scp

        title = embed.get('title', '')
        description = embed.get('description', '')

        if title == "Trivia Question Answered":
            question = self.trivia_state.get("question", description) if self.trivia_state else description
            answer = None
            reward = 0
            winner = None

            for field in embed.get('fields', []):
                field_name = normalize_text(field.get('name', ''))
                field_value = normalize_text(field.get('value', ''))
                if field_name == "reward":
                    reward_match = re.search(r"(\d+)", field_value)
                    if reward_match:
                        reward = int(reward_match.group(1))
                elif field_name == "answer":
                    answer = field_value
                elif field_name == "winner":
                    winner = html.unescape(field.get('value', '')).strip()

            if answer:
                upsert_trivia_bank(question, answer)
                session_trivia_answered += 1
                session_trivia_scp += reward
                self.add_event(f"Trivia answered: {answer}", "GREEN")
                if winner:
                    self.add_event(f"Winner: {winner}", "GREEN")

            self.trivia_state = None

        elif title == "Error" and "No one answered the trivia question in time" in description:
            answer_match = re.search(r"answer was\s*(.+?)\.?$", description, re.IGNORECASE)
            if answer_match:
                answer = normalize_text(answer_match.group(1))
                question = self.trivia_state.get("question", description) if self.trivia_state else description
                upsert_trivia_bank(question, answer)
                self.add_event(f"Trivia timed out. Correct answer: {answer}", "RED")
            self.trivia_state = None

    def edit_time(self, event: str, amount: float):
        queue_logs = deque(maxlen=10)
        for log in self.queue_logs:
            if log[0] == event:
                queue_logs.append((log[0], log[1] + amount, log[2]))
            else:
                queue_logs.append(log)
        self.queue_logs = queue_logs

    def random_time(self, amount: int) -> float:
        return amount + random.uniform(-1, 1)

    def add_queue(self, event: str, amount: float, kwargs: dict = {}):
        self.queue_logs.append((event, time.time() + amount, kwargs))
    
    def add_event(self, message: str, color: str = "WHITE"):
        self.event_logs.append((message, color))

    def listen(self) -> None:
        """Listens for and processes incoming gateway events."""
        while self.is_connected:
            try:
                response = self.ws.recv()
                if not response:
                    continue
                
                data = json.loads(response)
                
                # Update sequence number for next heartbeat
                if data.get('s') is not None:
                    self.seq = data['s']

                op = data.get('op')
                event_type = data.get('t')

                if op == 0:
                    if event_type == "READY":
                        self.session_id = data['d']['session_id']
                        self.user_id = data['d']['user']['id']
                        self.user_name = data['d']['user']['username']
                        self.add_event(f"Connected as {self.user_name} (ID: {self.user_id})", "GREEN")
                        self.add_event(f"Session ID: {self.session_id}", "GREEN")
                        self.add_queue("NEXT_GLORY", 5)
                        if globals()["snipe"]:
                            self.add_queue("CHECK_SNIPE", self.random_time(6))
                    
                    if event_type == "MESSAGE_CREATE":
                        msg_data = data['d']
                        channel_id = msg_data.get('channel_id')

                        if channel_id == self.grind_id:
                            if msg_data.get('author', {}).get('id') == self.holger_id:
                                if msg_data.get('channel_id') == self.grind_id:
                                    if msg_data.get('content', '').startswith(f"<@{self.user_id}>"):
                                        if globals()["grind_scp"]:
                                            self.add_queue("NEXT_GLORY", self.random_time(22))

                                        content = msg_data.get('content', '')
                                        search = re.search(r"\+(\d+) Social Credits have", content)
                                        global session_count, session_credits, session_gold_bars, session_scp
                                        if search:
                                            recieved = int(search.group(1))
                                            self.add_event(f"Received {recieved} Social Credits from Holger.", "RED")
                                            session_scp += recieved
                                            session_credits += 1
                                            self.edit_time("NEXT_GLORY", -15)
                                            if globals()["gamble"]:
                                                self.add_queue("COINFLIP", self.random_time(1), {"scp": recieved % 100})
                                        elif "You have been awarded a" in content:
                                            if globals()["grind_scp"]:
                                                self.add_event(f"Received gold bar from Holger.", "YELLOW")
                                                session_gold_bars += 1
                                                self.edit_time("NEXT_GLORY", -15)
                                        else:
                                            if globals()["grind_scp"]:
                                                self.add_event("Received message from Holger.", "ORANGE")
                                                # Next glory will be 21 seconds.
                                        session_count += 1
                                        self.callbacked = True

                            for components in msg_data.get('components', []):
                                for action in components.get('components', []):
                                    if action.get('type') == 2 and msg_data.get('content', '').startswith(f"<@{self.user_id}>"):
                                        self.add_event(f"Button detected: {action.get('custom_id')}", "BLUE")
                                        self.button = True
                                        self.add_queue(
                                            "CLICK_BUTTON",
                                            self.random_time(1),
                                            {
                                                "application_id": self.holger_id,
                                                "custom_id": action.get('custom_id'),
                                                "guild_id": msg_data.get('guild_id'),
                                                "channel_id": msg_data.get('channel_id'),
                                                "message_id": msg_data.get('id'),
                                            }
                                        )

                            # I think finding components seperately 
                            # is better because it's more easy to read
                            for embed in msg_data.get('embeds', []):
                                if embed.get('title', '') == "Trivia Question" and globals()["grind_trivia"]:
                                    self.start_trivia(msg_data, embed)
                                elif embed.get('title', '') in {"Trivia Question Answered", "Error"} and self.trivia_state:
                                    self.handle_trivia_result(embed)

                            if self.trivia_state and msg_data.get('author', {}).get('id') != self.holger_id:
                                self.narrow_trivia_candidates(msg_data.get('content', ''))


                        if channel_id == self.bot_c_id:
                            global session_coinflips, session_coinflips_success, session_coinflips_scp
                            content = msg_data.get('content', '')
                            match = re.search(r"has ([\d,]+) Gold Bars?", content)
                            if match and self.check_gold and globals()["snipe"]:
                                gold_amount = int(match.group(1).replace(",", ""))
                                if gold_amount > 0:
                                    self.add_event(f"Holger has {gold_amount} gold bars", "YELLOW")
                                    self.add_queue("SNIPE", self.random_time(1), {"gold_amount": gold_amount})
                                    self.check_gold = False  # Reset to allow NEXT_GLORY during snipe
                                else:
                                    self.add_event("Shop has 0 gold bars.", "YELLOW")
                                    self.check_gold = False
                                    self.add_queue("CHECK_SNIPE", self.random_time(60))

                                match = re.search(r"The coin landed on (heads|tails)", content)
                                if match and globals()["gamble"]:
                                    result = match.group(1)
                                    self.add_event(f"Coinflip result: {result}", "MAGENTA")
                                    session_coinflips += 1
                                    
                                    gamble_amt = getattr(self, "current_gamble_amount", 0)

                                    if result == "heads":
                                        self.add_event(f"Coinflip win. Gained {gamble_amt * 2} SCP.", "GREEN")
                                        session_coinflips_success += 1
                                        session_coinflips_scp += gamble_amt * 2
                                    else:
                                        self.add_event(f"Coinflip loss. Lost {gamble_amt} SCP.", "RED")
                                        session_coinflips_scp -= gamble_amt
                                    globals()["gamble"] = False
                                    
                                elif "I dropped the coin" in content and globals()["gamble"]:
                                    gamble_amt = getattr(self, "current_gamble_amount", 0)
                                    self.add_event(f"Coinflip sides. Lost {gamble_amt / 2} SCP.", "RED")
                                    session_coinflips += 1
                                    session_coinflips_scp -= gamble_amt / 2
                                    globals()["gamble"] = False
                                    
                            for embed in msg_data.get('embeds', []):
                                if embed.get('title', '') == "Success":
                                    if "You have bought" in embed.get('description', ''):
                                        gold_match = re.search(r"You bought (\d+) Gold Bars?", embed.get('description', ''))
                                        if gold_match:
                                            gold_amount = int(gold_match.group(1))
                                            self.add_event(f"Successfully sniped {gold_amount} gold bars.", "YELLOW")
                                            session_sniped_gold += gold_amount
                                            self.check_gold = False
                                            self.add_queue("CHECK_SNIPE", self.random_time(60))

                                elif embed.get('title', '') == "Error":
                                    error_desc = embed.get('description', '')
                                    if "You do not" in error_desc and "SCP" in error_desc:
                                        # Not enough SCP, try with lower amount
                                        if self.snipe_amount > 1:
                                            new_amount = self.snipe_amount - 1
                                            self.add_event(f"Not enough SCP, retrying with {new_amount} gold bars.", "ORANGE")
                                            self.add_queue("SNIPE", self.random_time(1), {"gold_amount": new_amount})
                                        else:
                                            self.add_event("Failed to snipe. Not enough SCP for even 1 gold bar.", "RED")
                                            self.check_gold = False
                                            self.add_queue("CHECK_SNIPE", self.random_time(60))
                                    elif "The bank does not have enough gold bars" in error_desc:
                                        self.add_event("Bank doesn't have enough gold bars.", "RED")
                                        self.check_gold = False
                                        self.add_queue("CHECK_SNIPE", self.random_time(60))

                                elif embed.get('title', '') == "Trivia Question":
                                    if globals()["grind_trivia"]:
                                        global session_trivia, session_trivia_answered
                                        session_trivia += 1

                                        question = embed.get('description', '')
                                        trivia_entry = self.find_trivia_entry(question)
                                        if not trivia_entry:
                                            self.add_event("Could not match trivia question in trivia.json.", "ORANGE")
                                            continue

                                        correct_answer = normalize_text(trivia_entry.get('correct_answer', ''))
                                        answers = []
                                        for field in embed.get('fields', []):
                                            if field.get('name', '').startswith("Option"):
                                                answers.append(field.get('value', ''))

                                        matching_index = None
                                        for index, answer in enumerate(answers):
                                            if normalize_text(answer) == correct_answer:
                                                matching_index = index
                                                break

                                        if matching_index is None:
                                            self.add_event(f"Trivia matched, but no exact option matched: {correct_answer}", "ORANGE")
                                            continue

                elif op == 11:
                    pass

            except websocket.WebSocketConnectionClosedException:
                self.is_connected = False
                self.start(run_forever=False)

            except Exception as e:
                self.is_connected = False

    def loop(self):
        current_time = time.time()

        # for log in self.event_logs:
        #     print(log[0])

        # for log in self.queue_logs:
        #    print(log[0])

        due_item = None
        for event, event_time, kwargs in self.queue_logs:
            if event_time <= current_time:
                due_item = (event, event_time, kwargs)
                break

        if due_item:
            next_event, _, kwargs = due_item

            if next_event == "NEXT_GLORY" and self.callbacked and not self.button and not self.check_gold:
                if self.trivia_state:
                    self.edit_time("NEXT_GLORY", 5)
                    self.add_event("Delaying NEXT_GLORY due to active trivia.", "ORANGE")
                else:
                    self.callbacked = False
                    self.subscribe_to_channel(self.guild_id, self.grind_id)
                    self.send_message(self.grind_id, self.message)
                    self.queue_logs.remove(due_item)
                    # self.queue_logs.append(("NEXT_GLORY", current_time + 21))   
                    self.add_event("Sent message to grind channel.", "BLUE")

            if next_event == "CLICK_BUTTON":
                global session_buttons
                self.click(**kwargs)
                session_buttons += 1
                self.queue_logs.remove(due_item)
                self.add_event(f"Successfully clicked button: {kwargs['custom_id']}", "BLUE")
                self.button = False
                self.edit_time("NEXT_GLORY", -15)

            if next_event == "TRIVIA_REPLY":
                if not self.trivia_state:
                    self.queue_logs.remove(due_item)
                else:
                    answer = self.resolve_trivia_reply()
                    if answer:
                        self.send_message(kwargs['channel_id'], answer, kwargs['message_id'])
                        self.add_event(f"Sent trivia answer: {answer}", "BLUE")
                    else:
                        self.add_event("Trivia had no available answer.", "ORANGE")
                    self.queue_logs.remove(due_item)

            if next_event == "CHECK_SNIPE":
                self.check_gold = True # this will just temp pause the program
                self.check_gold_time = current_time  # Track when we set check_gold
                # in case subscribing back does not work
                self.queue_logs.remove(due_item)
                self.subscribe_to_channel(self.guild_id, self.bot_c_id)
                shop_options = [
                    {
                        "type": 1,
                        "name": "check",
                        "options": [
                            {
                                "type": 3,
                                "name": "value",
                                "value": "gold bars"
                            },
                            {
                                "type": 6,
                                "name": "member",
                                "value": self.holger_id
                            }
                        ]
                    }
                ]
                self.command(
                    application_id=self.holger_id,
                    channel_id=self.bot_c_id,
                    command_id="1509679847029473310",
                    command_name="shop",
                    version="1509679847029473311",
                    options=shop_options,
                    guild_id=self.guild_id
                )

            if next_event == "SNIPE":
                self.queue_logs.remove(due_item)
                self.edit_time("GAMBLE", 2) # in case of rate limit
                gold_amount = kwargs.get("gold_amount", 0)
                self.subscribe_to_channel(self.guild_id, self.bot_c_id)
                if gold_amount > 0:
                    self.snipe_amount = gold_amount  # Track for retry logic
                    self.add_event(f"Attempting to snipe {gold_amount} gold bars.", "YELLOW")
                    buy_options = [
                        {
                            "type": 1,
                            "name": "buy",
                            "options": [
                                {
                                    "type": 3,
                                    "name": "item",
                                    "value": "\ud83d\udcb0Gold bar" # stated from discord api
                                },
                                {
                                    "type": 4,
                                    "name": "amount",
                                    "value": gold_amount
                                }
                            ]
                        }
                    ]
                    self.command(
                        application_id=self.holger_id,
                        channel_id=self.bot_c_id,
                        command_id="1509679847029473310",
                        command_name="shop",
                        version="1509679847029473311",
                        options=buy_options,
                        guild_id=self.guild_id
                    )
                else:
                    # gold_amount reached 0, stop attempting
                    self.check_gold = False
                    self.add_queue("CHECK_SNIPE", self.random_time(60)) # check again in a bit

            if next_event == "COINFLIP":
                self.queue_logs.remove(due_item)
                scp_amount = kwargs.get("scp", 0)
                self.current_gamble_amount = scp_amount
                self.subscribe_to_channel(self.guild_id, self.bot_c_id)
                self.add_event(f"Attempting coinflip gamble with {scp_amount} SCP.", "MAGENTA")
                flip_options = [
                    {
                        "type": 1,
                        "name": "coinflip",
                        "options": [
                            {
                                "type": 4,
                                "name": "amount",
                                "value": scp_amount
                            },
                            {
                                "type": 3,
                                "name": "side",
                                "value": "heads"
                            }
                        ]
                    }
                ]
                self.command(
                    application_id=self.holger_id,
                    channel_id=self.bot_c_id,
                    command_id="1509679839454433330",
                    command_name="scp",
                    version="1509679839454433331",
                    options=flip_options,
                    guild_id=self.guild_id
                )

class CursesUI:
    def __init__(self, client: Client):
        self.client = client
        self.start_time = time.time()
        self.page = 0
        self.max_pages = 5
        self.settings_options = [
            ("grind_scp", "Grind SCP"),
            ("grind_trivia", "Grind Trivia"),
            ("snipe", "Snipe Gold Bars"),
            ("gamble", "Gamble (Coinflip)")
        ]
        self.settings_selected = 0
        self.window = curses.initscr()
        self.help = "Press < for previous page, > for next page, q to quit."

        # Prevent getch() from blocking the render loop.
        self.window.nodelay(True)
        self.window.keypad(True)
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

        # since events disappear automatically basically
        # we keep the most recent 8
        self.events = deque(maxlen=8)

    def draw(self):
        self.window.erase()

        key = self.window.getch()
        if key in (ord('<'), ord(','), curses.KEY_LEFT):
            self.page = (self.page + 1) % self.max_pages
        elif key in (ord('>'), ord('.'), curses.KEY_RIGHT):
            self.page = (self.page - 1) % self.max_pages
        elif key == ord('q'):
            curses.nocbreak()
            curses.echo()
            curses.endwin()
            exit()
        elif self.page == 4:
            if key == curses.KEY_UP:
                self.settings_selected = (self.settings_selected - 1) % len(self.settings_options)
            elif key == curses.KEY_DOWN:
                self.settings_selected = (self.settings_selected + 1) % len(self.settings_options)
            elif key in (curses.KEY_ENTER, 10, 13):
                opt = self.settings_options[self.settings_selected][0]
                globals()[opt] = not globals()[opt]
                save_settings()

        if self.page == 0:
            self.window.addstr(0, 0, f"Logs ({self.help})", curses.A_BOLD)
            self.window.addstr(2, 0, "Queue", curses.A_REVERSE)
            queue_logs = list(self.client.queue_logs)[-8:]
            for i, log in enumerate(queue_logs):
                event, event_time, kwargs = log
                time_remaining = max(0, event_time - time.time())
                self.window.addstr(3 + i, 0, f"{event}: {time_remaining:.1f}s")

            self.window.addstr(2, 30, "Events", curses.A_REVERSE)
            while self.client.event_logs:
                self.events.append(self.client.event_logs.popleft())

            for i, log in enumerate(self.events):
                message, color = log
                color_pair = {
                    "RED": curses.color_pair(1),
                    "GREEN": curses.color_pair(2),
                    "YELLOW": curses.color_pair(3),
                    "BLUE": curses.color_pair(4),
                    "MAGENTA": curses.color_pair(5),
                }.get(color, curses.A_NORMAL)
                self.window.addstr(3 + i, 30, message, color_pair)

        if self.page == 1:
            runtime = max(1e-9, time.time() - self.start_time)
            credit_rate = (session_credits / session_count * 100) if session_count else 0.0
            trivia_rate = (session_trivia_answered / session_trivia * 100) if session_trivia else 0.0
            bar_rate = (session_gold_bars / session_count * 100) if session_count else 0.0

            self.window.addstr(0, 0, f"Session SCP Grinding ({self.help})", curses.A_BOLD)
            self.window.addstr(2, 0, f"Session messages: {session_count} | Session trivia: {session_trivia}")
            self.window.addstr(3, 0, f"Session messages SCP: {session_scp} | {credit_rate:.1f}% Chance | Hourly: {session_scp * 3600 / runtime:.1f} SCP/h")
            self.window.addstr(4, 0, f"Session trivia SCP: {session_trivia_scp} | {trivia_rate:.1f}% Answered | Hourly: {session_trivia_scp * 3600 / runtime:.1f} SCP/h")
            self.window.addstr(5, 0, f"Session raw SCP: {session_scp + session_trivia_scp} | Hourly: {(session_scp + session_trivia_scp) * 3600 / runtime:.1f} SCP/h")
            self.window.addstr(6, 0, f"Session Gold Bars: {session_gold_bars} | {bar_rate:.1f}% Chance")
            self.window.addstr(7, 0, "*Note gold bars does not account for sniper bars.", curses.A_DIM)

            button_rate = (session_buttons / session_count * 100) if session_count else 0.0
            button_time = runtime / session_buttons if session_buttons else 0.0
            self.window.addstr(9, 0, f"Session buttons: {session_buttons} | Button every ~{button_time:.1f}s | {button_rate:.1f}% Chance/message")

            snipe_time = runtime / session_sniped_gold if session_sniped_gold else 0.0
            self.window.addstr(10, 0, f"Session gold sniped: {session_sniped_gold} | Gold restocked every ~{snipe_time:.1f}s")

        if self.page == 2:
            total_count = count + session_count
            total_credits = credits + session_credits
            total_scp = scp + session_scp
            total_buttons = buttons + session_buttons
            total_trivia_scp = trivia_scp + session_trivia_scp
            total_trivia = trivia + session_trivia
            total_trivia_answered = trivia_answered + session_trivia_answered
            total_gold_bars = gold_bars + session_gold_bars
            
            credit_rate = (total_credits / total_count * 100) if total_count else 0.0
            trivia_rate = (total_trivia_answered / total_trivia * 100) if total_trivia else 0.0
            bar_rate = (total_gold_bars / total_count * 100) if total_count else 0.0

            self.window.addstr(0, 0, f"Global SCP Grinding ({self.help})", curses.A_BOLD)
            self.window.addstr(2, 0, f"Total messages: {total_count} | Total trivia: {total_trivia}")
            self.window.addstr(3, 0, f"Total messages SCP: {total_scp} | {credit_rate:.1f}% Chance")
            self.window.addstr(4, 0, f"Total trivia SCP: {total_trivia_scp} | {trivia_rate:.1f}% Answered")
            self.window.addstr(5, 0, f"Total raw SCP: {total_scp + total_trivia_scp}")
            self.window.addstr(6, 0, f"Total Gold Bars: {total_gold_bars} | {bar_rate:.1f}% Chance")
            self.window.addstr(7, 0, "*Note gold bars does not account for sniper bars.", curses.A_DIM)

            button_rate = (total_buttons / total_count * 100) if total_count else 0.0
            self.window.addstr(9, 0, f"Total buttons: {total_buttons} | {button_rate:.1f}% Chance/message")

            total_sniped_gold = sniped_gold + session_sniped_gold
            self.window.addstr(10, 0, f"Total gold sniped: {total_sniped_gold}")

        if self.page == 3:
            total_coinflips = coinflips + session_coinflips
            total_coinflips_success = coinflips_success + session_coinflips_success
            total_coinflips_scp = coinflips_scp + session_coinflips_scp
            session_coinflips_loss = session_coinflips - session_coinflips_success
            total_coinflips_loss = total_coinflips - total_coinflips_success
            session_coinflips_net = session_coinflips_scp
            total_coinflips_net = coinflips_scp + session_coinflips_scp
            runtime = max(1e-9, time.time() - self.start_time)
            win_rate = (session_coinflips_success / session_coinflips * 100) if session_coinflips else 0.0
            total_win_rate = (total_coinflips_success / total_coinflips * 100) if total_coinflips else 0.0

            self.window.addstr(0, 0, f"Gambling Stats ({self.help})", curses.A_BOLD)
            self.window.addstr(2, 0, f"Session coinflips: {session_coinflips}")
            self.window.addstr(3, 0, f"Session wins: {session_coinflips_success} | Losses: {session_coinflips_loss}")
            self.window.addstr(4, 0, f"Session win rate: {win_rate:.1f}%")
            self.window.addstr(5, 0, f"Session SCP net: {session_coinflips_net}")
            self.window.addstr(6, 0, f"Session SCP/h: {session_coinflips_net * 3600 / runtime:.1f}")
            self.window.addstr(8, 0, f"Total coinflips: {total_coinflips}")
            self.window.addstr(9, 0, f"Total wins: {total_coinflips_success} | Losses: {total_coinflips_loss}")
            self.window.addstr(10, 0, f"Total win rate: {total_win_rate:.1f}%")
            self.window.addstr(11, 0, f"Total SCP net: {total_coinflips_net}")

        if self.page == 4:
            self.window.addstr(0, 0, f"Settings ({self.help})", curses.A_BOLD)
            for idx, (var, label) in enumerate(self.settings_options):
                value = globals()[var]
                sel = curses.A_REVERSE if idx == self.settings_selected else curses.A_NORMAL
                self.window.addstr(2 + idx, 0, f"{label}: {'ON' if value else 'OFF'}", sel)

        self.window.refresh()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCP Client")
    parser.add_argument("--token", type=str, help="Discord Token")
    parser.add_argument("--no-ui", action="store_true", default=False, help="Run without UI")
    args = parser.parse_args()
    no_ui = args.no_ui or not curses
    token = None
    if args.token:
        token = args.token
    else:
        load_dotenv()
        token = os.getenv("TOKEN")
    if not token:
        raise ValueError("TOKEN is not set in the environment variables or provided as an argument.")
    
    load_persistents()
    atexit.register(save_persistents)
    
    client = Client(token)
    # client.queue_logs.append(("NEXT_GLORY", time.time() + 21))
    client.start(run_forever=False)
    
    ui = None
    if not no_ui:
        logging.getLogger("DiscordWS").setLevel(logging.WARNING)
        ui = CursesUI(client)

    while True:
        client.loop()

        if ui is not None:
            ui.draw()

        time.sleep(0.05)
