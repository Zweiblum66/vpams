"""
Content Management Workflow Templates
"""

from ..models.schemas import (
    TaskType, TriggerType, WorkflowPriority,
    ConditionOperator
)

# Content Publishing Workflow
CONTENT_PUBLISHING_WORKFLOW = {
    "template_id": "content-publishing",
    "name": "Content Publishing Pipeline",
    "description": "Publish content to multiple destinations with validation and approval",
    "category": "content-management",
    "tags": ["publishing", "content", "distribution"],
    "is_public": True,
    "definition": {
        "triggers": [
            {
                "trigger_id": "publish-request",
                "trigger_type": TriggerType.MANUAL.value
            }
        ],
        "variables": {
            "destinations": ["website", "social-media", "archive"],
            "require_legal_review": True,
            "watermark_enabled": True
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset to publish"
                },
                "destinations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target destinations"
                },
                "embargo_date": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Optional embargo date"
                }
            },
            "required": ["asset_id", "destinations"]
        },
        "tasks": [
            {
                "task_id": "validate-metadata",
                "task_type": TaskType.SCRIPT_EXECUTION.value,
                "name": "Validate Required Metadata",
                "parameters": {
                    "script": "validate_metadata.py",
                    "language": "python",
                    "args": {
                        "asset_id": "$input.asset_id",
                        "required_fields": ["title", "description", "rights", "creator"]
                    }
                }
            },
            {
                "task_id": "check-rights",
                "task_type": TaskType.API_CALL.value,
                "name": "Check Rights Management",
                "parameters": {
                    "url": "${RIGHTS_SERVICE_URL}/api/v1/check",
                    "method": "POST",
                    "body": {
                        "asset_id": "$input.asset_id",
                        "usage": "publishing",
                        "destinations": "$input.destinations"
                    }
                }
            },
            {
                "task_id": "legal-review",
                "task_type": "conditional",
                "name": "Legal Review Required?",
                "conditions": [
                    {
                        "field": "$variables.require_legal_review",
                        "operator": ConditionOperator.EQUALS.value,
                        "value": True
                    }
                ],
                "then_tasks": [
                    {
                        "task_id": "request-legal-approval",
                        "task_type": TaskType.APPROVAL.value,
                        "name": "Request Legal Approval",
                        "parameters": {
                            "approvers": ["legal-team"],
                            "message": "Please review this content for legal compliance",
                            "timeout": 172800  # 48 hours
                        }
                    }
                ],
                "else_tasks": []
            },
            {
                "task_id": "prepare-versions",
                "task_type": "parallel",
                "name": "Prepare Platform-Specific Versions",
                "tasks": [
                    {
                        "task_id": "web-version",
                        "task_type": TaskType.TRANSCODE.value,
                        "name": "Create Web Version",
                        "parameters": {
                            "asset_id": "$input.asset_id",
                            "profile": "web-streaming",
                            "settings": {
                                "watermark": "$variables.watermark_enabled"
                            }
                        }
                    },
                    {
                        "task_id": "social-version",
                        "task_type": TaskType.TRANSCODE.value,
                        "name": "Create Social Media Version",
                        "parameters": {
                            "asset_id": "$input.asset_id",
                            "profile": "social-media",
                            "settings": {
                                "aspect_ratio": "1:1",
                                "duration_limit": 60
                            }
                        }
                    }
                ]
            },
            {
                "task_id": "publish-loop",
                "task_type": "loop",
                "name": "Publish to Each Destination",
                "items_source": "$input.destinations",
                "item_variable": "destination",
                "tasks": [
                    {
                        "task_id": "publish-destination",
                        "task_type": TaskType.PUBLISH_ASSET.value,
                        "name": "Publish to Destination",
                        "parameters": {
                            "asset_id": "$input.asset_id",
                            "destination": "$variables.destination",
                            "embargo_date": "$input.embargo_date"
                        }
                    }
                ]
            },
            {
                "task_id": "update-status",
                "task_type": TaskType.UPDATE_ASSET.value,
                "name": "Update Publication Status",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "metadata": {
                        "publication_status": "published",
                        "publication_date": "$now",
                        "published_destinations": "$input.destinations"
                    }
                }
            }
        ],
        "timeout": 7200,
        "max_retries": 2,
        "retry_delay": 600,
        "default_priority": WorkflowPriority.HIGH.value
    }
}

