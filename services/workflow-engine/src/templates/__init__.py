"""
Workflow Templates

Pre-defined workflow templates for common use cases
"""

from .media_processing import (
    MEDIA_INGEST_WORKFLOW,
    MEDIA_QC_WORKFLOW,
    BATCH_TRANSCODE_WORKFLOW
)

from .content_management import (
    CONTENT_PUBLISHING_WORKFLOW,
    ARCHIVE_MANAGEMENT_WORKFLOW,
    CONTENT_REVIEW_WORKFLOW
)

# All available templates
WORKFLOW_TEMPLATES = [
    MEDIA_INGEST_WORKFLOW,
    MEDIA_QC_WORKFLOW,
    BATCH_TRANSCODE_WORKFLOW,
    CONTENT_PUBLISHING_WORKFLOW,
    ARCHIVE_MANAGEMENT_WORKFLOW,
    CONTENT_REVIEW_WORKFLOW
]

# Template registry by ID
TEMPLATE_REGISTRY = {
    template["template_id"]: template
    for template in WORKFLOW_TEMPLATES
}

# Templates by category
TEMPLATES_BY_CATEGORY = {}
for template in WORKFLOW_TEMPLATES:
    category = template["category"]
    if category not in TEMPLATES_BY_CATEGORY:
        TEMPLATES_BY_CATEGORY[category] = []
    TEMPLATES_BY_CATEGORY[category].append(template)

__all__ = [
    "WORKFLOW_TEMPLATES",
    "TEMPLATE_REGISTRY",
    "TEMPLATES_BY_CATEGORY",
    "MEDIA_INGEST_WORKFLOW",
    "MEDIA_QC_WORKFLOW",
    "BATCH_TRANSCODE_WORKFLOW",
    "CONTENT_PUBLISHING_WORKFLOW",
    "ARCHIVE_MANAGEMENT_WORKFLOW",
    "CONTENT_REVIEW_WORKFLOW"
]