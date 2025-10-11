"""
Intelligent Router pro hybridní AI asistenta
5-fázová kaskádová logika pro optimální routing
"""

import re
import structlog
from typing import Tuple, Dict, Any
from enum import Enum

logger = structlog.get_logger()


class RoutingDecision(Enum):
    FORCE_LOCAL = "force_local"
    FORCE_CLOUD = "force_cloud"
    USE_LOCAL = "use_local"
    USE_CLOUD = "use_cloud"
    ASK_CLARIFICATION = "ask_clarification"


class IntentCategory(Enum):
    SIMPLE_COMMAND = "simple_command"
    COMPLEX_GENERATIVE = "complex_generative"
    UNCERTAIN = "uncertain"


class IntelligentRouter:
    """
    Inteligentní router implementující 5-fázovou kaskádu:
    1. Bezpečnostní kontrola (PII detection)
    2. Uživatelská preference
    3. Intent klasifikace
    4. ASR confidence rozhodnutí
    5. Fallback eskalace
    """
    
    def __init__(self, user_preference: str = None):
        """
        Args:
            user_preference: 'local_only', 'cloud_only', nebo None (auto)
        """
        self.user_preference = user_preference
        
        # Fáze 1: PII patterns
        self.pii_patterns = {
            'rodne_cislo': r'\b\d{6}/\d{3,4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(\+420)?\s?\d{3}\s?\d{3}\s?\d{3}\b'
        }
        
        # Fáze 3: Intent keywords
        self.simple_keywords = [
            'zapni', 'vypni', 'nastav', 'spusť', 'zastaviť',
            'čas', 'počasí', 'alarm', 'kde je', 'kolik je',
            'otevři', 'zavři', 'zhasni', 'rozsvit'
        ]
        
        self.complex_keywords = [
            'vysvětli', 'napiš', 'vymysli', 'analyzuj', 'porovnej',
            'sumarizuj', 'shrň', 'recept', 'jak funguje', 'co znamená',
            'proč', 'jaký je rozdíl', 'vytvoř', 'doporuč'
        ]
        
        logger.info("intelligent_router_initialized", preference=user_preference)
    
    
    def route(self, text: str, asr_confidence: float = 1.0, 
              session_context_length: int = 0) -> Tuple[RoutingDecision, Dict[str, Any]]:
        """
        Hlavní routovací logika - 5-fázová kaskáda
        
        Args:
            text: Přepsaný text z STT
            asr_confidence: Confidence score z ASR (0-1)
            session_context_length: Délka konverzace v tokenech
            
        Returns:
            (decision, metadata) - routing decision a metadata
        """
        metadata = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'asr_confidence': asr_confidence,
            'session_context': session_context_length
        }
        
        # FÁZE 1: Bezpečnostní kontrola (0-20ms)
        decision, reason = self._phase1_privacy_check(text)
        if decision:
            metadata['phase'] = 1
            metadata['reason'] = reason
            logger.info("router_decision", decision=decision.value, phase=1, reason=reason)
            return decision, metadata
        
        # FÁZE 2: Uživatelská preference (20-25ms)
        decision, reason = self._phase2_user_preference()
        if decision:
            metadata['phase'] = 2
            metadata['reason'] = reason
            logger.info("router_decision", decision=decision.value, phase=2, reason=reason)
            return decision, metadata
        
        # FÁZE 3: Intent klasifikace (25-55ms)
        intent, confidence = self._phase3_intent_classification(text)
        metadata['intent'] = intent.value
        metadata['intent_confidence'] = confidence
        
        if intent == IntentCategory.SIMPLE_COMMAND and confidence > 0.85:
            metadata['phase'] = 3
            metadata['reason'] = 'simple_command_high_confidence'
            logger.info("router_decision", decision="use_local", phase=3, 
                       intent=intent.value, confidence=confidence)
            return RoutingDecision.USE_LOCAL, metadata
        
        if intent == IntentCategory.COMPLEX_GENERATIVE and confidence > 0.80:
            metadata['phase'] = 3
            metadata['reason'] = 'complex_task_high_confidence'
            logger.info("router_decision", decision="use_cloud", phase=3,
                       intent=intent.value, confidence=confidence)
            return RoutingDecision.USE_CLOUD, metadata
        
        # FÁZE 4: ASR confidence rozhodnutí (55-70ms)
        decision, reason = self._phase4_asr_confidence(asr_confidence, intent)
        metadata['phase'] = 4
        metadata['reason'] = reason
        logger.info("router_decision", decision=decision.value, phase=4,
                   asr_confidence=asr_confidence, reason=reason)
        return decision, metadata
    
    
    def _phase1_privacy_check(self, text: str) -> Tuple[RoutingDecision, str]:
        """
        Fáze 1: Detekce PII (osobních údajů)
        Pokud najde citlivá data → FORCE_LOCAL
        """
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text):
                logger.warning("pii_detected", type=pii_type)
                return RoutingDecision.FORCE_LOCAL, f"pii_detected_{pii_type}"
        
        # Kontrola citlivých slov
        sensitive_words = ['heslo', 'pin', 'kód', 'číslo karty', 'rodné číslo', 'účet']
        text_lower = text.lower()
        for word in sensitive_words:
            if word in text_lower:
                logger.warning("sensitive_keyword_detected", keyword=word)
                return RoutingDecision.FORCE_LOCAL, f"sensitive_keyword_{word}"
        
        return None, None
    
    
    def _phase2_user_preference(self) -> Tuple[RoutingDecision, str]:
        """
        Fáze 2: Explicitní uživatelská preference
        """
        if self.user_preference == 'local_only':
            return RoutingDecision.FORCE_LOCAL, "user_preference_local"
        elif self.user_preference == 'cloud_only':
            return RoutingDecision.FORCE_CLOUD, "user_preference_cloud"
        
        return None, None
    
    
    def _phase3_intent_classification(self, text: str) -> Tuple[IntentCategory, float]:
        """
        Fáze 3: Klasifikace intentu (záměru)
        Returns: (category, confidence_score)
        """
        text_lower = text.lower()
        words = text_lower.split()
        word_count = len(words)
        
        # Heuristiky pro intent
        simple_score = 0.0
        complex_score = 0.0
        
        # 1. Délka textu (krátké = pravděpodobně jednoduché)
        if word_count <= 4:
            simple_score += 0.3
        elif word_count >= 10:
            complex_score += 0.3
        
        # 2. Klíčová slova
        for keyword in self.simple_keywords:
            if keyword in text_lower:
                simple_score += 0.4
                break
        
        for keyword in self.complex_keywords:
            if keyword in text_lower:
                complex_score += 0.5
                break
        
        # 3. Syntaktické znaky
        if '?' in text and word_count > 6:
            complex_score += 0.2
        
        if text.startswith(('zapni', 'vypni', 'nastav', 'spusť')):
            simple_score += 0.3
        
        # 4. Počet vět (více vět = složitější)
        sentence_count = text.count('.') + text.count('?') + text.count('!')
        if sentence_count > 1:
            complex_score += 0.2
        
        # Rozhodnutí
        if simple_score > complex_score:
            confidence = min(0.95, 0.5 + simple_score)
            return IntentCategory.SIMPLE_COMMAND, confidence
        elif complex_score > simple_score:
            confidence = min(0.95, 0.5 + complex_score)
            return IntentCategory.COMPLEX_GENERATIVE, confidence
        else:
            return IntentCategory.UNCERTAIN, 0.5
    
    
    def _phase4_asr_confidence(self, asr_confidence: float, 
                                intent: IntentCategory) -> Tuple[RoutingDecision, str]:
        """
        Fáze 4: Rozhodnutí podle ASR confidence
        Threshold 0.75 vychází z výzkumu
        """
        if asr_confidence >= 0.75:
            # Přepis je spolehlivý
            if intent == IntentCategory.SIMPLE_COMMAND:
                return RoutingDecision.USE_LOCAL, "high_asr_confidence_simple"
            else:
                return RoutingDecision.USE_CLOUD, "high_asr_confidence_complex"
        else:
            # Nízká ASR confidence
            if asr_confidence < 0.5:
                return RoutingDecision.ASK_CLARIFICATION, "low_asr_confidence"
            else:
                # Střední confidence → cloud má lepší ASR korekci
                return RoutingDecision.USE_CLOUD, "medium_asr_confidence_use_cloud"
    
    
    def should_escalate_to_cloud(self, local_response: str, query: str) -> bool:
        """
        Fáze 5: Fallback eskalace
        Vyhodnotí kvalitu lokální odpovědi
        """
        # Detekce placeholder odpovědí
        placeholder_phrases = [
            'nevím', 'nenašel jsem', 'nerozumím', 
            'nedokážu', 'nemohu', 'pracuji na implementaci',
            'placeholder'
        ]
        
        response_lower = local_response.lower()
        for phrase in placeholder_phrases:
            if phrase in response_lower:
                logger.info("escalating_to_cloud", reason=f"placeholder_{phrase}")
                return True
        
        # Odpověď je příliš krátká pro složitý dotaz
        query_words = len(query.split())
        response_words = len(local_response.split())
        
        if query_words >= 8 and response_words < 10:
            logger.info("escalating_to_cloud", reason="response_too_short")
            return True
        
        return False
