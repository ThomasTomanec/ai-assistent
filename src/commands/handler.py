"""Command processing and business logic"""
import structlog
from datetime import datetime

logger = structlog.get_logger()


class CommandHandler:
    """Handles command processing and responses"""
    
    def __init__(self):
        self.commands = self._initialize_commands()
        logger.info("command_handler_initialized")
    
    def _initialize_commands(self) -> dict:
        """Initialize command mappings"""
        return {
            "greeting": {
                "keywords": ["ahoj", "hello", "hi", "nazdar", "čau"],
                "handler": self._handle_greeting
            },
            "wellbeing": {
                "keywords": ["jak se máš", "how are you", "co děláš"],
                "handler": self._handle_wellbeing
            },
            "thanks": {
                "keywords": ["děkuji", "díky", "děkuju", "thanks", "thank you"],
                "handler": self._handle_thanks
            },
            "goodbye": {
                "keywords": ["nashle", "sbohem", "čau čau", "bye", "goodbye"],
                "handler": self._handle_goodbye
            },
            "time": {
                "keywords": ["kolik je hodin", "který je čas", "what time", "time is"],
                "handler": self._handle_time
            },
            "date": {
                "keywords": ["jaký je datum", "kolikátého je", "what date", "what day"],
                "handler": self._handle_date
            },
            "light_on": {
                "keywords": ["zapni světlo", "rozsviť"],
                "handler": self._handle_light_on
            },
            "light_off": {
                "keywords": ["zhasni světlo", "vypni světlo"],
                "handler": self._handle_light_off
            },
            "light_dim": {
                "keywords": ["ztlum světlo"],
                "handler": self._handle_light_dim
            },
            "weather": {
                "keywords": ["počasí", "weather"],
                "handler": self._handle_weather
            },
            "help": {
                "keywords": ["pomoc", "help", "co umíš"],
                "handler": self._handle_help
            }
        }
    
    def process(self, text: str) -> str:
        """
        Process command and return response
        
        Args:
            text: User command text
            
        Returns:
            Response text
        """
        text_lower = text.lower().strip()
        
        if not text_lower:
            return "Neřekl jsi nic."
        
        logger.info("processing_command", text=text[:50])
        
        # Find matching command
        for command_name, command_data in self.commands.items():
            if any(keyword in text_lower for keyword in command_data["keywords"]):
                logger.debug("command_matched", command=command_name)
                return command_data["handler"](text_lower)
        
        # No match - fallback
        logger.debug("command_not_matched", text=text[:50])
        return self._handle_unknown(text_lower)
    
    # ============================================
    # COMMAND HANDLERS
    # ============================================
    
    def _handle_greeting(self, text: str) -> str:
        return "Ahoj! Jak ti můžu pomoci?"
    
    def _handle_wellbeing(self, text: str) -> str:
        return "Mám se dobře, děkuji! Jsem tu pro tebe."
    
    def _handle_thanks(self, text: str) -> str:
        return "Rádo se stalo!"
    
    def _handle_goodbye(self, text: str) -> str:
        return "Nashledanou! Měj se hezky."
    
    def _handle_time(self, text: str) -> str:
        now = datetime.now()
        return f"Je {now.hour} hodin a {now.minute} minut."
    
    def _handle_date(self, text: str) -> str:
        now = datetime.now()
        days_cs = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
        months_cs = ["ledna", "února", "března", "dubna", "května", "června",
                    "července", "srpna", "září", "října", "listopadu", "prosince"]
        day_name = days_cs[now.weekday()]
        month_name = months_cs[now.month - 1]
        return f"Dnes je {day_name}, {now.day}. {month_name} {now.year}."
    
    def _handle_light_on(self, text: str) -> str:
        # TODO: Later integrate with actual device control
        room = self._extract_room(text)
        if room:
            return f"Zapínám světlo v {room}."
        return "Zapínám světlo."
    
    def _handle_light_off(self, text: str) -> str:
        room = self._extract_room(text)
        if room:
            return f"Zhasínám světlo v {room}."
        return "Zhasínám světlo."
    
    def _handle_light_dim(self, text: str) -> str:
        return "Ztlumuju světlo na 50 procent."
    
    def _handle_weather(self, text: str) -> str:
        # TODO: Later integrate with weather API
        return "Venku je asi 15°C a polojasno. (simulace - později přidám skutečná data)"
    
    def _handle_help(self, text: str) -> str:
        return ("Umím:\n"
                "• Pozdravit a povídat si\n"
                "• Říct čas a datum\n"
                "• Zapínat/zhasínat světla\n"
                "• Počasí (zatím simulace)\n"
                "Jsem v testovací fázi!")
    
    def _handle_unknown(self, text: str) -> str:
        return "Rozumím. Zatím to neumím. Zkus říct 'pomoc' pro seznam příkazů."
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _extract_room(self, text: str) -> str | None:
        """Extract room name from command"""
        rooms = {
            "obývák": ["obývák", "obyvak", "living room"],
            "ložnice": ["ložnice", "loznice", "bedroom"],
            "kuchyně": ["kuchyně", "kuchyne", "kuchyň", "kitchen"],
            "koupelna": ["koupelna", "bathroom"]
        }
        
        for room_name, keywords in rooms.items():
            if any(keyword in text for keyword in keywords):
                return room_name
        
        return None
