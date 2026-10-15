"""Evidence-traceable research core for mobile game market analysis."""

from .db import Database
from .repository import ResearchRepository
from .service import ResearchService

__all__ = ["Database", "ResearchRepository", "ResearchService"]