# Archive Management Workflow
ARCHIVE_MANAGEMENT_WORKFLOW = {
    "template_id": "archive-management",
    "name": "Archive Lifecycle Management",
    "description": "Automatically archive assets based on age and usage",
    "category": "content-management",
    "tags": ["archive", "storage", "lifecycle"],
    "is_public": True,
    "definition": {
        "triggers": [
            {
                "trigger_id": "daily-schedule",
                "trigger_type": TriggerType.SCHEDULE.value,
                "schedule": {
                    "schedule_type": "cron",
                    "cron_expression": "0 3 * * *",  # Daily at 3 AM
                    "timezone": "UTC"
                }
            }
        ],
        "variables": {
            "hot_storage_days": 30,
            "warm_storage_days": 90,
            "cold_storage_days": 365
        },
        "tasks": [
            {
                "task_id": "find-candidates",
                "task_type": TaskType.API_CALL.value,
                "name": "Find Archive Candidates",
                "parameters": {
                    "url": "${ASSET_SERVICE_URL}/api/v1/assets/search",
                    "method": "POST",
                    "body": {
                        "filters": {
                            "last_accessed": {
                                "before": "$today - 30 days"
                            },
                            "storage_tier": "hot"
                        },
                        "limit": 1000
                    }
                }
            },
            {
                "task_id": "process-candidates",
                "task_type": "loop",
                "name": "Process Each Candidate",
                "items_source": "$output.find-candidates.body.results",
                "item_variable": "asset",
                "parallel_execution": True,
                "max_concurrent": 10,
                "tasks": [
                    {
                        "task_id": "determine-tier",
                        "task_type": TaskType.SCRIPT_EXECUTION.value,
                        "name": "Determine Storage Tier",
                        "parameters": {
                            "script": "determine_storage_tier.py",
                            "args": {
                                "asset": "$variables.asset",
                                "hot_days": "$variables.hot_storage_days",
                                "warm_days": "$variables.warm_storage_days",
                                "cold_days": "$variables.cold_storage_days"
                            }
                        }
                    },
                    {
                        "task_id": "move-to-tier",
                        "task_type": TaskType.ARCHIVE_FILE.value,
                        "name": "Move to Storage Tier",
                        "parameters": {
                            "asset_id": "$variables.asset.id",
                            "tier": "$output.determine-tier.tier"
                        }
                    },
                    {
                        "task_id": "update-metadata",
                        "task_type": TaskType.UPDATE_ASSET.value,
                        "name": "Update Archive Status",
                        "parameters": {
                            "asset_id": "$variables.asset.id",
                            "metadata": {
                                "storage_tier": "$output.determine-tier.tier",
                                "archived_date": "$now"
                            }
                        }
                    }
                ]
            },
            {
                "task_id": "generate-report",
                "task_type": TaskType.SCRIPT_EXECUTION.value,
                "name": "Generate Archive Report",
                "parameters": {
                    "script": "generate_archive_report.py",
                    "args": {
                        "processed_assets": "$output.process-candidates",
                        "date": "$today"
                    }
                }
            },
            {
                "task_id": "send-report",
                "task_type": TaskType.SEND_EMAIL.value,
                "name": "Send Archive Report",
                "parameters": {
                    "to": ["storage-admin@company.com"],
                    "subject": "Daily Archive Report",
                    "template": "archive_report",
                    "template_data": {
                        "report": "$output.generate-report"
                    }
                }
            }
        ],
        "timeout": 14400,  # 4 hours
        "max_retries": 1,
        "retry_delay": 1800,
        "default_priority": WorkflowPriority.LOW.value
    }
}

