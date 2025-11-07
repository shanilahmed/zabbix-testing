"""
AI Maintenance Assistant for Zabbix 7.2
Interactive Maintenance Assistant with AI

Developed by: Grover T.
Date: 2025
Version: 1.7.0

Interactive system for creating maintenance tasks in Zabbix using AI.
Supports one-time and routine maintenance tasks (daily, weekly, monthly)
with advanced ticket and bitmask management.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import datetime
import json
import re
import logging
from typing import List

# ----- Configuración de Logging -----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ----- Configuración de Variables -----
ZABBIX_API_URL = "http://localhost/zabbix/api_jsonrpc.php"
ZABBIX_TOKEN = "77af53397a33bed3688bef7b428ec1c0fa91256c9c691779c482a1c158f28a33"
AI_PROVIDER = "gemini"

# Configuración para OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")

# Configuración para Gemini
#GEMINI_API_KEY = "AIzaSyCce4fWLTYS4FOmtagEs-Y7PAnh9EdjGxw"
GEMINI_API_KEY = "AIzaSyDOCPROMf6gN56NyhueIGU8AvHOIAamIMk"
GEMINI_MODEL = "gemini-2.0-flash"

# ----- Inicialización de la IA -----
openai_client = None
gemini_model = None
loaded_provider = None

if AI_PROVIDER == "openai":
    try:
        from openai import OpenAI
        if OPENAI_API_KEY:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            loaded_provider = "openai"
            logger.info(f"OpenAI configured. Model: {OPENAI_MODEL}")
        else:
            logger.error("OPENAI_API_KEY is missing to use OpenAI")
    except Exception as e:
        logger.error(f"Error initializing OpenAI: {e}")

elif AI_PROVIDER == "gemini":
    try:
        import google.generativeai as genai
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            loaded_provider = "gemini"
            logger.info(f"Gemini configured. Model: {GEMINI_MODEL}")
        else:
            logger.error("Missing GOOGLE_API_KEY to use Gemini")
    except Exception as e:
        logger.error(f"Error initializing Gemini: {e}")
else:
    logger.error(f"AI provider not supported:{AI_PROVIDER}")

app = Flask(__name__)
CORS(app)

# ----- Class for the Zabbix API (7.2) -----
class ZabbixAPI:
    """Class to interact with the Zabbix 7.2 API"""
    
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def _make_request(self, method: str, params: dict) -> dict:
        """Base method for API calls"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        try:
            logger.info(f"API call: {method} with parameters: {params}")
            
            response = requests.post(
                self.url, 
                json=payload, 
                headers=self.headers, 
                timeout=30
            )
            
            logger.info(f"Status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Answer: {result}")
            
            if "error" in result:
                logger.error(f"Error in API Zabbix: {result['error']}")
                return {"error": result["error"]}
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in Zabbix API request: {str(e)}")
            return {"error": f"Connection error: {str(e)}"}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response: {str(e)}")
            return {"error": f"Invalid response from server: {str(e)}"}
    
    def get_hosts(self, host_names: List[str]) -> List[dict]:
        """Get host information by name"""
        if not host_names:
            return []
            
        params = {
            "output": ["hostid", "host", "name", "status"],
            "filter": {"host": host_names}
        }
        
        result = self._make_request("host.get", params)
        
        if "error" in result:
            logger.error(f"Error getting hosts: {result['error']}")
            return []
        
        hosts = result.get("result", [])
        logger.info(f"Hosts found: {len(hosts)}")
        return hosts
    
    def search_hosts(self, search_term: str) -> List[dict]:
        """Search for hosts that contain the search term"""
        params = {
            "output": ["hostid", "host", "name", "status"],
            "search": {"host": search_term, "name": search_term},
            "searchWildcardsEnabled": True,
            "limit": 20
        }
        
        result = self._make_request("host.get", params)
        
        if "error" in result:
            logger.error(f"Error searching for hosts: {result['error']}")
            return []
            
        return result.get("result", [])
    
    def get_hosts_by_tags(self, tags: List[dict]) -> List[dict]:
        """Get hosts that match the specified tags"""
        if not tags:
            return []
            
        params = {
            "output": ["hostid", "host", "name", "status"],
            "evaltype": 0,  # AND/OR
            "tags": tags
        }
        
        result = self._make_request("host.get", params)
        
        if "error" in result:
            logger.error(f"Error getting hosts by tags: {result['error']}")
            return []
            
        return result.get("result", [])
    
    def get_hostgroups(self, group_names: List[str]) -> List[dict]:
        """Get group information by name"""
        if not group_names:
            return []
            
        params = {
            "output": ["groupid", "name"],
            "filter": {"name": group_names}
        }
        
        result = self._make_request("hostgroup.get", params)
        
        if "error" in result:
            logger.error(f"Error getting groups: {result['error']}")
            return []
            
        return result.get("result", [])
    
    def search_hostgroups(self, search_term: str) -> List[dict]:
        """Search for groups that contain the search term"""
        params = {
            "output": ["groupid", "name"],
            "search": {"name": search_term},
            "searchWildcardsEnabled": True,
            "limit": 20
        }
        
        result = self._make_request("hostgroup.get", params)
        
        if "error" in result:
            logger.error(f"Error searching for groups: {result['error']}")
            return []
            
        return result.get("result", [])
    
    def get_hosts_by_groups(self, group_names: List[str]) -> List[dict]:
        """Get hosts belonging to the specified groups"""
        if not group_names:
            return []
            
        # First get the group IDs
        groups_result = self._make_request("hostgroup.get", {
            "output": ["groupid", "name"],
            "filter": {"name": group_names}
        })
        
        if "error" in groups_result:
            logger.error(f"Error getting groups: {groups_result['error']}")
            return []
        
        groups = groups_result.get("result", [])
        if not groups:
            logger.warning(f"No groups found: {group_names}")
            return []
        
        group_ids = [g["groupid"] for g in groups]
        
        # Get hosts from those groups
        params = {
            "output": ["hostid", "host", "name", "status"],
            "groupids": group_ids
        }
        
        result = self._make_request("host.get", params)
        
        if "error" in result:
            logger.error(f"Error getting hosts by groups: {result['error']}")
            return []
            
        return result.get("result", [])
    
    def create_maintenance(self, name: str, host_ids: List[str] = None, 
                         group_ids: List[str] = None, start_time: int = None, 
                         end_time: int = None, description: str = "", 
                         tags: List[dict] = None, recurrence_type: str = "once",
                         recurrence_config: dict = None) -> dict:
        """
Creating a maintenance period in Zabbix 7.2
Supports one-time and recurring maintenance

recurrence_type: "once", "daily", "weekly", "monthly"
recurrence_config: Recurrence-specific configuration
        """
        try:
            params = {
                "name": name,
                "active_since": start_time,
                "active_till": end_time,
                "description": description,
                "maintenance_type": 0,  # with data collection
            }
            
            # Configure time periods based on recurrence type
            if recurrence_type == "once":
                # One-time maintenance
                params["timeperiods"] = [{
                    "timeperiod_type": 0,  # single period
                    "start_date": start_time,
                    "period": end_time - start_time
                }]
                
            elif recurrence_type == "daily":
                #Daily maintenance
                if not recurrence_config:
                    raise ValueError("Recurrence_config is required for daily maintenance.")
                    
                params["timeperiods"] = [{
                    "timeperiod_type": 2,  # daily
                    "start_time": recurrence_config.get("start_time", 0),
                    "period": recurrence_config.get("duration", 3600),
                    "every": recurrence_config.get("every", 1)
                }]
                
            elif recurrence_type == "weekly":
                # Weekly maintenance
                if not recurrence_config:
                    raise ValueError("Recurrence_config is required for weekly maintenance.")                
                
                dayofweek_bitmask = recurrence_config.get("dayofweek", 1)
                
                params["timeperiods"] = [{
                    "timeperiod_type": 3,  # semanal
                    "start_time": recurrence_config.get("start_time", 0),
                    "period": recurrence_config.get("duration", 3600),
                    "dayofweek": dayofweek_bitmask,
                    "every": recurrence_config.get("every", 1),                   
                }]
                
            elif recurrence_type == "monthly":
                # Monthly maintenance
                if not recurrence_config:
                    raise ValueError("Recurrence_config is required for monthly maintenance.")
                
                timeperiod = {
                    "timeperiod_type": 4,  # Monthly
                    "start_time": recurrence_config.get("start_time", 0),
                    "period": recurrence_config.get("duration", 3600),
                    "month": recurrence_config.get("month", 4095),
                }
                
                # Determine if it is by day of the month or day of the weeka
                if "day" in recurrence_config: 
                    # By specific day of the month (e.g. 5th of each month)
                    timeperiod["day"] = recurrence_config["day"]
                    timeperiod["every"] = recurrence_config.get("every", 1)  # Every X months
                    
                elif "dayofweek" in recurrence_config:                    
                    timeperiod["dayofweek"] = recurrence_config["dayofweek"]  
                    timeperiod["every"] = recurrence_config.get("every", 1)  
                    
                else:
                    # By default, first day of the month
                    timeperiod["day"] = 1
                    timeperiod["every"] = recurrence_config.get("every", 1)
                
                params["timeperiods"] = [timeperiod]
            
            else:
                raise ValueError(f"Recurrence type not supported: {recurrence_type}")
            
            # Add specific hosts if provided
            if host_ids:
                params["hosts"] = [{"hostid": hid} for hid in host_ids]
            
            # Add groups if provided
            if group_ids:
                params["groups"] = [{"groupid": gid} for gid in group_ids]
            
            # Add specific tags for maintenance if provided
            if tags:
                params["tags"] = tags
            
            logger.info(f"Creating maintenance with parameters: {json.dumps(params, indent=2)}")
            return self._make_request("maintenance.create", params)
            
        except Exception as e:
            logger.error(f"Error preparing maintenance parameters: {str(e)}")
            return {"error": f"Configuration error: {str(e)}"}

    def test_connection(self) -> dict:
        """Test the API connection"""
        result = self._make_request("user.get", {
            "output": ["userid", "username"],
            "limit": 1
        })
        return result


