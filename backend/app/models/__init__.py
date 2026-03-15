"""Models package — import all models so Alembic can discover them."""

from app.models.user import User  # noqa: F401
from app.models.source import Source  # noqa: F401
from app.models.raw_item import RawItem  # noqa: F401
from app.models.canonical_item import CanonicalItem, CanonicalSource  # noqa: F401
from app.models.duplicate_group import DuplicateGroup, DuplicateGroupItem  # noqa: F401
from app.models.publish_record import PublishRecord  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.setting import Setting  # noqa: F401
from app.models.filter_rule import FilterRule  # noqa: F401