# Content Review and Approval Workflow
CONTENT_REVIEW_WORKFLOW = {
    "template_id": "content-review",
    "name": "Content Review and Approval",
    "description": "Multi-stage content review with feedback collection",
    "category": "content-management",
    "tags": ["review", "approval", "collaboration"],
    "is_public": True,
    "definition": {
        "triggers": [
            {
                "trigger_id": "review-request",
                "trigger_type": TriggerType.EVENT.value,
                "events": [
                    {
                        "event_type": "review.requested",
                        "filters": {}
                    }
                ]
            }
        ],
        "variables": {
            "review_stages": ["technical", "editorial", "final"],
            "allow_parallel_reviews": False
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset to review"
                },
                "reviewers": {
                    "type": "object",
                    "properties": {
                        "technical": {"type": "array", "items": {"type": "string"}},
                        "editorial": {"type": "array", "items": {"type": "string"}},
                        "final": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "required": ["asset_id", "reviewers"]
        },
        "tasks": [
            {
                "task_id": "create-review-proxy",
                "task_type": TaskType.GENERATE_PROXY.value,
                "name": "Create Review Proxy",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "quality": "medium",
                    "watermark": True,
                    "watermark_text": "REVIEW COPY"
                }
            },
            {
                "task_id": "review-stages",
                "task_type": "conditional",
                "name": "Review Process Type",
                "conditions": [
                    {
                        "field": "$variables.allow_parallel_reviews",
                        "operator": ConditionOperator.EQUALS.value,
                        "value": True
                    }
                ],
                "then_tasks": [
                    {
                        "task_id": "parallel-reviews",
                        "task_type": "parallel",
                        "name": "Parallel Reviews",
                        "tasks": [
                            {
                                "task_id": "technical-review",
                                "task_type": TaskType.APPROVAL.value,
                                "name": "Technical Review",
                                "parameters": {
                                    "approvers": "$input.reviewers.technical",
                                    "message": "Please complete technical review",
                                    "require_all": False
                                }
                            },
                            {
                                "task_id": "editorial-review",
                                "task_type": TaskType.APPROVAL.value,
                                "name": "Editorial Review",
                                "parameters": {
                                    "approvers": "$input.reviewers.editorial",
                                    "message": "Please complete editorial review",
                                    "require_all": False
                                }
                            }
                        ]
                    }
                ],
                "else_tasks": [
                    {
                        "task_id": "sequential-reviews",
                        "task_type": "sequential",
                        "name": "Sequential Reviews",
                        "tasks": [
                            {
                                "task_id": "technical-review-seq",
                                "task_type": TaskType.APPROVAL.value,
                                "name": "Technical Review",
                                "parameters": {
                                    "approvers": "$input.reviewers.technical",
                                    "message": "Please complete technical review"
                                }
                            },
                            {
                                "task_id": "editorial-review-seq",
                                "task_type": TaskType.APPROVAL.value,
                                "name": "Editorial Review",
                                "parameters": {
                                    "approvers": "$input.reviewers.editorial",
                                    "message": "Please complete editorial review"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "task_id": "final-approval",
                "task_type": TaskType.APPROVAL.value,
                "name": "Final Approval",
                "parameters": {
                    "approvers": "$input.reviewers.final",
                    "message": "Please provide final approval",
                    "require_all": True
                }
            },
            {
                "task_id": "mark-approved",
                "task_type": TaskType.UPDATE_ASSET.value,
                "name": "Mark as Approved",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "metadata": {
                        "review_status": "approved",
                        "approval_date": "$now",
                        "approved_by": "$output.final-approval.approved_by"
                    }
                }
            }
        ],
        "timeout": 259200,  # 72 hours
        "max_retries": 0,
        "default_priority": WorkflowPriority.NORMAL.value
    }
}