# ----- Auxiliary functions -----
def safe_strip(value, default=""):
    """Helper function to safely strip()"""
    if value is None:
        return default
    return str(value).strip()

def generate_maintenance_description(parsed_data: dict, user_info: dict = None) -> str:
    """
    Generates the maintenance description, including ticket and user information
    in an organized format (each piece of information on its own line).
    """
    import re

    # Descripción base
    description = parsed_data.get("description", "Maintenance created via AI Widget")
    ticket_number = safe_strip(parsed_data.get("ticket_number"))
    ticket_inline_pattern = re.compile(
        r'\s*[-–—]?\s*Ticket:\s*\d{3}-\d{3,6}\s*',
        flags=re.IGNORECASE
    )
    cleaned_description = ticket_inline_pattern.sub('', description).strip()

    # 2) If we were not given an explicit ticket, we try to extract it from the original description
    if not ticket_number:
        m = re.search(r'\b(\d{3}-\d{3,6})\b', description)
        if m:
            ticket_number = m.group(1)

    # 3) Assemble on separate lines
    lines = [cleaned_description if cleaned_description else "Maintenance created via AI Widget"]

    # Add ticket if it exists (and is not already embedded)
    if ticket_number:
        lines.append(f"Ticket: {ticket_number}")

    # Add user information if available
    if user_info:
        # Build username
        user_display = ""
        if user_info.get("name") or user_info.get("surname"):
            user_display = " ".join(filter(None, [user_info.get("name"), user_info.get("surname")]))
        if not user_display:
            user_display = user_info.get("username", "Unknown user")

        # Add user at the end, on a new line
        lines.append(f"User: {user_display}")

    # 4) Return all lines joined with line breaks
    return "\n".join(lines)


def generate_maintenance_name(parsed_data: dict, host_names: list = None, group_names: list = None) -> str:
    """
    Generates the maintenance name based on the ticket and recurrence type
    """
    ticket_number = parsed_data.get("ticket_number", "").strip()
    recurrence_type = parsed_data.get("recurrence_type", "once")
    
    # Base prefix according to type of maintenance
    if recurrence_type == "once":
        base_prefix = "AI Maintenance"
    else:
        base_prefix = "AI Routine Maintenance"
    
    # If there is a ticket, use it as the main name
    if ticket_number:
        return f"{base_prefix}: {ticket_number}"
    
    # If there is no ticket, use the current system (resource names)
    maintenance_name_parts = []
    
    if host_names:
        maintenance_name_parts.extend(host_names[:3])
        if len(host_names) > 3:
            maintenance_name_parts.append(f"y {len(host_names)-3} hosts more")
    
    if group_names:
        maintenance_name_parts.extend([f"Group {name}" for name in group_names[:2]])
        if len(group_names) > 2:
            maintenance_name_parts.append(f"y {len(group_names)-2} more Groups")
    
    if maintenance_name_parts:
        return f"{base_prefix}: {', '.join(maintenance_name_parts)}"
    else:
        return f"{base_prefix}: Various resources"


