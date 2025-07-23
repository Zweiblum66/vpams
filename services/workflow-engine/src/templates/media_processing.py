"""
Media Processing Workflow Templates
"""

from ..models.schemas import (
    TaskType, TriggerType, WorkflowPriority,
    ConditionOperator
)

# Standard Media Ingest Workflow
MEDIA_INGEST_WORKFLOW = {
    "template_id": "media-ingest-standard",
    "name": "Standard Media Ingest",
    "description": "Process newly uploaded media files with metadata extraction, proxy generation, and auto-tagging",
    "category": "media-processing",
    "tags": ["ingest", "media", "automated"],
    "is_public": True,
    "definition": {
        "triggers": [
            {
                "trigger_id": "file-upload",
                "trigger_type": TriggerType.EVENT.value,
                "events": [
                    {
                        "event_type": "asset.created",
                        "filters": {
                            "asset_type": "media"
                        }
                    }
                ],
                "input_mapping": {
                    "asset_id": "$event.asset_id"
                }
            }
        ],
        "variables": {
            "proxy_quality": "medium",
            "thumbnail_count": 3,
            "auto_publish": False
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset ID to process"
                }
            },
            "required": ["asset_id"]
        },
        "tasks": [
            {
                "task_id": "extract-metadata",
                "task_type": TaskType.EXTRACT_METADATA.value,
                "name": "Extract Metadata",
                "description": "Extract technical and descriptive metadata",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "extractors": ["basic", "technical", "exif"]
                }
            },
            {
                "task_id": "generate-proxy",
                "task_type": TaskType.GENERATE_PROXY.value,
                "name": "Generate Proxy",
                "description": "Generate proxy video for preview",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "quality": "$variables.proxy_quality"
                },
                "depends_on": ["extract-metadata"]
            },
            {
                "task_id": "generate-thumbnails",
                "task_type": TaskType.GENERATE_THUMBNAIL.value,
                "name": "Generate Thumbnails",
                "description": "Generate thumbnail images",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "count": "$variables.thumbnail_count",
                    "method": "interval"
                },
                "depends_on": ["extract-metadata"]
            },
            {
                "task_id": "auto-tag",
                "task_type": TaskType.AUTO_TAG.value,
                "name": "Auto Tag Content",
                "description": "Automatically tag content using AI",
                "parameters": {
                    "asset_id": "$input.asset_id"
                },
                "depends_on": ["generate-proxy"]
            },
            {
                "task_id": "notify-complete",
                "task_type": TaskType.SEND_NOTIFICATION.value,
                "name": "Notify Completion",
                "description": "Send notification when processing is complete",
                "parameters": {
                    "user_id": "$workflow.triggered_by",
                    "title": "Media Processing Complete",
                    "message": "Your media file has been processed successfully",
                    "data": {
                        "asset_id": "$input.asset_id"
                    }
                }
            }
        ],
        "timeout": 3600,
        "max_retries": 3,
        "retry_delay": 300,
        "default_priority": WorkflowPriority.NORMAL.value
    }
}

