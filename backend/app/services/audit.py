import json
from ..models import AuditLog

def audit(db, user_id, action, entity_type, entity_id=None, details=None):
    db.add(AuditLog(actor_user_id=user_id, action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id else None, details_json=json.dumps(details or {}, default=str)))
    db.commit()