# ----- Class for the AI ​​Parser (Now Interactive) -----
class AIParser:
    """Class to analyze maintenance requests using AI interactively"""
    
    @staticmethod
    def _extract_ticket_number(text: str) -> str:
        """Extracts the ticket number from the user's text"""        
        if text is None:
            return ""
            
        # Patterns for different ticket formats: 100-178306, 200-8341, 500-43116
        ticket_patterns = [
            r'\b\d{3}-\d{3,6}\b',  # Format XXX-XXXXXX
            r'\bticket\s*:?\s*(\d{3}-\d{3,6})\b',  # "ticket: XXX-XXXXXX"
            r'\b#(\d{3}-\d{3,6})\b',  # "#XXX-XXXXXX"
        ]
        
        for pattern in ticket_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # If the pattern has groups, take group 1, otherwise take the entire match
                ticket = match.group(1) if match.groups() else match.group(0)
                logger.info(f"Ticket Found: {ticket}")
                return ticket
        
        logger.info("No ticket number found in the text")
        return ""
    
    @staticmethod
    def _build_interactive_prompt(user_text: str) -> str:
        """Cbuild the enhanced interactive prompt for AI"""
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        tomorrow_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
        return f"""
You are a specialized Zabbix assistant who helps create maintenance tasks. You are friendly, helpful, and conversational.

CURRENT DATE: {current_date}
TOMORROW DATE: {tomorrow_date}

USER MESSAGE: "{user_text}"

IMPORTANT: For routine maintenance tasks, build the JSON file DIRECTLY with the correct bitmask calculations.

EQUIPMENT TERMINOLOGY - Recognize these terms as servers/hosts:
- CIs, Configuration Items
- Servers, servers, srv
- Equipment, hosts, machines
- Routers, switches, devices
- Nodes, nodes, systems
- Instances, instances
- Appliances, appliances

MESSAGE ANALYSIS:
Determine what type of message it is and respond appropriately:

1. **VALID MAINTENANCE REQUEST**: If the user requests to create a maintenance request, respond with JSON:
```json
{{
    "type": "maintenance_request",
    "hosts": ["server1", "server2"], // array of strings with specific server names (optional)
    "groups": ["group1", "group2"], // array of strings with group names (optional)
    "trigger_tags": [{{"tag": "component", "value": "cpu"}}], // array of tag objects for specific triggers (optional)
    "start_time": "YYYY-MM-DD HH:MM", // string in start format
    "end_time": "YYYY-MM-DD HH:MM", // string in end format
    "description": "Maintenance description",
    "recurrence_type": "once", // "once" | "daily" | "weekly" | "monthly"
    "recurrence_config": {{}}, // object with recurrence configuration (only if not "once")
    "ticket_number": "100-178306", // string with ticket number if mentioned
    "confidence": 95, // confidence number 0-100
    "message": "Perfect! I've set up your maintenance. Review the details and confirm everything is correct."
}}
```

ROUTINE RECURRENCE SETTINGS:

For "daily":
{{"start_time": seconds_since_midnight, "duration": duration_in_seconds, "every": every_x_days}}

For "weekly" - CALCULATE THE BITMASK DIRECTLY:
{{"start_time": seconds_since_midnight, "duration": duration_in_seconds, "dayofweek": calculated_bitmask, "every": every_x_weeks}}

DAY BITMASKS (USE THESE EXACT VALUES):
- Monday: 1
- Tuesday: 2
- Wednesday: 4
- Thursday: 8
- Friday: 16
- Saturday: 32
- Sunday: 64

BITMASK CALCULATION EXAMPLES:
- Monday only: dayofweek = 1
- Thursday only: dayofweek = 8
- Friday only: dayofweek = 16
- Thursday AND Friday: dayofweek = 8 + 16 = 24
- Monday, Wednesday, Friday: dayofweek = 1 + 4 + 16 = 21
- All weekdays: dayofweek = 1 + 2 + 4 + 8 + 16 = 31
- Weekend: dayofweek = 32 + 64 = 96
- Every day: dayofweek = 1 + 2 + 4 + 8 + 16 + 32 + 64 = 127

For "monthly" - SPECIFIC DAY OF THE MONTH (Day of month):
{{"start_time": seconds_since_midnight, "duration": duration_in_seconds, "day": day_of_month, "every": every_x_months, "month": bitmask_months}}

For "monthly" - SPECIFIC DAY OF THE WEEK (Day of week):
{{"start_time": seconds_since_midnight, "duration": duration_in_seconds, "dayofweek": bitmask_day, "every": occurrence_in_week, "month": bitmask_months}}

WEEK OCCURRENCES for "day of week" (USE THESE EXACT VALUES):
- First week (first): every = 1
- Second week (second): every = 2
- Third week (third): every = 3
- Fourth week (fourth): every = 4
- Last week (last): every = 5

MULTIPLE OCCURRENCES (For cases like "second and fourth Monday"):
- For multiple occurrences, add the values ​​as a bitmask:
- Second and fourth week: every = 2 + 4 = 6
- First, third, and fifth week: every = 1 + 3 + 5 = 9
- All weeks: every = 1 + 2 + 3 + 4 + 5 = 15

MONTH BITMASKS - CALCULATE DIRECTLY (USE THESE EXACT VALUES):
- January: 1, February: 2, March: 4, April: 8, May: 16, June: 32
- July: 64, August: 128, September: 256, October: 512, November: 1024, December: 2048
- All months: 4095 (sum of all)

EXAMPLES OF CALCULATING MONTH BITMASKS:
- January only: month = 1
- August only: month = 128
- January and March: month = 1 + 4 = 5
- January, March, August, September: month = 1 + 4 + 128 + 256 = 389
- Quarter 1 (Jan, Feb, Mar): month = 1 + 2 + 4 = 7
- Quarter 4 (Oct, Nov, Dec): month = 512 + 1024 + 2048 = 3584
- Even months only: month = 2 + 8 + 32 + 128 + 512 + 2048 = 2730
- Odd months only: month = 1 + 4 + 16 + 64 + 256 + 1024 = 1365
- All months: month = 4095

SPECIFIC CONFIGURATION EXAMPLES:

**"Weekly routine maintenance on Thursdays and Fridays from 5 to 7 am":**
```json
{{
    "recurrence_type": "weekly", 
    "recurrence_config": {{ 
    "start_time": 18000, // 5:00 AM = 5 * 3600 
    "duration": 7200, // 2 hours = 2 * 3600 
    "dayofweek": 24, // Thursday(8) + Friday(16) = 24 
    "every": 1 // every week
  }}
}}
```

**"Monthly maintenance the first week from 1 to 5 am in the months of January, March, August and September":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 3600, // 1:00 AM = 1 * 3600
    "duration": 14400, // 4 hours = 4 * 3600
    "dayofweek": 127, // all days of the first week = 1+2+4+8+16+32+64
    "every": 1, // first week
    "month": 389 // January(1) + March(4) + August(128) + September(256) = 389
  }}
}}
```

**"Maintenance on the 5th of every month from 2 to 4 AM":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 7200, // 2:00 AM = 2 * 3600
    "duration": 7200, // 2 hours = 2 * 3600
    "day": 5, // 5th of the month
    "every": 1, // every month
    "month": 4095 // every month
}}
}}
```
**"First Monday of every month from 3 to 5 AM":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 10800, // 3:00 AM = 3 * 3600
    "duration": 7200, // 2 hours = 2 * 3600
    "dayofweek": 1, // Monday = 1
    "every": 1, // first week
    "month": 4095 // every month
}}
}}
```

**"Last Friday of January, April, July, and October from 1 to 3 AM":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 3600, // 1:00 AM = 1 * 3600
    "duration": 7200, // 2 hours = 2 * 3600
    "dayofweek": 16, // Friday = 16
    "every": 5, // last week
    "month": 585 // January(1) + April(8) + July(64) + October(512) = 585
}}
}}
```

**"Day 15 only in January and July from 2 to 4 AM":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 7200, // 2:00 AM = 2 * 3600
    "duration": 7200, // 2 hours = 2 * 3600
    "day": 15, // 15th day of the month
    "every": 1, // every month (where applicable)
    "month": 65 // January(1) + July(64) = 65
}}
}}
```

**"First Monday of quarter (January, April, July, October)":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 32400, // 9:00 AM = 9 * 3600
    "duration": 3600, // 1 hour = 1 * 3600
    "dayofweek": 1, // Monday = 1
    "every": 1, // first week
    "month": 585 // January(1) + April(8) + July(64) + October(512) = 585
}}
}}
```

**"Last day of every month only in even-numbered months":**
```json
{{
    "recurrence_type": "monthly",
    "recurrence_config": {{
    "start_time": 0, // 00:00 = 0 * 3600
    "duration": 3600, // 1 hour = 1 * 3600
    "day": 31, // last possible day (automatically adjusted)
    "every": 1, // every month (where applicable)
    "month": 2730 // Feb(2) + Apr(8) + Jun(32) + Aug(128) + Oct(512) + Dec(2048) = 2730
}}
}}
```

**"Daily backup from 2 to 4 AM":**
```json
{{ 
    "recurrence_type": "daily", 
    "recurrence_config": {{ 
    "start_time": 7200, // 2:00 AM = 2 * 3600 
    "duration": 7200, // 2 hours = 2 * 3600 
    "every": 1 // every day 
}}
}}
```

**"Every Monday from 2-5 AM":**
```json
{{ 
    "recurrence_type": "weekly", 
    "recurrence_config": {{ 
    "start_time": 7200, // 2:00 AM = 2 * 3600 
    "duration": 10800, // 3 hours = 3 * 3600 
    "dayofweek": 1, // Monday only = 1 
    "every": 1 // each week
}}
}}
```

IMPORTANT RULES:
- Always calculate bitmasks directly in the JSON
- For multiple days, sum the bitmask values
- For multiple months, sum the month bitmask values
- Convert hours to seconds since midnight (hour * 3600)
- Convert duration to seconds (hours * 3600)
- If you detect "tomorrow," use {tomorrow_date}; if you detect "today," use {current_date}

DATE FORMATS YOU SHOULD RECOGNIZE:
- "24/08/25 10:00am" = "2025-08-24 10:00"
- "24/08/2025 16:50" = "2025-08-24 16:50"
- "from 10:00 to 16:50" = Use the current date with those times
- "tomorrow from 8 to 10" = use {tomorrow_date} with those times
- "today from 2 to 4" = use {current_date} with those times


EXAMPLES WITH INFRASTRUCTURE TERMINOLOGY:
**"Schedule maintenance for CI srv-tuxito from 08/24/25 10:00 AM to 4:50 PM":**
```json
{{
"type": "maintenance_request",
"hosts": ["srv-tuxito"],
"start_time": "2025-08-24 10:00 AM",
"end_time": "2025-08-24 4:50 PM",
"description": "CI Monitoring-Level Maintenance",
"recurrence_type": "once",
"confidence": 90,
"message": "Perfect! I've scheduled maintenance for CI srv-tuxito."
}}
```

**"Network equipment maintenance for router01 and switch01 tomorrow 2-4 AM":**
``` json
{{
"type": "maintenance_request",
"hosts": ["router01", "switch01"],
"start_time": "{tomorrow_date} 02:00",
"end_time": "{tomorrow_date} 04:00",
"description": "Network equipment maintenance",
"recurrence_type": "once",
"confidence": 95,
"message": "Done! Scheduled maintenance for network equipment."
}}
```

- Be conversational and friendly in all messages
- Always offer additional help at the end of replies
- Use emojis sparingly to make the experience more user-friendly

2. **EXAMPLE REQUEST**: If you ask for examples, help, or don't know how to formulate a request:
```json
{{
"type": "help_request",
"message": "Of course! I'll help you with some examples of how to request maintenance:\\n\\n📋 **Basic Examples:**\\n- \\"Maintenance for srv-web01 tomorrow from 8 to 10 with ticket 100-178306\\"\\n- \\"Put server SRV-TUXITO under maintenance today from 2 to 4 PM\\"\\n- \\"Maintenance of CI SRV-TUXITO on Sunday from 2 to 4 AM\\"\\n- \\"Schedule maintenance for router CORE01 from 08/24/25 10:00 AM until 16:50\\"\\n\\n🔄 **Routine Maintenance:**\\n- \\"Daily backup for the CI srv-backup from 2 to 4 AM with ticket 200-8341\\"\\n- \\"Weekly maintenance on Sundays for network switches\\"\\n- \\"Monthly cleaning the first day of the month for all web equipment\\"\\n\\n🎫 **With Tickets:**\\nYou can always include ticket numbers like: 100-178306, 200-8341, 500-43116\\n\\n**Terminology I understand:**\\n- CI's, CIs, Configuration Items\\n- Servers, servers, equipment\\n- Routers, switches, devices\\n- Nodes, hosts, machines\\n\\nWhat type of maintenance do you need? create?",
  "examples": [
    {{
        "title": "Simple Maintenance",
        "example": "Maintenance for srv-web01 tomorrow from 8 to 10 with ticket 100-178306"
    }},
    {{
        "title": "CI Maintenance",
        "example": "Schedule maintenance for CI SRV-TUXITO from 08/24/25 10:00 AM to 4:50 PM"
    }},
    {{
        "title": "Routine Maintenance",
        "example": "Daily backup for server srv-backup from 2 to 4 AM during January with ticket 500-43116"
    }}
  ]
}}
```

3. **UNRELATED QUERY**: If you're asking about other things (status, configuration, etc.):
```json
{{
    "type": "off_topic",
    "message": "Hi! I'm your specialized assistant for **creating maintenances** in Zabbix. 🔧\\n\\nI can only help you with:\\n✅ Creating one-time maintenances\\n✅ Scheduling routine maintenances (daily, weekly, monthly)\\n✅ Maintenances with tickets\\n\\n💡 **Do you need to create a maintenance?** \\nTell me something like: \\"Maintenance for srv-web01 tomorrow from 8 to 10 with ticket 100-178306\\"\\n\\n❓ **Do you need examples?** \\nType \\"examples\\" or \\"help\\" and I'll show you how Do it.\n\nFor other Zabbix queries, use the main system tools. What maintenance do you want to create?
}}
```

4. **INCOMPLETE OR CONFUSING REQUEST**: If it's about maintenance but data is missing:
```json
{{
"type": "clarification_needed",
"message": "I understand you want to create a maintenance request, but I'm missing some details. 🤔\\n\\n**I've detected:** [explain what you detected]\\n\\n**I need to know:**\\n- 🖥️ Which servers or groups?\\n- ⏰ When? (date and time)\\n- ⏱️ For how long?\\n- 🎫 Do you have a ticket number?\\n\\n**Full example:**\\n\\"Maintenance for srv-web01 tomorrow from 8 to 10 with ticket 100-178306\\"\\n\\nCould you give me more? details?", 
"missing_info": ["hosts_or_groups", "timing", "duration"], 
"detected_info": {{}}
}}
```

**RESPOND ONLY WITH THE JSON CORRESPONDING TO THE TYPE OF MESSAGE DETECTED.**
"""
    
    @staticmethod
    def _call_openai(prompt: str) -> str:
        """Call the OpenAI API"""
        if not openai_client:
            raise RuntimeError("OpenAI is not configured correctly")
        
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You're a friendly assistant specializing in creating maintenance tasks for Zabbix. You respond in a conversational and helpful manner."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        return response.choices[0].message.content if response.choices else ""
    
    @staticmethod
    def _call_gemini(prompt: str) -> str:
        """Call the Gemini API"""
        if not gemini_model:
            raise RuntimeError("Gemini is not configured correctly")
        
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1200
            }
        )
        return response.text if hasattr(response, "text") else ""
    
    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract the JSON from the AI ​​response"""
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if not json_match:
                return {"error": "No JSON found in the response"}
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            return {"error": f"Error decoding JSON: {str(e)}"}
    
    @classmethod
    def parse_interactive_request(cls, user_text: str) -> dict:
        """Analyze any user request interactively"""
        # Extracción del ticket como respaldo
        ticket_number = cls._extract_ticket_number(user_text)
        
        prompt = cls._build_interactive_prompt(user_text)
        
        try:
            if loaded_provider == "openai":
                content = cls._call_openai(prompt)
            elif loaded_provider == "gemini":
                content = cls._call_gemini(prompt)
            else:
                return {
                    "type": "error", 
                    "message": "The AI ​​assistant is currently unavailable. Please try again later."
                }
            
            if not content:
                return {
                    "type": "error",
                    "message": "I couldn't process your request. Could you try again with more details?"
                }
            
            parsed_data = cls._extract_json(content)
            if "error" in parsed_data:
                return {
                    "type": "error",
                    "message": f"There was a problem processing your message.: {parsed_data['error']}"
                }
            
            # If it is a maintenance request, perform additional validations
            if parsed_data.get("type") == "maintenance_request":
                # If the AI ​​didn't detect the ticket but we did, add it
                if not parsed_data.get("ticket_number") and ticket_number:
                    parsed_data["ticket_number"] = ticket_number
                    logger.info(f"Ticket added by local detection: {ticket_number}")
                
                # Basic validation of fields required for maintenance
                required_fields = ["start_time", "end_time", "recurrence_type"]
                for field in required_fields:
                    if field not in parsed_data:
                        return {
                            "type": "error",
                            "message": f"Incomplete information: {field} is missing. Could you provide more details?"
                        }
                
                #Validate recurrence_type
                valid_recurrence = ["once", "daily", "weekly", "monthly"]
                if parsed_data["recurrence_type"] not in valid_recurrence:
                    return {
                        "type": "error", 
                        "message": f"Invalid recurrence type. Use: once, daily, weekly, or monthly."
                    }
                
                # If not "once", must have recurrence_config
                if parsed_data["recurrence_type"] != "once" and "recurrence_config" not in parsed_data:
                    return {
                        "type": "error",
                        "message": "Routine maintenance configuration is missing. Could you provide more details?"
                    }                
               
                if parsed_data["recurrence_type"] != "once":
                    config = parsed_data.get("recurrence_config", {})
                    
                    # Type-specific validations
                    if parsed_data["recurrence_type"] == "weekly":
                        if "dayofweek" not in config:
                            return {
                                "type": "error",
                                "message": "For weekly maintenance, I need to know the day of the week. Could you specify?"
                            }
                        # CHANGE: Validate that it is a valid bitmask (1-127) instead of individual day
                        dayofweek_bitmask = config["dayofweek"]
                        if not isinstance(dayofweek_bitmask, int) or not (1 <= dayofweek_bitmask <= 127):
                            return {
                                "type": "error",
                                "message": "Invalid weekday bitmask. Must be between 1 and 127."
                            }
                    
                    elif parsed_data["recurrence_type"] == "monthly":
                        has_day = "day" in config 
                        has_dayofweek = "dayofweek" in config
                        
                        if not has_day and not has_dayofweek:
                            return {
                                "type": "error",
                                "message": "For monthly maintenance I need to know the specific day (e.g. day 5) or day of the week (e.g. first Monday)"
                            }
                        
                        if has_day and has_dayofweek:
                            return {
                                "type": "error",
                                "message": "You can only specify day of month OR day of week, not both"
                            }
                        
                        if has_day:
                            
                            if not (1 <= config["day"] <= 31):
                                return {
                                    "type": "error",
                                    "message": "Invalid day of the month. Must be between 1 and 31."
                                }
                        
                        if has_dayofweek:                            
                            dayofweek_bitmask = config["dayofweek"]
                            if not isinstance(dayofweek_bitmask, int) or not (1 <= dayofweek_bitmask <= 127):
                                return {
                                    "type": "error",
                                    "message": "Invalid weekday bitmask. Must be between 1 and 127.."
                                }                            
                            
                            if "every" not in config:
                                config["every"] = 1  # First week by default
                            elif not (1 <= config["every"] <= 31): 
                                return {
                                    "type": "error",
                                    "message": "Invalid week occurrence. Use 1=first, 2=second, 3=third, 4=fourth, 5=last, or combinations."
                                }
                        
                        # Validate month bitmask if present
                        if "month" in config:
                            month_bitmask = config["month"]
                            if not isinstance(month_bitmask, int) or not (1 <= month_bitmask <= 4095):
                                return {
                                    "type": "error",
                                    "message": "Invalid month bitmask. Must be between 1 and 4095."
                                }
                        
                        if "start_time" not in config:
                            return {
                                "type": "error",
                                "message": "Missing start_time for monthly maintenance"
                            }
                        if "duration" not in config:
                            return {
                                "type": "error",
                                "message": "Lack of duration for monthly maintenance"
                            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error in the interactive AI parser: {str(e)}")
            return {
                "type": "error",
                "message": f"An unexpected error occurred: {str(e)}. Could you try again?"
            }


# ----- Service initialization -----
zabbix_api = ZabbixAPI(ZABBIX_API_URL, ZABBIX_TOKEN)

def validate_zabbix_user(user_info):
    """Validates that the user is authenticated in Zabbix"""
    if not user_info or not user_info.get('userid'):
        return False
    
    # Verify that the userid exists in Zabbix
    try:
        result = zabbix_api._make_request("user.get", {
            "userids": [user_info['userid']],
            "output": ["userid", "username"]
        })
        return "result" in result and len(result["result"]) > 0
    except:
        return False

# ----- API Endpoints -----
@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint to check service status"""
    zabbix_status = zabbix_api.test_connection()
    zabbix_ok = "result" in zabbix_status and not ("error" in zabbix_status)
    
    return jsonify({
        "status": "healthy" if zabbix_ok else "degraded",
        "timestamp": datetime.datetime.now().isoformat(),
        "zabbix_connected": zabbix_ok,
        "zabbix_version": zabbix_status.get("result", "unknown") if zabbix_ok else "error",
        "ai_provider": loaded_provider or AI_PROVIDER,
        "version": "1.7.0",
        "features": ["interactive_chat", "routine_maintenance", "daily", "weekly", "monthly", "ticket_support", "bitmask_support", "direct_ai_calculation"]
    })

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    """Main endpoint for interactive chat"""
    try:
        data = request.json
        if not data or "message" not in data:
            return jsonify({
                "type": "error",
                "message": "It looks like your message arrived empty. Could you please write your maintenance request?"
            }), 400
            
        user_info = data.get("user_info")
        if not validate_zabbix_user(user_info):
            return jsonify({
                "type": "error",
                "message": "Unauthorized access. You must be logged in to Zabbix."
            }), 401    
        
        user_text = data["message"]
        if user_text is None:
            user_text = ""
        user_text = user_text.strip()
        user_info = data.get("user_info")  
        
        if not user_text:
            return jsonify({
                "type": "error", 
                "message": "I didn't receive any messages. What maintenance do you need to create?"
            }), 400
        
        logger.info(f"Message received: {user_text}")
        if user_info:
            logger.info(f"User: {user_info.get('username', 'unknown')}")
        
        # Analyze the request with AI
        ai_response = AIParser.parse_interactive_request(user_text)
        
        #If it is not a maintenance request, return the AI ​​response directly
        if ai_response.get("type") != "maintenance_request":
            return jsonify(ai_response)
        
        # It's a maintenance request - process with Zabbix
        logger.info("Processing maintenance request...")
        
        # Search for entities by different methods
        found_hosts = []
        found_groups = []
        missing_hosts = []
        missing_groups = []
        
        # 1. Search for specific hosts
        if ai_response.get("hosts"):
            logger.info(f"Searching for hosts: {ai_response['hosts']}")
            
            # Exact search
            hosts_by_name = zabbix_api.get_hosts(ai_response["hosts"])
            found_hosts.extend(hosts_by_name)
            found_host_names = [h["host"] for h in hosts_by_name]
            
            # Flexible search for hosts not found
            missing_host_names = [h for h in ai_response["hosts"] if h not in found_host_names]
            
            for missing_host in missing_host_names:
                flexible_results = zabbix_api.search_hosts(missing_host)
                if flexible_results:
                    found_hosts.extend(flexible_results)
                else:
                    missing_hosts.append(missing_host)
        
        # 2. Search groups
        if ai_response.get("groups"):
            logger.info(f"Looking for groups: {ai_response['groups']}")
            
            # Exact group search
            groups_by_name = zabbix_api.get_hostgroups(ai_response["groups"])
            found_groups.extend(groups_by_name)
            found_group_names = [g["name"] for g in groups_by_name]
            
            # Flexible search for groups not found
            missing_group_names = [g for g in ai_response["groups"] if g not in found_group_names]
            
            for missing_group in missing_group_names:
                flexible_results = zabbix_api.search_hostgroups(missing_group)
                if flexible_results:
                    found_groups.extend(flexible_results)
                else:
                    missing_groups.append(missing_group)
        
        # 3. Search hosts by trigger tags
        hosts_by_tags = []
        if ai_response.get("trigger_tags"):
            logger.info(f"Searching for trigger tags:{ai_response['trigger_tags']}")
            hosts_by_tags = zabbix_api.get_hosts_by_tags(ai_response["trigger_tags"])
            found_hosts.extend(hosts_by_tags)
        
        # Remove duplicates in hosts
        unique_hosts = {h["hostid"]: h for h in found_hosts}.values()
        
        logger.info(f"Result - Hosts: {len(unique_hosts)}, Groups: {len(found_groups)}")
        
        # Build response with additional information
        response_data = {
            **ai_response,
            "found_hosts": list(unique_hosts),
            "found_groups": found_groups,
            "missing_hosts": missing_hosts,
            "missing_groups": missing_groups,
            "original_message": user_text,
            "user_info": user_info, 
            "search_summary": {
                "total_hosts_found": len(unique_hosts),
                "total_groups_found": len(found_groups),
                "hosts_by_tags": len(hosts_by_tags),
                "has_missing": len(missing_hosts) > 0 or len(missing_groups) > 0,
                "is_routine": ai_response.get("recurrence_type", "once") != "once",
                "has_ticket": bool(ai_response.get("ticket_number", "").strip())
            }
        }
        
        # If there are missing resources, update the message to be more informative.
        if missing_hosts or missing_groups:
            missing_info = []
            if missing_hosts:
                missing_info.append(f"hosts: {', '.join(missing_hosts)}")
            if missing_groups:
                missing_info.append(f"Groups: {', '.join(missing_groups)}")
            
            response_data["message"] = f"I've prepared your maintenance, but I didn't find some resources: {'; '.join(missing_info)}.\n\nResources found:\n"
            
            if unique_hosts:
                response_data["message"] += f"Hosts: {', '.join([h['name'] or h['host'] for h in unique_hosts])}\n"
            if found_groups:
                response_data["message"] += f"Grupos: {', '.join([g['name'] for g in found_groups])}\n"
                
            response_data["message"] += "\nDo you want to continue with the resources you found or would you prefer to adjust your request?"
        
        elif not unique_hosts and not found_groups:
            response_data["type"] = "clarification_needed"
            response_data["message"] = "I didn't find any servers or groups with those names.\n\nSuggestions:\n- Check the server names\n- Use exact names as they appear in Zabbix\n- You can use groups instead of individual servers\n\nCould you please check the names and try again?"        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in /chat: {str(e)}")
        return jsonify({
            "type": "error",
            "message": f"An unexpected error occurred: {str(e)}. Could you please try again?"
        }), 500

