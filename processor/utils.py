from datetime import datetime
from settings import ALERT_INTERVAL

cooldowns = {}


def can_alert(person_id: str) -> bool:
    now = datetime.now()
    last = cooldowns.get(person_id)
    if last is None or now - last > ALERT_INTERVAL:
        cooldowns[person_id] = now
        return True
    return False