# Advanced Media Processing with Quality Control
MEDIA_QC_WORKFLOW = {
    "template_id": "media-qc-advanced",
    "name": "Media Processing with QC",
    "description": "Advanced media processing with quality control checks and approval workflow",
    "category": "media-processing",
    "tags": ["ingest", "media", "qc", "approval"],
    "is_public": True,
    "definition": {
        "triggers": [
            {
                "trigger_id": "manual-trigger",
                "trigger_type": TriggerType.MANUAL.value
            }
        ],
        "variables": {
            "proxy_qualities": ["low", "medium", "high"],
            "require_approval": True,
            "qc_profile": "broadcast"
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset ID to process"
                },
                "destination": {
                    "type": "string",
                    "description": "Target destination for the asset"
                }
            },
            "required": ["asset_id"]
        },
        "tasks": [
            {
                "task_id": "extract-metadata",
                "task_type": TaskType.EXTRACT_METADATA.value,
                "name": "Extract Metadata",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "extractors": ["basic", "technical", "timecode", "loudness"]
                }
            },
            {
                "task_id": "quality-check",
                "task_type": TaskType.ANALYZE_CONTENT.value,
                "name": "Quality Control Check",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "profile": "$variables.qc_profile"
                }
            },
            {
                "task_id": "check-qc-pass",
                "task_type": "conditional",
                "name": "Check QC Results",
                "conditions": [
                    {
                        "field": "$output.quality-check.qc_passed",
                        "operator": ConditionOperator.EQUALS.value,
                        "value": True
                    }
                ],
                "then_tasks": [
                    {
                        "task_id": "generate-proxies",
                        "task_type": "parallel",
                        "name": "Generate All Proxies",
                        "tasks": [
                            {
                                "task_id": "proxy-low",
                                "task_type": TaskType.GENERATE_PROXY.value,
                                "name": "Generate Low Quality Proxy",
                                "parameters": {
                                    "asset_id": "$input.asset_id",
                                    "quality": "low"
                                }
                            },
                            {
                                "task_id": "proxy-medium",
                                "task_type": TaskType.GENERATE_PROXY.value,
                                "name": "Generate Medium Quality Proxy",
                                "parameters": {
                                    "asset_id": "$input.asset_id",
                                    "quality": "medium"
                                }
                            },
                            {
                                "task_id": "proxy-high",
                                "task_type": TaskType.GENERATE_PROXY.value,
                                "name": "Generate Edit Quality Proxy",
                                "parameters": {
                                    "asset_id": "$input.asset_id",
                                    "quality": "edit"
                                }
                            }
                        ]
                    }
                ],
                "else_tasks": [
                    {
                        "task_id": "qc-failed-notification",
                        "task_type": TaskType.SEND_EMAIL.value,
                        "name": "QC Failed Notification",
                        "parameters": {
                            "to": ["qc-team@company.com"],
                            "subject": "Quality Control Failed",
                            "template": "qc_failed",
                            "template_data": {
                                "asset_id": "$input.asset_id",
                                "issues": "$output.quality-check.issues"
                            }
                        }
                    }
                ]
            },
            {
                "task_id": "request-approval",
                "task_type": TaskType.APPROVAL.value,
                "name": "Request Publishing Approval",
                "parameters": {
                    "approvers": ["content-manager", "technical-lead"],
                    "message": "Please review and approve this asset for publishing",
                    "timeout": 86400
                },
                "depends_on": ["generate-proxies"]
            },
            {
                "task_id": "publish-asset",
                "task_type": TaskType.PUBLISH_ASSET.value,
                "name": "Publish Asset",
                "parameters": {
                    "asset_id": "$input.asset_id",
                    "destination": "$input.destination",
                    "settings": {
                        "include_metadata": True,
                        "include_proxies": True
                    }
                },
                "depends_on": ["request-approval"]
            }
        ],
        "timeout": 7200,
        "max_retries": 2,
        "retry_delay": 600,
        "default_priority": WorkflowPriority.HIGH.value
    }
}

# Batch Transcode Workflow
BATCH_TRANSCODE_WORKFLOW = {
    "template_id": "batch-transcode",
    "name": "Batch Transcode",
    "description": "Transcode multiple assets to various formats",
    "category": "media-processing",
    "tags": ["transcode", "batch", "media"],
    "is_public": True,
    "definition": {
        "triggers": [
            {
                "trigger_id": "schedule-trigger",
                "trigger_type": TriggerType.SCHEDULE.value,
                "schedule": {
                    "schedule_type": "cron",
                    "cron_expression": "0 2 * * *",  # Daily at 2 AM
                    "timezone": "UTC"
                }
            }
        ],
        "variables": {
            "output_formats": ["mp4", "webm"],
            "profiles": {
                "mp4": "h264-1080p",
                "webm": "vp9-1080p"
            }
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_ids": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of asset IDs to transcode"
                }
            },
            "required": ["asset_ids"]
        },
        "tasks": [
            {
                "task_id": "process-assets",
                "task_type": "loop",
                "name": "Process Each Asset",
                "items_source": "$input.asset_ids",
                "item_variable": "current_asset_id",
                "parallel_execution": True,
                "max_iterations": 100,
                "tasks": [
                    {
                        "task_id": "transcode-formats",
                        "task_type": "parallel",
                        "name": "Transcode to All Formats",
                        "tasks": [
                            {
                                "task_id": "transcode-mp4",
                                "task_type": TaskType.TRANSCODE.value,
                                "name": "Transcode to MP4",
                                "parameters": {
                                    "asset_id": "$variables.current_asset_id",
                                    "profile": "$variables.profiles.mp4",
                                    "output_format": "mp4"
                                }
                            },
                            {
                                "task_id": "transcode-webm",
                                "task_type": TaskType.TRANSCODE.value,
                                "name": "Transcode to WebM",
                                "parameters": {
                                    "asset_id": "$variables.current_asset_id",
                                    "profile": "$variables.profiles.webm",
                                    "output_format": "webm"
                                }
                            }
                        ]
                    },
                    {
                        "task_id": "update-asset",
                        "task_type": TaskType.UPDATE_ASSET.value,
                        "name": "Update Asset Status",
                        "parameters": {
                            "asset_id": "$variables.current_asset_id",
                            "metadata": {
                                "transcode_status": "completed",
                                "transcode_date": "$now"
                            }
                        }
                    }
                ]
            },
            {
                "task_id": "send-report",
                "task_type": TaskType.SEND_EMAIL.value,
                "name": "Send Completion Report",
                "parameters": {
                    "to": ["operations@company.com"],
                    "subject": "Batch Transcode Complete",
                    "template": "batch_report",
                    "template_data": {
                        "total_assets": "$input.asset_ids.length",
                        "completion_time": "$now"
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