@app.route("/parse", methods=["POST"])
def parse_request():
    """Legacy endpoint for compatibility - redirects to /chat"""
    return chat_endpoint()

@app.route("/create_maintenance", methods=["POST"])
def create_maintenance():
    """Endpoint to create maintenance periods in Zabbix"""
    try:
        data = request.json
        required_fields = ["start_time", "end_time", "recurrence_type"]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "type": "error",
                    "message": f"Required information is missing: {field}"
                }), 400
        
        user_info = data.get("user_info")
        if not validate_zabbix_user(user_info):
            return jsonify({
                "type": "error",
                "message": "Unauthorized access. You must be logged in to Zabbix.."
            }), 401
            
        # Must have at least hosts or groups
        if not data.get("hosts") and not data.get("groups"):
            return jsonify({
                "type": "error",
                "message": "Specific hosts or groups are required for maintenance"
            }), 400
        
        # Obtain user information
        user_info = data.get("user_info")
        
        # Convert dates to timestamp
        try:
            start_dt = datetime.datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M")
            end_dt = datetime.datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M")
            start_time = int(start_dt.timestamp())
            end_time = int(end_dt.timestamp())
        except ValueError as e:
            return jsonify({
                "type": "error",
                "message": f"Invalid date format: {str(e)}"
            }), 400
        
        # Additional validations
        if end_time <= start_time:
            return jsonify({
                "type": "error",
                "message": "The end date must be after the start date."
            }), 400
        
        # Prepare data for maintenance
        host_ids = []
        group_ids = []
        host_names = []
        group_names = []
        
        # Process specific hosts
        if data.get("hosts"):
            hosts_info = zabbix_api.get_hosts(data["hosts"])
            if hosts_info:
                host_ids = [h["hostid"] for h in hosts_info]
                host_names = [h["name"] for h in hosts_info]
        
        # Process groups
        if data.get("groups"):
            groups_info = zabbix_api.get_hostgroups(data["groups"])
            if groups_info:
                group_ids = [g["groupid"] for g in groups_info]
                group_names = [g["name"] for g in groups_info]
        
        # Verify that valid resources were found
        if not host_ids and not group_ids:
            return jsonify({
                "type": "error",
                "message": "No valid hosts or groups found"
            }), 404
        
        # Generate maintenance name using the new function
        maintenance_name = generate_maintenance_name(data, host_names, group_names)
        
        # Generate description with user information
        description = generate_maintenance_description(data, user_info)
        
        # Prepare recurrence configuration
        recurrence_type = data.get("recurrence_type", "once")
        recurrence_config = data.get("recurrence_config")
        
        # Detailed configuration log
        logger.info(f"Creating maintenance: {maintenance_name}")
        logger.info(f"Recurrence type: {recurrence_type}")
        logger.info(f"Recurrence configuration: {recurrence_config}")

        # Create maintenance in Zabbix
        result = zabbix_api.create_maintenance(
            name=maintenance_name,
            host_ids=host_ids if host_ids else None,
            group_ids=group_ids if group_ids else None,
            start_time=start_time,
            end_time=end_time,
            description=description,
            tags=data.get("trigger_tags"),
            recurrence_type=recurrence_type,
            recurrence_config=recurrence_config
        )
        
        if "error" in result:
            error_msg = result["error"].get("data", str(result["error"]))
            logger.error(f"Zabbix Error: {error_msg}")
            return jsonify({
                "type": "error",
                "message": f"Zabbix Error: {error_msg}"
            }), 400
        
        maintenance_id = None
        if "result" in result and "maintenanceids" in result["result"]:
            maintenance_id = result["result"]["maintenanceids"][0]
            logger.info(f"Maintenance created with ID: {maintenance_id}")
        
        #Build a success message with user information
        success_message = f"Maintenance created successfully!\n\n" 
        success_message += f"Details:\n" 
        success_message += f"• Name: {maintenance_name}\n" 
        success_message += f"• Start: {data['start_time']}\n" 
        success_message += f"• End: {data['end_time']}\n" 
        success_message += f"• Affected hosts: {len(host_ids)}\n" 
        success_message += f"• Groups affected: {len(group_ids)}\n"
        
        if recurrence_type != "once":
            success_message += f"• Type: Routine ({recurrence_type})\n"
            
            # Display specific details of the routine configuration
            if recurrence_config:
                if recurrence_type == "weekly":
                    # Decode bitmask of days
                    days_bitmask = recurrence_config.get("dayofweek", 1)
                    day_names = []
                    if days_bitmask & 1: day_names.append("Monday") 
                    if days_bitmask & 2: day_names.append("Tuesday") 
                    if days_bitmask & 4: day_names.append("Wednesday") 
                    if days_bitmask & 8: day_names.append("Thursday") 
                    if days_bitmask & 16: day_names.append("Friday") 
                    if days_bitmask & 32: day_names.append("Saturday") 
                    if days_bitmask & 64: day_names.append("Sunday")
                    success_message += f"• Days: {', '.join(day_names)}\n"
                    
                elif recurrence_type == "monthly":
                    if "day" in recurrence_config:
                        success_message += f"• Day of the Month: {recurrence_config['day']}\n"
                    elif "dayofweek" in recurrence_config:
                        #Decode day bitmask to monthly
                        days_bitmask = recurrence_config["dayofweek"]
                        day_names = []
                        if days_bitmask & 1: day_names.append("Monday") 
                        if days_bitmask & 2: day_names.append("Tuesday") 
                        if days_bitmask & 4: day_names.append("Wednesday") 
                        if days_bitmask & 8: day_names.append("Thursday") 
                        if days_bitmask & 16: day_names.append("Friday") 
                        if days_bitmask & 32: day_names.append("Saturday") 
                        if days_bitmask & 64: day_names.append("Sunday")
                        
                        # Decode occurrence of the week
                        week_occurrence = recurrence_config.get("every", 1)
                        week_names = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "last"}
                        week_name = week_names.get(week_occurrence, f"Week {week_occurrence}")
                        
                        success_message += f"• Programming: {week_name} Week - {', '.join(day_names)}\n"
                    
                    # Show months if specified
                    if "month" in recurrence_config and recurrence_config["month"] != 4095:
                        month_bitmask = recurrence_config["month"]
                        month_names = []
                        if month_bitmask & 1: month_names.append("January") 
                        if month_bitmask & 2: month_names.append("February") 
                        if month_bitmask & 4: month_names.append("March") 
                        if month_bitmask & 8: month_names.append("April") 
                        if month_bitmask & 16: month_names.append("May") 
                        if month_bitmask & 32: month_names.append("June") 
                        if month_bitmask & 64: month_names.append("July") 
                        if month_bitmask & 128: month_names.append("August") 
                        if month_bitmask & 256: month_names.append("September") 
                        if month_bitmask & 512: month_names.append("October") 
                        if month_bitmask & 1024: month_names.append("November") 
                        if month_bitmask & 2048: month_names.append("December")
                        success_message += f"• Months: {', '.join(month_names)}\n"
        
        ticket_number = data.get("ticket_number", "").strip()
        if ticket_number:
            success_message += f"• Ticket: {ticket_number}\n"
        
        # Show user if available
        if user_info:
            user_display = ""
            if user_info.get("name") or user_info.get("surname"):
                user_display = " ".join(filter(None, [user_info.get("name"), user_info.get("surname")]))
            if not user_display:
                user_display = user_info.get("username", "Unknown user")
            success_message += f"• Requested By: {user_display}\n"
        
        success_message += f"\nThe maintenance is up and running."
        
        return jsonify({
            "type": "maintenance_created",
            "success": True,
            "maintenance_id": maintenance_id,
            "hosts_affected": len(host_ids),
            "groups_affected": len(group_ids),
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "name": maintenance_name,
            "description": description,
            "recurrence_type": recurrence_type,
            "is_routine": recurrence_type != "once",
            "ticket_number": ticket_number,
            "user_info": user_info,
            "message": success_message
        })
        
    except Exception as e:
        logger.error(f"Error in /create_maintenance: {str(e)}")
        return jsonify({
            "type": "error",
            "message": f"Internal error: {str(e)}"
        }), 500

