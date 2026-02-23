"""Feature Flags for gradual rollout of new functionality."""
import os

class FeatureFlags:
    """Central feature flag configuration."""
    
    ENABLE_ITERATION_TRACKING = os.getenv("ENABLE_ITERATION_TRACKING", "true").lower() == "true"
    ENABLE_HUMAN_APPROVAL = os.getenv("ENABLE_HUMAN_APPROVAL", "false").lower() == "true"
    ENABLE_REFLECTION = os.getenv("ENABLE_REFLECTION", "false").lower() == "true"
    ENABLE_ENHANCED_LEARNING = os.getenv("ENABLE_ENHANCED_LEARNING", "false").lower() == "true"
    LEGACY_MODE = not ENABLE_HUMAN_APPROVAL
