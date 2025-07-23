"""
Sample onboarding flows and data
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging

from src.db.base import get_async_session
from src.db.models import (
    OnboardingFlow, OnboardingStep, Tutorial, OnboardingGoal,
    FlowType, StepType, UserRole
)

logger = logging.getLogger(__name__)


async def create_sample_flows():
    """Create sample onboarding flows for development"""
    async with get_async_session() as db:
        try:
            # Check if flows already exist
            existing = await db.execute(select(OnboardingFlow).limit(1))
            if existing.scalar():
                logger.info("Sample flows already exist")
                return
            
            # Create Organization Setup Flow
            org_flow = OnboardingFlow(
                name="Organization Setup",
                description="Complete your organization profile and configure initial settings",
                type=FlowType.ORGANIZATION_SETUP,
                target_roles=[UserRole.ADMIN],
                is_mandatory=True,
                estimated_duration_minutes=45,
                metadata={
                    "icon": "business",
                    "color": "#1976d2"
                }
            )
            db.add(org_flow)
            await db.flush()
            
            # Add steps to Organization Setup
            org_steps = [
                OnboardingStep(
                    flow_id=org_flow.id,
                    title="Welcome to MAMS",
                    description="Learn about the Media Asset Management System and its capabilities",
                    type=StepType.INFORMATION,
                    order=0,
                    content={
                        "sections": [
                            {
                                "title": "What is MAMS?",
                                "content": "MAMS is an enterprise-grade media asset management platform..."
                            },
                            {
                                "title": "Key Benefits",
                                "bullets": [
                                    "Centralized media storage",
                                    "Advanced search capabilities",
                                    "Collaborative workflows",
                                    "AI-powered features"
                                ]
                            }
                        ]
                    },
                    estimated_duration_minutes=3
                ),
                OnboardingStep(
                    flow_id=org_flow.id,
                    title="Organization Profile",
                    description="Set up your organization's basic information",
                    type=StepType.FORM,
                    order=1,
                    content={
                        "fields": [
                            {
                                "name": "company_name",
                                "label": "Company Name",
                                "type": "text",
                                "required": True
                            },
                            {
                                "name": "industry",
                                "label": "Industry",
                                "type": "select",
                                "options": ["Broadcasting", "Film Production", "News", "Marketing", "Other"],
                                "required": True
                            },
                            {
                                "name": "company_size",
                                "label": "Company Size",
                                "type": "select",
                                "options": ["1-10", "11-50", "51-200", "201-1000", "1000+"],
                                "required": True
                            }
                        ]
                    },
                    validation_rules=[
                        {"field": "company_name", "rule": "required"},
                        {"field": "industry", "rule": "required"}
                    ],
                    estimated_duration_minutes=5
                ),
                OnboardingStep(
                    flow_id=org_flow.id,
                    title="Storage Configuration",
                    description="Configure your media storage settings",
                    type=StepType.INTERACTIVE,
                    order=2,
                    content={
                        "component": "StorageConfig",
                        "options": {
                            "storage_types": ["Local", "S3", "Azure", "Google Cloud"],
                            "features": ["Auto-archiving", "Redundancy", "CDN Integration"]
                        }
                    },
                    action_url="/api/v1/storage/configure",
                    estimated_duration_minutes=10
                ),
                OnboardingStep(
                    flow_id=org_flow.id,
                    title="User Management",
                    description="Invite your team members and set up departments",
                    type=StepType.ACTION,
                    order=3,
                    content={
                        "action": "invite_users",
                        "minimum_users": 1,
                        "departments": ["Production", "Editorial", "Marketing", "IT"]
                    },
                    action_url="/api/v1/users/bulk-invite",
                    estimated_duration_minutes=8
                ),
                OnboardingStep(
                    flow_id=org_flow.id,
                    title="Security Settings",
                    description="Configure security and compliance settings",
                    type=StepType.FORM,
                    order=4,
                    content={
                        "sections": [
                            {
                                "title": "Authentication",
                                "fields": [
                                    {
                                        "name": "enable_mfa",
                                        "label": "Require Multi-Factor Authentication",
                                        "type": "checkbox"
                                    },
                                    {
                                        "name": "password_policy",
                                        "label": "Password Complexity",
                                        "type": "select",
                                        "options": ["Basic", "Medium", "Strong"]
                                    }
                                ]
                            },
                            {
                                "title": "Compliance",
                                "fields": [
                                    {
                                        "name": "gdpr_compliance",
                                        "label": "Enable GDPR Compliance Features",
                                        "type": "checkbox"
                                    }
                                ]
                            }
                        ]
                    },
                    estimated_duration_minutes=5
                )
            ]
            
            for step in org_steps:
                db.add(step)
            
            # Create Content Creator Flow
            creator_flow = OnboardingFlow(
                name="Content Creator Onboarding",
                description="Learn how to upload, manage, and collaborate on media assets",
                type=FlowType.ROLE_SPECIFIC,
                target_roles=[UserRole.CONTENT_CREATOR],
                is_mandatory=False,
                estimated_duration_minutes=30,
                metadata={
                    "icon": "video_library",
                    "color": "#388e3c"
                }
            )
            db.add(creator_flow)
            await db.flush()
            
            # Add steps to Content Creator Flow
            creator_steps = [
                OnboardingStep(
                    flow_id=creator_flow.id,
                    title="Asset Upload Basics",
                    description="Learn how to upload your media files",
                    type=StepType.VIDEO,
                    order=0,
                    content={
                        "video_url": "/tutorials/asset-upload.mp4",
                        "duration": 180,
                        "chapters": [
                            {"time": 0, "title": "Introduction"},
                            {"time": 30, "title": "Drag and Drop Upload"},
                            {"time": 90, "title": "Bulk Upload"},
                            {"time": 150, "title": "Upload Settings"}
                        ]
                    },
                    estimated_duration_minutes=5
                ),
                OnboardingStep(
                    flow_id=creator_flow.id,
                    title="Practice Upload",
                    description="Try uploading a sample asset",
                    type=StepType.INTERACTIVE,
                    order=1,
                    content={
                        "component": "PracticeUpload",
                        "sample_files": ["sample-video.mp4", "sample-image.jpg"],
                        "success_criteria": {
                            "files_uploaded": 1,
                            "metadata_added": True
                        }
                    },
                    requires_completion=True,
                    estimated_duration_minutes=8
                ),
                OnboardingStep(
                    flow_id=creator_flow.id,
                    title="Metadata Best Practices",
                    description="Learn how to add effective metadata to your assets",
                    type=StepType.INFORMATION,
                    order=2,
                    content={
                        "sections": [
                            {
                                "title": "Why Metadata Matters",
                                "content": "Good metadata makes your assets discoverable..."
                            },
                            {
                                "title": "Essential Fields",
                                "fields": ["Title", "Description", "Tags", "Copyright", "Creation Date"]
                            },
                            {
                                "title": "Tips",
                                "bullets": [
                                    "Use descriptive titles",
                                    "Add relevant tags",
                                    "Include technical details",
                                    "Specify usage rights"
                                ]
                            }
                        ]
                    },
                    is_optional=True,
                    estimated_duration_minutes=5
                ),
                OnboardingStep(
                    flow_id=creator_flow.id,
                    title="Collaboration Features",
                    description="Learn how to share and collaborate on assets",
                    type=StepType.TUTORIAL,
                    order=3,
                    content={
                        "tutorial_id": "collaboration-basics",
                        "interactive": True,
                        "features": ["Sharing", "Comments", "Version Control", "Collections"]
                    },
                    estimated_duration_minutes=10
                ),
                OnboardingStep(
                    flow_id=creator_flow.id,
                    title="Knowledge Check",
                    description="Test your understanding of asset management",
                    type=StepType.QUIZ,
                    order=4,
                    content={
                        "questions": [
                            {
                                "question": "What is the maximum file size for uploads?",
                                "type": "multiple_choice",
                                "options": ["1GB", "5GB", "10GB", "Unlimited"],
                                "correct": 2
                            },
                            {
                                "question": "Which metadata fields are required?",
                                "type": "multiple_select",
                                "options": ["Title", "Description", "Tags", "Location"],
                                "correct": [0, 1]
                            }
                        ],
                        "passing_score": 70
                    },
                    validation_rules=[
                        {"rule": "minimum_score", "value": 70}
                    ],
                    is_optional=True,
                    estimated_duration_minutes=5
                )
            ]
            
            for step in creator_steps:
                db.add(step)
            
            # Create Feature Introduction Flow
            feature_flow = OnboardingFlow(
                name="AI Features Introduction",
                description="Discover MAMS's AI-powered features for automatic tagging and content analysis",
                type=FlowType.FEATURE_INTRODUCTION,
                target_roles=[],  # Available to all roles
                is_mandatory=False,
                estimated_duration_minutes=20,
                prerequisites=[creator_flow.id],  # Requires basic onboarding first
                metadata={
                    "icon": "psychology",
                    "color": "#f57c00"
                }
            )
            db.add(feature_flow)
            
            # Create sample tutorials
            tutorials = [
                Tutorial(
                    title="Getting Started with MAMS",
                    description="A comprehensive introduction to the platform",
                    category="Basics",
                    content_type="video",
                    content_url="/tutorials/getting-started.mp4",
                    duration_minutes=15,
                    difficulty_level="beginner",
                    target_roles=[],
                    is_featured=True,
                    tags=["introduction", "basics", "getting-started"]
                ),
                Tutorial(
                    title="Advanced Search Techniques",
                    description="Master the search capabilities of MAMS",
                    category="Search",
                    content_type="interactive",
                    content_url="/tutorials/advanced-search",
                    duration_minutes=20,
                    difficulty_level="intermediate",
                    target_roles=[UserRole.CONTENT_CREATOR, UserRole.EDITOR],
                    tags=["search", "advanced", "productivity"]
                ),
                Tutorial(
                    title="Workflow Automation",
                    description="Set up automated workflows for your team",
                    category="Workflows",
                    content_type="article",
                    content_url="/tutorials/workflow-automation",
                    duration_minutes=25,
                    difficulty_level="advanced",
                    target_roles=[UserRole.ADMIN],
                    tags=["automation", "workflows", "efficiency"]
                )
            ]
            
            for tutorial in tutorials:
                db.add(tutorial)
            
            # Create sample goals
            goals = [
                OnboardingGoal(
                    name="Quick Starter",
                    description="Complete your first onboarding flow",
                    target_metric="flows_completed",
                    target_value=1,
                    time_limit_days=7,
                    reward_type="badge",
                    reward_data={"badge_name": "quick_starter", "icon": "rocket"}
                ),
                OnboardingGoal(
                    name="Team Builder",
                    description="Invite 5 team members",
                    target_metric="users_invited",
                    target_value=5,
                    time_limit_days=30,
                    reward_type="feature_unlock",
                    reward_data={"feature": "advanced_analytics"}
                ),
                OnboardingGoal(
                    name="Asset Master",
                    description="Upload 10 assets with complete metadata",
                    target_metric="assets_uploaded",
                    target_value=10,
                    time_limit_days=14,
                    reward_type="badge",
                    reward_data={"badge_name": "asset_master", "icon": "star"}
                )
            ]
            
            for goal in goals:
                db.add(goal)
            
            await db.commit()
            
            logger.info("Sample onboarding flows created successfully")
            
        except Exception as e:
            logger.error(f"Error creating sample flows: {e}")
            await db.rollback()