# Rest of endpoints...
@app.route("/search_hosts", methods=["POST"])
def search_hosts():
    """Endpoint to search for hosts by term"""
    try:
        data = request.json
        if not data or "search" not in data:
            return jsonify({
                "type": "error",
                "message": "The 'search' field is required"
            }), 400
        
        search_term = data["search"].strip()
        if not search_term:
            return jsonify({
                "type": "error",
                "message": "The search term cannot be empty"
            }), 400
        
        logger.info(f"Searching for hosts with the term: {search_term}")
        
        hosts = zabbix_api.search_hosts(search_term)
        
        return jsonify({
            "type": "search_results",
            "search_term": search_term,
            "hosts_found": len(hosts),
            "hosts": hosts,
            "message": f"I found {len(hosts)} host(s) that match '{search_term}'"
        })
        
    except Exception as e:
        logger.error(f"Error in /search_hosts: {str(e)}")
        return jsonify({
            "type": "error",
            "message": f"Internal Error: {str(e)}"
        }), 500

@app.route("/search_groups", methods=["POST"])
def search_groups():
    """Endpoint to search for groups by term"""
    try:
        data = request.json
        if not data or "search" not in data:
            return jsonify({
                "type": "error",
                "message": "The 'search' field is required"
            }), 400
        
        search_term = data["search"].strip()
        if not search_term:
            return jsonify({
                "type": "error",
                "message": "The search term cannot be empty"
            }), 400
        
        logger.info(f"Searching for groups with term: {search_term}")
        
        groups = zabbix_api.search_hostgroups(search_term)
        
        return jsonify({
            "type": "search_results",
            "search_term": search_term,
            "groups_found": len(groups),
            "groups": groups,
            "message": f"I found {len(groups)} group(s) that match '{search_term}'"
        })
        
    except Exception as e:
        logger.error(f"Error in /search_groups: {str(e)}")
        return jsonify({
            "type": "error",
            "message": f"Internal Error: {str(e)}"
        }), 500

