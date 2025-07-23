"""
Custom exceptions for Workflow Engine Service
"""


class WorkflowError(Exception):
    """Base exception for workflow errors"""
    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow is not found"""
    pass


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails"""
    pass


class WorkflowTimeoutError(WorkflowError):
    """Raised when workflow execution times out"""
    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails"""
    pass


class TaskError(Exception):
    """Base exception for task errors"""
    pass


class TaskExecutionError(TaskError):
    """Raised when task execution fails"""
    pass


class TaskTimeoutError(TaskError):
    """Raised when task execution times out"""
    pass


class TaskValidationError(TaskError):
    """Raised when task validation fails"""
    pass


class TriggerError(Exception):
    """Base exception for trigger errors"""
    pass


class TriggerNotFoundError(TriggerError):
    """Raised when a trigger is not found"""
    pass


class TriggerExecutionError(TriggerError):
    """Raised when trigger execution fails"""
    pass


class StateError(Exception):
    """Base exception for state management errors"""
    pass


class StateNotFoundError(StateError):
    """Raised when state is not found"""
    pass


class StateLockError(StateError):
    """Raised when state lock operations fail"""
    pass


# Visual Workflow Designer Exceptions

class WorkflowDesignerError(WorkflowError):
    """Base exception for workflow designer errors"""
    pass


class NodeLibraryError(WorkflowDesignerError):
    """Raised when node library operations fail"""
    pass


class NodeNotFoundError(NodeLibraryError):
    """Raised when a node type is not found in the library"""
    pass


class DesignerValidationError(WorkflowDesignerError):
    """Raised when designer validation fails"""
    pass


class ConnectionError(WorkflowDesignerError):
    """Raised when connection operations fail"""
    pass


class DesignerStateError(WorkflowDesignerError):
    """Raised when designer state operations fail"""
    pass


class TemplateError(WorkflowDesignerError):
    """Raised when template operations fail"""
    pass


class ImportExportError(WorkflowDesignerError):
    """Raised when import/export operations fail"""
    pass


class CollaborationError(WorkflowDesignerError):
    """Raised when collaboration operations fail"""
    pass