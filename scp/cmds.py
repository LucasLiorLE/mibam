import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

GUILD_ID = "820093197933740062"
APP_ID = "1050445714825695242" 

# Discord's official mapping of option types to human-readable names
OPTION_TYPES = {
    1: "SUB_COMMAND",
    2: "SUB_COMMAND_GROUP",
    3: "STRING",
    4: "INTEGER",
    5: "BOOLEAN",
    6: "USER",
    7: "CHANNEL",
    8: "ROLE",
    9: "MENTIONABLE",
    10: "NUMBER",
    11: "ATTACHMENT"
}

def print_tree(options, indent_level=1):
    """Recursively prints the command tree (Groups -> Subcommands -> Arguments)"""
    indent = "    " * indent_level
    for opt in options:
        opt_type = opt.get("type")
        opt_name = opt.get("name")
        type_name = OPTION_TYPES.get(opt_type, f"UNKNOWN({opt_type})")
        
        # Is this argument required or optional?
        required = opt.get("required", False)
        req_str = "(Required)" if required else "(Optional)"

        if opt_type == 2: # SUB_COMMAND_GROUP
            print(f"{indent}Group: {opt_name}")
            if "options" in opt:
                print_tree(opt["options"], indent_level + 1)
                
        elif opt_type == 1: # SUB_COMMAND
            print(f"{indent}Subcommand: {opt_name}")
            if "options" in opt:
                print_tree(opt["options"], indent_level + 1)
                
        else: # Regular Argument (String, Integer, User, etc.)
            print(f"{indent}Argument: {opt_name} | Type: {type_name} {req_str}")

def fetch_slash_commands():
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/application-command-index"
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        all_commands = data.get("application_commands", [])
        bot_commands = [cmd for cmd in all_commands if cmd.get("application_id") == APP_ID]
        
        print(f"Found {len(bot_commands)} base commands for Holger Danske:\n")
        print("="*50)
        
        for cmd in bot_commands:
            name = cmd.get("name")
            cmd_id = cmd.get("id")
            version = cmd.get("version")
            
            print(f"Command: /{name}")
            print(f"    ID: {cmd_id}")
            print(f"    Version: {version}")
            
            # Print the nested structure if it has options
            if "options" in cmd:
                print_tree(cmd["options"])
                
            print("="*50)
    else:
        print(f"Error fetching commands: {response.status_code} - {response.text}")

if __name__ == "__main__":
    fetch_slash_commands()