@app.route("/maintenance/list", methods=["GET"])
def list_maintenances():
    """Endpoint to list existing maintenance"""
    try:
        params = {
            "output": ["maintenanceid", "name", "active_since", "active_till", "description", "maintenance_type"],
            "selectHosts": ["hostid", "host", "name"],
            "selectGroups": ["groupid", "name"],
            "selectTags": ["tag", "value"],
            "selectTimeperiods": ["timeperiod_type", "start_time", "period", "every", "dayofweek", "day", "month"],
            "sortfield": "active_since",
            "sortorder": "DESC",
            "limit": 50
        }
        result = zabbix_api._make_request("maintenance.get", params)
        
        if "error" in result:
            return jsonify({
                "type": "error",
                "message": f"Error getting maintenance: {result['error']}"
            }), 400
        
        maintenances = result.get("result", [])
        for maint in maintenances:
            maint["active_since"] = datetime.datetime.fromtimestamp(int(maint["active_since"])).strftime("%Y-%m-%d %H:%M")
            maint["active_till"] = datetime.datetime.fromtimestamp(int(maint["active_till"])).strftime("%Y-%m-%d %H:%M")
            
            #Determine if it is routine based on time periods
            is_routine = False
            routine_type = "once"
            if maint.get("timeperiods"):
                timeperiod = maint["timeperiods"][0]
                tp_type = int(timeperiod.get("timeperiod_type", 0))
                if tp_type == 2:
                    routine_type = "daily"
                    is_routine = True
                elif tp_type == 3:
                    routine_type = "weekly"
                    is_routine = True
                elif tp_type == 4:
                    routine_type = "monthly"
                    is_routine = True
            
            maint["is_routine"] = is_routine
            maint["routine_type"] = routine_type
            
            #Extract ticket number from name or description
            ticket_match = re.search(r'\b\d{3}-\d{3,6}\b', maint.get("name", "") + " " + maint.get("description", ""))
            maint["ticket_number"] = ticket_match.group(0) if ticket_match else ""
        
        return jsonify({
            "type": "maintenance_list",
            "maintenances": maintenances,
            "total": len(maintenances),
            "message": f"Showing {len(maintenances)} most recent maintenance(s)"
        })
        
    except Exception as e:
        logger.error(f"Error in /maintenance/list: {str(e)}")
        return jsonify({
            "type": "error",
            "message": f"Internal Error: {str(e)}"
        }), 500

