"""
Klasifikace příkazů - jednoduchý vs složitý
"""

def is_simple_prompt(text: str) -> bool:
    """
    Rozhodne, zda je dotaz jednoduchý (pro lokální AI) nebo složitý (pro cloud AI).
    
    Kritéria:
    - Délka věty (počet slov)
    - Můžeš přidat další kritéria (entitní analýza, syntax, klíčová slova atd.)
    
    Args:
        text: Text příkazu od uživatele
    
    Returns:
        True pokud je jednoduchý, False pokud složitý
    """
    words = text.strip().split()
    
    # Jednoduché kritérium: méně než 8 slov = jednoduchý
    if len(words) <= 8:
        return True
    
    return False
