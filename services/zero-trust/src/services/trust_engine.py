"""
Trust Engine - Core zero-trust verification and evaluation system.

Implements continuous verification, trust scoring, and adaptive access controls
based on multiple factors including device, location, behavior, and context.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
import ipaddress

from ..core.config import get_settings
from ..core.exceptions import (
    TrustEvaluationError, AccessDeniedError, InsufficientTrustError,
    DeviceNotTrustedError, LocationRestrictedError, TimeRestrictedError,
    MFARequiredError, PolicyViolationError, AnomalousActivityError,
    HighRiskSessionError, NetworkNotTrustedError, SessionExpiredError
)
from ..models.schemas import (
    TrustRequest, TrustResult, TrustLevel, RiskLevel, DeviceInfo,
    SessionContext, TrustFactor, AccessDecision
)
from .device_analyzer import DeviceAnalyzer
from .behavior_analyzer import BehaviorAnalyzer
from .risk_assessor import RiskAssessor
from .policy_engine import PolicyEngine
from .threat_intelligence import ThreatIntelligence


logger = structlog.get_logger()


class TrustDecision(Enum):
    """Trust-based access decisions."""
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    STEP_UP_AUTH = "step_up_auth"
    MONITOR = "monitor"


@dataclass
class TrustEvaluation:
    """Result of trust evaluation."""
    user_id: str
    session_id: str
    device_id: str
    trust_score: float
    risk_score: float
    decision: TrustDecision
    factors: Dict[str, Any]
    recommendations: List[str]
    expires_at: datetime
    metadata: Dict[str, Any]


class TrustEngine:
    """Main trust engine for zero-trust security evaluation."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Core components
        self.device_analyzer: Optional[DeviceAnalyzer] = None
        self.behavior_analyzer: Optional[BehaviorAnalyzer] = None
        self.risk_assessor: Optional[RiskAssessor] = None
        self.policy_engine: Optional[PolicyEngine] = None
        self.threat_intelligence: Optional[ThreatIntelligence] = None
        
        # Trust tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.trust_history: Dict[str, List[TrustEvaluation]] = {}
        self.device_trust_cache: Dict[str, Dict[str, Any]] = {}
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        # Statistics
        self.stats = {
            "evaluations_performed": 0,
            "access_granted": 0,
            "access_denied": 0,
            "challenges_issued": 0,
            "anomalies_detected": 0,
            "average_trust_score": 0.0,
            "last_evaluation": None
        }
    
    async def initialize(self) -> None:
        """Initialize trust engine and all components."""
        try:
            logger.info("Initializing trust engine")
            
            # Initialize device analyzer
            self.device_analyzer = DeviceAnalyzer()
            await self.device_analyzer.initialize()
            logger.info("Device analyzer initialized")
            
            # Initialize behavior analyzer
            if self.settings.behavioral_analysis_enabled:
                self.behavior_analyzer = BehaviorAnalyzer()
                await self.behavior_analyzer.initialize()
                logger.info("Behavior analyzer initialized")
            
            # Initialize risk assessor
            if self.settings.risk_assessment_enabled:
                self.risk_assessor = RiskAssessor()
                await self.risk_assessor.initialize()
                logger.info("Risk assessor initialized")
            
            # Initialize policy engine
            if self.settings.policy_engine_enabled:
                self.policy_engine = PolicyEngine()
                await self.policy_engine.initialize()
                logger.info("Policy engine initialized")
            
            # Initialize threat intelligence
            if self.settings.threat_intel_enabled:
                self.threat_intelligence = ThreatIntelligence()
                await self.threat_intelligence.initialize()
                logger.info("Threat intelligence initialized")
            
            # Start background tasks
            await self._start_background_tasks()
            self._running = True
            
            logger.info(
                "Trust engine initialized",
                components_active={
                    "device_analyzer": self.device_analyzer is not None,
                    "behavior_analyzer": self.behavior_analyzer is not None,
                    "risk_assessor": self.risk_assessor is not None,
                    "policy_engine": self.policy_engine is not None,
                    "threat_intelligence": self.threat_intelligence is not None
                }
            )
            
        except Exception as e:
            logger.error("Failed to initialize trust engine", error=str(e))
            raise TrustEvaluationError(f"Initialization failed: {str(e)}")
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring and evaluation tasks."""
        # Continuous session verification
        if self.settings.continuous_auth_enabled:
            task = asyncio.create_task(self._continuous_verification_loop())
            self._tasks.append(task)
        
        # Trust score decay
        task = asyncio.create_task(self._trust_decay_loop())
        self._tasks.append(task)
        
        # Statistics update
        task = asyncio.create_task(self._stats_update_loop())
        self._tasks.append(task)
        
        # Session cleanup
        task = asyncio.create_task(self._session_cleanup_loop())
        self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background tasks")
    
    async def evaluate_trust(self, request: TrustRequest) -> TrustResult:
        """Evaluate trust for a user access request."""
        try:
            start_time = time.time()
            self.stats["evaluations_performed"] += 1
            
            logger.info(
                "Evaluating trust",
                user_id=request.user_id,
                resource=request.resource,
                action=request.action,
                source_ip=request.source_ip
            )
            
            # Build session context
            session_context = await self._build_session_context(request)
            
            # Perform trust evaluation
            evaluation = await self._perform_trust_evaluation(request, session_context)
            
            # Make access decision
            decision = await self._make_access_decision(evaluation, request)
            
            # Update statistics
            evaluation_time = time.time() - start_time
            await self._update_evaluation_stats(evaluation, evaluation_time)
            
            # Store evaluation result
            await self._store_evaluation(evaluation)
            
            # Create result
            result = TrustResult(
                user_id=request.user_id,
                session_id=request.session_id,
                trust_score=evaluation.trust_score,
                risk_score=evaluation.risk_score,
                decision=decision.decision,
                trust_level=self._score_to_trust_level(evaluation.trust_score),
                risk_level=self._score_to_risk_level(evaluation.risk_score),
                factors=evaluation.factors,
                recommendations=evaluation.recommendations,
                expires_at=evaluation.expires_at,
                metadata={
                    **evaluation.metadata,
                    "evaluation_time_ms": round(evaluation_time * 1000, 2)
                }
            )
            
            logger.info(
                "Trust evaluation completed",
                user_id=request.user_id,
                trust_score=evaluation.trust_score,
                risk_score=evaluation.risk_score,
                decision=decision.decision.value,
                evaluation_time=evaluation_time
            )
            
            return result
            
        except Exception as e:
            logger.error("Trust evaluation failed", user_id=request.user_id, error=str(e))
            raise TrustEvaluationError(f"Trust evaluation failed: {str(e)}")
    
    async def _build_session_context(self, request: TrustRequest) -> SessionContext:
        """Build comprehensive session context for evaluation."""
        context = SessionContext(
            user_id=request.user_id,
            session_id=request.session_id,
            device_info=request.device_info,
            source_ip=request.source_ip,
            user_agent=request.user_agent,
            timestamp=datetime.utcnow(),
            resource=request.resource,
            action=request.action
        )
        
        # Add geographic context
        if self.settings.geo_restrictions_enabled:
            geo_info = await self._get_geographic_info(request.source_ip)
            context.geographic_info = geo_info
        
        # Add network context
        if self.settings.network_verification_enabled:
            network_info = await self._get_network_context(request.source_ip)
            context.network_info = network_info
        
        # Add session history
        if request.session_id in self.active_sessions:
            context.session_history = self.active_sessions[request.session_id].get("history", [])
        
        return context
    
    async def _perform_trust_evaluation(self, request: TrustRequest, context: SessionContext) -> TrustEvaluation:
        """Perform comprehensive trust evaluation."""
        factors = {}
        trust_scores = {}
        risk_factors = {}
        recommendations = []
        
        # Device trust evaluation
        if self.device_analyzer:
            device_trust = await self.device_analyzer.evaluate_device_trust(
                request.device_info, request.user_id
            )
            trust_scores["device"] = device_trust.trust_score
            factors["device"] = device_trust.factors
            if device_trust.recommendations:
                recommendations.extend(device_trust.recommendations)
        
        # Behavioral analysis
        if self.behavior_analyzer:
            behavior_analysis = await self.behavior_analyzer.analyze_behavior(
                request.user_id, context
            )
            trust_scores["behavior"] = behavior_analysis.trust_score
            factors["behavior"] = behavior_analysis.factors
            risk_factors["behavioral_anomalies"] = behavior_analysis.anomalies
        
        # Geographic trust evaluation
        geo_trust = await self._evaluate_geographic_trust(context)
        trust_scores["geographic"] = geo_trust
        factors["geographic"] = await self._get_geographic_factors(context)
        
        # Time-based trust evaluation
        time_trust = await self._evaluate_time_based_trust(context)
        trust_scores["time"] = time_trust
        factors["time"] = await self._get_time_factors(context)
        
        # Network trust evaluation
        network_trust = await self._evaluate_network_trust(context)
        trust_scores["network"] = network_trust
        factors["network"] = await self._get_network_factors(context)
        
        # Calculate overall trust score
        overall_trust = await self._calculate_weighted_trust_score(trust_scores)
        
        # Risk assessment
        overall_risk = 0.0
        if self.risk_assessor:
            risk_assessment = await self.risk_assessor.assess_risk(request, context, factors)
            overall_risk = risk_assessment.risk_score
            risk_factors.update(risk_assessment.risk_factors)
        
        # Policy evaluation
        policy_result = None
        if self.policy_engine:
            policy_result = await self.policy_engine.evaluate_policies(request, context)
            if policy_result.violations:
                recommendations.extend(policy_result.recommendations)
        
        # Threat intelligence check
        threat_indicators = []
        if self.threat_intelligence:
            threat_check = await self.threat_intelligence.check_indicators(request, context)
            threat_indicators = threat_check.indicators
            if threat_indicators:
                overall_risk = max(overall_risk, 0.8)  # High risk if threats detected
        
        # Determine expiration
        expires_at = datetime.utcnow() + timedelta(
            seconds=self.settings.trust_verification_interval
        )
        
        evaluation = TrustEvaluation(
            user_id=request.user_id,
            session_id=request.session_id,
            device_id=request.device_info.device_id if request.device_info else "unknown",
            trust_score=overall_trust,
            risk_score=overall_risk,
            decision=TrustDecision.ALLOW,  # Will be determined in _make_access_decision
            factors={
                "trust_scores": trust_scores,
                "risk_factors": risk_factors,
                "policy_result": policy_result.dict() if policy_result else None,
                "threat_indicators": threat_indicators
            },
            recommendations=recommendations,
            expires_at=expires_at,
            metadata={
                "evaluation_method": "comprehensive",
                "components_used": {
                    "device_analyzer": self.device_analyzer is not None,
                    "behavior_analyzer": self.behavior_analyzer is not None,
                    "risk_assessor": self.risk_assessor is not None,
                    "policy_engine": self.policy_engine is not None,
                    "threat_intelligence": self.threat_intelligence is not None
                }
            }
        )
        
        return evaluation
    
    async def _calculate_weighted_trust_score(self, trust_scores: Dict[str, float]) -> float:
        """Calculate weighted overall trust score."""
        weights = self.settings.trust_factor_weights
        weighted_sum = 0.0
        total_weight = 0.0
        
        for factor, score in trust_scores.items():
            weight = weights.get(f"{factor}_trust", 0.2)  # Default weight
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(1.0, weighted_sum / total_weight)
    
    async def _make_access_decision(self, evaluation: TrustEvaluation, request: TrustRequest) -> AccessDecision:
        """Make final access decision based on trust evaluation."""
        trust_score = evaluation.trust_score
        risk_score = evaluation.risk_score
        
        # Check minimum trust threshold
        if trust_score < self.settings.min_trust_score:
            decision = TrustDecision.DENY
            reason = f"Trust score {trust_score:.2f} below minimum {self.settings.min_trust_score}"
        
        # Check high risk threshold
        elif risk_score >= self.settings.high_risk_threshold:
            decision = TrustDecision.CHALLENGE
            reason = f"High risk score {risk_score:.2f}"
        
        # Check for policy violations
        elif evaluation.factors.get("policy_result", {}).get("violations"):
            decision = TrustDecision.DENY
            reason = "Policy violations detected"
        
        # Check for threat indicators
        elif evaluation.factors.get("threat_indicators"):
            decision = TrustDecision.DENY
            reason = "Threat indicators detected"
        
        # Check MFA requirements
        elif await self._requires_mfa(request, evaluation):
            decision = TrustDecision.STEP_UP_AUTH
            reason = "Multi-factor authentication required"
        
        # Default to allow with monitoring
        else:
            if risk_score >= self.settings.medium_risk_threshold:
                decision = TrustDecision.MONITOR
                reason = "Medium risk - monitoring enabled"
            else:
                decision = TrustDecision.ALLOW
                reason = "Trust criteria satisfied"
        
        # Update evaluation with decision
        evaluation.decision = decision
        
        # Update statistics
        if decision == TrustDecision.ALLOW:
            self.stats["access_granted"] += 1
        elif decision in [TrustDecision.DENY]:
            self.stats["access_denied"] += 1
        elif decision in [TrustDecision.CHALLENGE, TrustDecision.STEP_UP_AUTH]:
            self.stats["challenges_issued"] += 1
        
        return AccessDecision(
            decision=decision,
            reason=reason,
            trust_score=trust_score,
            risk_score=risk_score,
            required_actions=evaluation.recommendations
        )
    
    async def _evaluate_geographic_trust(self, context: SessionContext) -> float:
        """Evaluate geographic-based trust."""
        if not self.settings.geo_restrictions_enabled or not context.geographic_info:
            return 1.0
        
        geo_info = context.geographic_info
        country_code = geo_info.get("country_code", "")
        
        # Check blocked countries
        if country_code in self.settings.blocked_countries:
            return 0.0
        
        # Check allowed countries
        if self.settings.allowed_countries and country_code not in self.settings.allowed_countries:
            return 0.3
        
        # Check for known VPN/proxy indicators
        if geo_info.get("is_anonymous_proxy", False):
            return 0.4
        
        return 1.0
    
    async def _evaluate_time_based_trust(self, context: SessionContext) -> float:
        """Evaluate time-based trust."""
        if not self.settings.time_restrictions_enabled:
            return 1.0
        
        current_hour = context.timestamp.hour
        start_hour = self.settings.allowed_hours_start
        end_hour = self.settings.allowed_hours_end
        
        # Check if current time is within allowed hours
        if start_hour <= end_hour:
            # Normal range (e.g., 8-18)
            if start_hour <= current_hour <= end_hour:
                return 1.0
        else:
            # Overnight range (e.g., 22-6)
            if current_hour >= start_hour or current_hour <= end_hour:
                return 1.0
        
        return 0.3  # Lower trust outside business hours
    
    async def _evaluate_network_trust(self, context: SessionContext) -> float:
        """Evaluate network-based trust."""
        if not self.settings.network_verification_enabled:
            return 1.0
        
        source_ip = context.source_ip
        
        try:
            ip_addr = ipaddress.ip_address(source_ip)
            
            # Check trusted networks
            for trusted_network in self.settings.trusted_networks:
                if ip_addr in ipaddress.ip_network(trusted_network, strict=False):
                    return 1.0
            
            # Check untrusted networks
            for untrusted_network in self.settings.untrusted_networks:
                if ip_addr in ipaddress.ip_network(untrusted_network, strict=False):
                    return 0.2
            
            return 0.7  # Neutral trust for unknown networks
            
        except ValueError:
            logger.warning("Invalid IP address", ip=source_ip)
            return 0.1
    
    async def _get_geographic_info(self, ip_address: str) -> Dict[str, Any]:
        """Get geographic information for IP address."""
        # Placeholder implementation - would use GeoIP database
        return {
            "country_code": "US",
            "country_name": "United States",
            "city": "Unknown",
            "is_anonymous_proxy": False,
            "confidence": 0.8
        }
    
    async def _get_network_context(self, ip_address: str) -> Dict[str, Any]:
        """Get network context information."""
        # Placeholder implementation
        return {
            "network_type": "unknown",
            "isp": "unknown",
            "organization": "unknown",
            "threat_level": "low"
        }
    
    async def _get_geographic_factors(self, context: SessionContext) -> Dict[str, Any]:
        """Get geographic trust factors."""
        if not context.geographic_info:
            return {}
        
        return {
            "country": context.geographic_info.get("country_code"),
            "is_proxy": context.geographic_info.get("is_anonymous_proxy", False),
            "confidence": context.geographic_info.get("confidence", 0.0)
        }
    
    async def _get_time_factors(self, context: SessionContext) -> Dict[str, Any]:
        """Get time-based trust factors."""
        current_hour = context.timestamp.hour
        is_business_hours = (
            self.settings.allowed_hours_start <= current_hour <= self.settings.allowed_hours_end
        )
        
        return {
            "hour": current_hour,
            "is_business_hours": is_business_hours,
            "day_of_week": context.timestamp.weekday()
        }
    
    async def _get_network_factors(self, context: SessionContext) -> Dict[str, Any]:
        """Get network trust factors."""
        return {
            "source_ip": context.source_ip,
            "network_info": context.network_info or {}
        }
    
    async def _requires_mfa(self, request: TrustRequest, evaluation: TrustEvaluation) -> bool:
        """Determine if multi-factor authentication is required."""
        if not self.settings.mfa_enforcement_enabled:
            return False
        
        # Always require MFA for high-risk sessions
        if evaluation.risk_score >= self.settings.high_risk_threshold:
            return True
        
        # Require MFA for privileged actions
        if request.action in ["admin", "delete", "modify_permissions"]:
            return True
        
        # Check if user has recent MFA
        session_info = self.active_sessions.get(request.session_id, {})
        last_mfa = session_info.get("last_mfa_verification")
        
        if last_mfa:
            mfa_age = (datetime.utcnow() - last_mfa).total_seconds()
            if mfa_age < self.settings.mfa_grace_period:
                return False
        
        return True
    
    def _score_to_trust_level(self, score: float) -> TrustLevel:
        """Convert trust score to trust level."""
        if score >= 0.9:
            return TrustLevel.HIGH
        elif score >= 0.7:
            return TrustLevel.MEDIUM
        elif score >= 0.5:
            return TrustLevel.LOW
        else:
            return TrustLevel.NONE
    
    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level."""
        if score >= 0.8:
            return RiskLevel.HIGH
        elif score >= 0.5:
            return RiskLevel.MEDIUM
        elif score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    async def _continuous_verification_loop(self) -> None:
        """Background task for continuous session verification."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                
                # Check all active sessions
                for session_id, session_data in list(self.active_sessions.items()):
                    last_verification = session_data.get("last_verification", current_time)
                    
                    # Check if verification is due
                    if (current_time - last_verification).total_seconds() >= self.settings.session_verification_interval:
                        await self._verify_session(session_id, session_data)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Error in continuous verification loop", error=str(e))
                await asyncio.sleep(60)
    
    async def _verify_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Verify an active session."""
        try:
            # Create verification request
            verification_request = TrustRequest(
                user_id=session_data["user_id"],
                session_id=session_id,
                resource="session_verification",
                action="continue",
                source_ip=session_data.get("source_ip", ""),
                device_info=session_data.get("device_info")
            )
            
            # Evaluate trust
            result = await self.evaluate_trust(verification_request)
            
            # Update session based on result
            if result.decision in [TrustDecision.DENY]:
                # Terminate session
                del self.active_sessions[session_id]
                logger.info("Session terminated due to trust violation", session_id=session_id)
            
            elif result.decision in [TrustDecision.CHALLENGE, TrustDecision.STEP_UP_AUTH]:
                # Mark session as requiring verification
                session_data["requires_verification"] = True
                session_data["verification_reason"] = result.decision.value
            
            else:
                # Update last verification time
                session_data["last_verification"] = datetime.utcnow()
                session_data["trust_score"] = result.trust_score
                session_data["risk_score"] = result.risk_score
            
        except Exception as e:
            logger.error("Error verifying session", session_id=session_id, error=str(e))
    
    async def _trust_decay_loop(self) -> None:
        """Background task for trust score decay."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                decay_rate = self.settings.trust_decay_rate
                
                # Apply decay to device trust cache
                for device_id, device_data in self.device_trust_cache.items():
                    last_update = device_data.get("last_update", current_time)
                    hours_elapsed = (current_time - last_update).total_seconds() / 3600
                    
                    if hours_elapsed > 0:
                        current_trust = device_data.get("trust_score", 1.0)
                        decayed_trust = max(0.0, current_trust - (decay_rate * hours_elapsed))
                        device_data["trust_score"] = decayed_trust
                        device_data["last_update"] = current_time
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error("Error in trust decay loop", error=str(e))
                await asyncio.sleep(3600)
    
    async def _stats_update_loop(self) -> None:
        """Background task for updating statistics."""
        while self._running:
            try:
                # Update average trust score
                if self.active_sessions:
                    trust_scores = [
                        session.get("trust_score", 0.0)
                        for session in self.active_sessions.values()
                        if "trust_score" in session
                    ]
                    
                    if trust_scores:
                        self.stats["average_trust_score"] = sum(trust_scores) / len(trust_scores)
                
                self.stats["last_evaluation"] = datetime.utcnow()
                
                logger.debug(
                    "Trust engine statistics",
                    active_sessions=len(self.active_sessions),
                    **self.stats
                )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error("Error in stats update loop", error=str(e))
                await asyncio.sleep(300)
    
    async def _session_cleanup_loop(self) -> None:
        """Background task for cleaning up expired sessions."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                expired_sessions = []
                
                for session_id, session_data in self.active_sessions.items():
                    # Check for expired sessions
                    last_activity = session_data.get("last_activity", current_time)
                    if (current_time - last_activity).total_seconds() > 3600:  # 1 hour timeout
                        expired_sessions.append(session_id)
                
                # Remove expired sessions
                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
                    logger.debug("Removed expired session", session_id=session_id)
                
                await asyncio.sleep(600)  # Clean up every 10 minutes
                
            except Exception as e:
                logger.error("Error in session cleanup loop", error=str(e))
                await asyncio.sleep(600)
    
    async def _store_evaluation(self, evaluation: TrustEvaluation) -> None:
        """Store evaluation result for history and analytics."""
        user_id = evaluation.user_id
        
        if user_id not in self.trust_history:
            self.trust_history[user_id] = []
        
        self.trust_history[user_id].append(evaluation)
        
        # Limit history size
        if len(self.trust_history[user_id]) > 100:
            self.trust_history[user_id] = self.trust_history[user_id][-100:]
    
    async def _update_evaluation_stats(self, evaluation: TrustEvaluation, evaluation_time: float) -> None:
        """Update evaluation statistics."""
        if evaluation.risk_score >= self.settings.high_risk_threshold:
            self.stats["anomalies_detected"] += 1
    
    async def get_session_trust(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current trust information for a session."""
        return self.active_sessions.get(session_id)
    
    async def update_session_activity(self, session_id: str, activity_data: Dict[str, Any]) -> None:
        """Update session activity information."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.utcnow()
            self.active_sessions[session_id].setdefault("activities", []).append({
                **activity_data,
                "timestamp": datetime.utcnow()
            })
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get trust engine statistics."""
        return {
            **self.stats,
            "active_sessions": len(self.active_sessions),
            "device_trust_cache_size": len(self.device_trust_cache),
            "trust_history_users": len(self.trust_history)
        }
    
    async def cleanup(self) -> None:
        """Cleanup trust engine resources."""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._tasks:
                task.cancel()
            
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Cleanup components
            if self.device_analyzer:
                await self.device_analyzer.cleanup()
            
            if self.behavior_analyzer:
                await self.behavior_analyzer.cleanup()
            
            if self.risk_assessor:
                await self.risk_assessor.cleanup()
            
            if self.policy_engine:
                await self.policy_engine.cleanup()
            
            if self.threat_intelligence:
                await self.threat_intelligence.cleanup()
            
            logger.info("Trust engine cleanup completed")
            
        except Exception as e:
            logger.error("Error during trust engine cleanup", error=str(e))