@app.route("/maintenance/templates", methods=["GET"])
def get_maintenance_templates():
    """Endpoint for routine maintenance templates"""
    templates = {
        "daily": {
            "name": "Daily Maintenance",
            "description": "Maintenance that runs every day",
            "examples": [
                "Daily backup at 2 AM for 2 hours with ticket 100-178306",
                "Daily log cleanup at 11:00 PM with ticket 200-8341",
                "Daily service restart from 3-4 AM with ticket 500-43116"
            ]
        },
        "weekly": {
           "name": "Weekly Maintenance",
            "description": "Maintenance that runs weekly",
            "examples": [
                "Weekly maintenance Sundays 1-3 AM ticket 100-178306",
                "DB update every Friday at 10 PM ticket 200-8341",
                "Full backup every Saturday ticket 500-43116"
            ]
        },
        "monthly": {
            "name":"Monthly Maintenance",
            "description": "Maintenance that runs monthly",
            "examples": [
                "Maintenance on the first day of each month with ticket 100-178306",
                "DB Optimization on the 15th of each month with ticket 200-8341",
                "Deep cleaning on the first Sunday of the month with ticket 500-43116"
            ]
        }
    }
    
    return jsonify({
        "type": "templates",
        "templates": templates,
        "message": "Here are the templates available for routine maintenance."
    })

@app.route("/examples", methods=["GET"])
def get_examples():
    """Endpoint for usage examples"""
    examples = {
        "basic": [
            {
                "title": "Simple Maintenance",
                "description": "A specific server for a limited time",
                "example": "Maintenance for srv-web01 tomorrow from 8 to 10 with ticket 100-178306"
            },
            {
                "title": "Multiple Maintenance",
                "description": "Multiple servers at the same time",
                "example": "Put srv-web01, srv-web02, and srv-web03 under maintenance today from 2:00 PM to 4:00 PM"
            }
        ],
        "groups": [
            {
                "title": "Group Maintenance",
                "description": "An entire server group",
                "example": "Database group maintenance on Sunday from 2 to 4 AM, ticket 200-8341"
            },
            {
                "title": "Multiple Groups",
                "description": "Several groups at once",
                "example": "Maintenance for web server and app server groups tomorrow from 1 to 3 AM"
            }
        ],
        "routine": [
            {
                "title": "Daily Backup",
                "description": "Maintenance that runs every day",
                "example": "Daily backup for srv-backup from 2 to 4 AM during January with ticket 500-43116"
            },
            {
                "title": "Weekly Maintenance",
                "description": "Maintenance that runs every week",
                "example": "Weekly maintenance on Sundays for the database group from 1 to 3 AM"
            },
            {
                "title": "Monthly Daily Maintenance",
                "description": "Maintenance that runs on a specific day each month",
                "example": "Monthly cleanup on the 5th of each month for all web servers"
            },
            {
                "title": "Monthly Weekday Maintenance",
                "description": "Maintenance that runs on a specific weekday each month",
                "example": "Update the first Sunday of each month for the group database"
            }
        ]
    }
    
    return jsonify({
        "type": "examples",
        "examples": examples,
        "message": "Here are some examples of how to request maintenance"
    })

# Eendpoint for testing routine configurations
@app.route("/test/routine", methods=["POST"])
def test_routine_configuration():
    """Endpoint for testing routine maintenance configurations"""
    try:
        data = request.json
        if not data:
            return jsonify({
                "type": "error",
                "message": "Test data is required"
            }), 400
        
        recurrence_type = data.get("recurrence_type", "once")
        recurrence_config = data.get("recurrence_config", {})
        
        #Validate configuration according to type
        result = {"type": "test_result", "valid": True, "details": []}
        
        try:
            if recurrence_type == "weekly":
                dayofweek = recurrence_config.get("dayofweek", 1)
                # Decode bitmask
                day_names = []
                if dayofweek & 1: day_names.append("Monday") 
                if dayofweek & 2: day_names.append("Tuesday") 
                if dayofweek & 4: day_names.append("Wednesday") 
                if dayofweek & 8: day_names.append("Thursday") 
                if dayofweek & 16: day_names.append("Friday") 
                if dayofweek & 32: day_names.append("Saturday") 
                if dayofweek & 64: day_names.append("Sunday")
                result["details"].append(f"Days {', '.join(day_names)} (bitmask: {dayofweek})")
                
            elif recurrence_type == "monthly":
                if "day" in recurrence_config:
                    day = recurrence_config["day"]
                    result["details"].append(f"Day of the month: {day}")
                elif "dayofweek" in recurrence_config:
                    dayofweek = recurrence_config["dayofweek"]
                    week_occurrence = recurrence_config.get("every", 1)
                    
                    # Decode bitmask of days
                    day_names = []
                    if dayofweek & 1: day_names.append("Monday") 
                    if dayofweek & 2: day_names.append("Tuesday") 
                    if dayofweek & 4: day_names.append("Wednesday") 
                    if dayofweek & 8: day_names.append("Thursday") 
                    if dayofweek & 16: day_names.append("Friday") 
                    if dayofweek & 32: day_names.append("Saturday") 
                    if dayofweek & 64: day_names.append("Sunday")
                    
                    weeks = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "last"}
                    week_name = weeks.get(week_occurrence, f"Week {week_occurrence}")
                    
                    result["details"].extend([
                        f"Days: {', '.join(day_names)} (bitmask: {dayofweek})",
                        f"week: {week_name} (valor: {week_occurrence})"
                    ])
                
                # Decode months if present
                if "month" in recurrence_config:
                    month_bitmask = recurrence_config["month"]
                    month_names = []
                    if month_bitmask & 1: month_names.append("January") 
                    if month_bitmask & 2: month_names.append("February") 
                    if month_bitmask & 4: month_names.append("March") 
                    if month_bitmask & 8: month_names.append("April") 
                    if month_bitmask & 16: month_names.append("May") 
                    if month_bitmask & 32: month_names.append("June") 
                    if month_bitmask & 64: month_names.append("July") 
                    if month_bitmask & 128: month_names.append("August") 
                    if month_bitmask & 256: month_names.append("September") 
                    if month_bitmask & 512: month_names.append("October") 
                    if month_bitmask & 1024: month_names.append("November") 
                    if month_bitmask & 2048: month_names.append("December")
                    result["details"].append(f"Months: {', '.join(month_names)} (bitmask: {month_bitmask})")
            
            # Validate start time
            if "start_time" in recurrence_config:
                start_seconds = recurrence_config["start_time"]
                hours = start_seconds // 3600
                minutes = (start_seconds % 3600) // 60
                result["details"].append(f"Start time: {hours:02d}:{minutes:02d} ({start_seconds}s)")
            
            #Validate duration
            if "duration" in recurrence_config:
                duration_seconds = recurrence_config["duration"]
                hours = duration_seconds // 3600
                minutes = (duration_seconds % 3600) // 60
                result["details"].append(f"Duration: {hours}h {minutes}m ({duration_seconds}s)")
            
            result["message"] = f"Valid {recurrence_type} configuration"
            
        except ValueError as e:
            result["valid"] = False
            result["message"] = f"Configuration error: {str(e)}"
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in /test/routine: {str(e)}")
        return jsonify({
            "type": "error",
            "message": f"Internal Error: {str(e)}"
        }), 500

# ----- Inicio de la aplicación -----
if __name__ == "__main__":
    print("\nInteractive AI Maintenance Assistant for Zabbix 7.2") 
    print("==============================================================") 
    print(f"Zabbix API: {ZABBIX_API_URL}") 
    print(f"Token: {'Configured' if ZABBIX_TOKEN else 'Not configured'}") 
    print(f"IA Provider: {loaded_provider or 'Not available'}") 

    if loaded_provider == "openai": 
        print(f" - Model: {OPENAI_MODEL}") 
    elif loaded_provider == "gemini": 
        print(f" - Model: {GEMINI_MODEL}")
    
    # Connection test at startup
    test_result = zabbix_api.test_connection()
    if "result" in test_result:
        print(f"Zabbix Connection OK - Users Found: {len(test_result['result'])}")
    else:
        print(f"Zabbix connection error: {test_result.get('error', 'Unknown')}")
    
    print("Interactive Chat Endpoints:")
    print(f" - POST /chat (Main endpoint - conversational)")
    print(f" - POST /create_maintenance (Create maintenance)")
    print(f" - GET /examples (Get usage examples)")

    print("API Endpoints:")
    print(f" - POST /search_hosts (Search hosts)")
    print(f" - POST /search_groups (Search groups)")
    print(f" - GET /maintenance/list (List maintenance)")
    print(f" - GET /maintenance/templates (Routine templates)")
    print(f" - POST /test/routine (Test routine configurations)")
    print(f" - GET /health (Check status)")

    print("Interaction Types:")
    print(f" - Maintenance Requests")
    print(f" - Help requests and examples")
    print(f" - System questions")
    print(f" - Redirection for unrelated inquiries")

    print("\nSupported maintenance types:")
    print(f" - One-time (eleven)")
    print(f" - Daily (daily)")
    print(f" - Weekly (weekly) - with bitmask for days")
    print(f" - Monthly (monthly) - specific day or weekday")

    print("\nTicket support:")
    print(f" - Format: XXX-XXXXXX (e.g.: 100-178306)")
    print(f" - Automatic detection in text")
    print(f" - Custom names per ticket")

    print("\nRoutine maintenance improvements:")
    print(f" - Correct bitmasks for weekdays")
    print(f" - Monthly support for a specific day (day 5)")
    print(f" - Monthly support by weekday (first Sunday)")
    print(f" - Improved configuration validation")
    print(f" - Detailed logs for debugging")
    print(f" - Direct AI bitmask calculation")

    print("\nInteractive AI functions:")
    print(f" - Natural and friendly conversation")
    print(f" - Automatic examples upon request")
    print(f" - Polite redirection for unrelated queries")
    print(f" - Intelligent clarification of incomplete requests")
    print(f" - Advanced validation of routine configurations")
    print(f" - Automatic calculation of complex bitmasks")
    
    app.run(host="0.0.0.0", port=5005, debug=False)

