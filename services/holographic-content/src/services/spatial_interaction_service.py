"""Spatial interaction service for holographic content"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import structlog

from ..core.config import settings

logger = structlog.get_logger()


class SpatialInteractionService:
    """Service for spatial interaction with holographic content"""
    
    def __init__(self):
        self.interaction_methods: Dict[str, Any] = {}
        self.active_sessions: Dict[str, Any] = {}
        self.gesture_library: Dict[str, Any] = {}
        self.initialized = False
        
    async def initialize(self):
        """Initialize spatial interaction capabilities"""
        try:
            # Hand tracking methods
            self.interaction_methods['hand_tracking'] = {
                'type': 'optical',
                'name': 'Computer Vision Hand Tracking',
                'capabilities': {
                    'finger_tracking': True,
                    'gesture_recognition': True,
                    'two_hand_support': True,
                    'tracking_rate': 120,  # Hz
                    'latency': 20,  # ms
                    'accuracy': 'sub_millimeter'
                },
                'supported_devices': ['hololens2', 'magic_leap_2', 'quest_pro']
            }
            
            # Eye tracking
            self.interaction_methods['eye_tracking'] = {
                'type': 'infrared',
                'name': 'Infrared Eye Tracking',
                'capabilities': {
                    'gaze_direction': True,
                    'pupil_dilation': True,
                    'blink_detection': True,
                    'attention_mapping': True,
                    'tracking_rate': 90,  # Hz
                    'accuracy': '1_degree'
                },
                'supported_devices': ['hololens2', 'magic_leap_2', 'varjo_aero']
            }
            
            # Voice commands
            self.interaction_methods['voice_control'] = {
                'type': 'speech',
                'name': 'Natural Language Voice Control',
                'capabilities': {
                    'command_recognition': True,
                    'natural_language': True,
                    'multi_language': True,
                    'context_aware': True,
                    'noise_cancellation': True
                },
                'languages': ['en', 'es', 'fr', 'de', 'ja', 'zh']
            }
            
            # Spatial controllers
            self.interaction_methods['controllers'] = {
                'type': 'tracked_controller',
                'name': '6DOF Spatial Controllers',
                'capabilities': {
                    'position_tracking': True,
                    'rotation_tracking': True,
                    'haptic_feedback': True,
                    'button_input': True,
                    'trigger_analog': True,
                    'thumbstick': True
                },
                'supported_devices': ['oculus_touch', 'valve_index', 'pico_controllers']
            }
            
            # Brain-computer interface (experimental)
            self.interaction_methods['neural_interface'] = {
                'type': 'bci',
                'name': 'Neural Interface (Experimental)',
                'capabilities': {
                    'thought_commands': True,
                    'attention_detection': True,
                    'emotional_state': True,
                    'cognitive_load': True
                },
                'status': 'experimental',
                'supported_devices': ['neuralink_dev', 'emotiv_epoc', 'neurable']
            }
            
            # Initialize gesture library
            await self._initialize_gestures()
            
            # Haptic feedback systems
            if settings.ENABLE_HAPTIC_FEEDBACK:
                self.interaction_methods['haptic_feedback'] = {
                    'type': 'tactile',
                    'name': 'Ultrasound Haptic Feedback',
                    'capabilities': {
                        'mid_air_haptics': True,
                        'texture_simulation': True,
                        'force_feedback': True,
                        'thermal_feedback': False
                    },
                    'supported_devices': ['ultraleap', 'ultrahaptics']
                }
            
            self.initialized = True
            logger.info("Spatial interaction service initialized", 
                       method_count=len(self.interaction_methods))
            
        except Exception as e:
            logger.error("Failed to initialize spatial interaction", error=str(e))
            raise
    
    async def _initialize_gestures(self):
        """Initialize gesture recognition library"""
        # Basic gestures
        self.gesture_library['tap'] = {
            'type': 'discrete',
            'fingers': 1,
            'motion': 'forward',
            'duration': 0.2
        }
        
        self.gesture_library['pinch'] = {
            'type': 'continuous',
            'fingers': 2,
            'motion': 'together',
            'parameters': ['distance']
        }
        
        self.gesture_library['grab'] = {
            'type': 'discrete',
            'fingers': 5,
            'motion': 'close',
            'hold': True
        }
        
        self.gesture_library['swipe'] = {
            'type': 'continuous',
            'fingers': 1,
            'motion': 'lateral',
            'parameters': ['direction', 'velocity']
        }
        
        self.gesture_library['rotate'] = {
            'type': 'continuous',
            'fingers': 2,
            'motion': 'circular',
            'parameters': ['angle', 'speed']
        }
        
        # Advanced gestures
        self.gesture_library['bloom'] = {
            'type': 'discrete',
            'fingers': 5,
            'motion': 'expand',
            'system_gesture': True
        }
        
        self.gesture_library['point'] = {
            'type': 'continuous',
            'fingers': 1,
            'motion': 'extended',
            'parameters': ['direction', 'distance']
        }
    
    async def enable(self, hologram_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Enable spatial interaction for a hologram"""
        session_id = f"interact_{datetime.utcnow().timestamp()}"
        
        # Create interaction session
        session = {
            'id': session_id,
            'hologram_id': hologram_id,
            'config': config,
            'status': 'active',
            'start_time': datetime.utcnow(),
            'enabled_methods': [],
            'interaction_log': [],
            'gesture_buffer': [],
            'attention_map': {}
        }
        
        # Enable requested interaction methods
        methods = config.get('methods', ['hand_tracking', 'voice_control'])
        for method in methods:
            if method in self.interaction_methods:
                session['enabled_methods'].append(method)
                logger.info(f"Enabled {method} for hologram", 
                           session_id=session_id, 
                           hologram_id=hologram_id)
        
        self.active_sessions[session_id] = session
        
        # Start interaction monitoring
        asyncio.create_task(self._monitor_interactions(session_id))
        
        return {
            'session_id': session_id,
            'hologram_id': hologram_id,
            'enabled_methods': session['enabled_methods'],
            'status': 'active'
        }
    
    async def _monitor_interactions(self, session_id: str):
        """Monitor and process interactions"""
        try:
            session = self.active_sessions[session_id]
            
            while session['status'] == 'active':
                # Simulate interaction monitoring
                await asyncio.sleep(0.016)  # 60 FPS update rate
                
                # Process gesture buffer
                if session['gesture_buffer']:
                    await self._process_gesture_buffer(session_id)
                
                # Update attention map
                if 'eye_tracking' in session['enabled_methods']:
                    await self._update_attention_map(session_id)
                
        except Exception as e:
            logger.error(f"Interaction monitoring error", session_id=session_id, error=str(e))
    
    async def _process_gesture_buffer(self, session_id: str):
        """Process buffered gestures"""
        session = self.active_sessions[session_id]
        
        # Process each gesture in buffer
        for gesture_data in session['gesture_buffer']:
            gesture_type = gesture_data['type']
            
            if gesture_type in self.gesture_library:
                gesture_def = self.gesture_library[gesture_type]
                
                # Log recognized gesture
                session['interaction_log'].append({
                    'timestamp': datetime.utcnow(),
                    'type': 'gesture',
                    'gesture': gesture_type,
                    'parameters': gesture_data.get('parameters', {}),
                    'confidence': gesture_data.get('confidence', 1.0)
                })
        
        # Clear processed gestures
        session['gesture_buffer'] = []
    
    async def _update_attention_map(self, session_id: str):
        """Update attention heatmap from eye tracking"""
        session = self.active_sessions[session_id]
        
        # Simulate gaze point
        gaze_point = {
            'x': np.random.normal(0.5, 0.1),
            'y': np.random.normal(0.5, 0.1),
            'timestamp': datetime.utcnow()
        }
        
        # Add to attention map
        grid_x = int(gaze_point['x'] * 10)
        grid_y = int(gaze_point['y'] * 10)
        key = f"{grid_x},{grid_y}"
        
        if key not in session['attention_map']:
            session['attention_map'][key] = 0
        session['attention_map'][key] += 1
    
    async def process_hand_gesture(self, session_id: str, gesture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process hand gesture input"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        session = self.active_sessions[session_id]
        
        # Add to gesture buffer for processing
        session['gesture_buffer'].append({
            'type': gesture_data['gesture_type'],
            'parameters': gesture_data.get('parameters', {}),
            'hand': gesture_data.get('hand', 'right'),
            'confidence': gesture_data.get('confidence', 1.0),
            'timestamp': datetime.utcnow()
        })
        
        # Immediate response for certain gestures
        response = {
            'session_id': session_id,
            'gesture_received': gesture_data['gesture_type'],
            'status': 'processing'
        }
        
        # Handle system gestures immediately
        if gesture_data['gesture_type'] == 'bloom':
            response['action'] = 'open_menu'
        elif gesture_data['gesture_type'] == 'tap':
            response['action'] = 'select'
        
        return response
    
    async def process_voice_command(self, session_id: str, voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice command"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        session = self.active_sessions[session_id]
        
        command = voice_data['command'].lower()
        confidence = voice_data.get('confidence', 1.0)
        
        # Log voice interaction
        session['interaction_log'].append({
            'timestamp': datetime.utcnow(),
            'type': 'voice',
            'command': command,
            'confidence': confidence,
            'language': voice_data.get('language', 'en')
        })
        
        # Process commands
        action = None
        if 'rotate' in command:
            action = 'rotate_hologram'
        elif 'scale' in command or 'size' in command:
            action = 'scale_hologram'
        elif 'move' in command:
            action = 'move_hologram'
        elif 'play' in command:
            action = 'play_animation'
        elif 'stop' in command or 'pause' in command:
            action = 'pause_animation'
        elif 'reset' in command:
            action = 'reset_position'
        
        return {
            'session_id': session_id,
            'command': command,
            'action': action,
            'confidence': confidence
        }
    
    async def process_eye_gaze(self, session_id: str, gaze_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process eye gaze data"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        session = self.active_sessions[session_id]
        
        # Check for dwell selection
        target = gaze_data.get('target')
        dwell_time = gaze_data.get('dwell_time', 0)
        
        response = {
            'session_id': session_id,
            'gaze_target': target,
            'dwell_time': dwell_time
        }
        
        # Trigger selection on dwell
        if dwell_time > 1.5:  # 1.5 second dwell
            response['action'] = 'select'
            session['interaction_log'].append({
                'timestamp': datetime.utcnow(),
                'type': 'eye_select',
                'target': target,
                'dwell_time': dwell_time
            })
        
        return response
    
    async def enable_haptic_feedback(self, session_id: str, haptic_config: Dict[str, Any]) -> Dict[str, Any]:
        """Enable haptic feedback for interactions"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        if not settings.ENABLE_HAPTIC_FEEDBACK:
            raise ValueError("Haptic feedback not enabled in settings")
        
        session = self.active_sessions[session_id]
        session['haptic_enabled'] = True
        session['haptic_config'] = haptic_config
        
        return {
            'session_id': session_id,
            'haptic_enabled': True,
            'feedback_types': ['touch', 'texture', 'resistance']
        }
    
    async def trigger_haptic(self, session_id: str, haptic_event: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger haptic feedback"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        session = self.active_sessions[session_id]
        if not session.get('haptic_enabled'):
            raise ValueError("Haptic feedback not enabled for this session")
        
        # Log haptic event
        session['interaction_log'].append({
            'timestamp': datetime.utcnow(),
            'type': 'haptic',
            'event_type': haptic_event['type'],
            'intensity': haptic_event.get('intensity', 0.5),
            'duration': haptic_event.get('duration', 0.1),
            'pattern': haptic_event.get('pattern', 'pulse')
        })
        
        return {
            'session_id': session_id,
            'haptic_triggered': True,
            'event': haptic_event['type']
        }
    
    async def get_interaction_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics for interaction session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        session = self.active_sessions[session_id]
        
        # Analyze interaction log
        interaction_counts = {}
        for interaction in session['interaction_log']:
            int_type = interaction['type']
            if int_type not in interaction_counts:
                interaction_counts[int_type] = 0
            interaction_counts[int_type] += 1
        
        # Calculate session duration
        duration = (datetime.utcnow() - session['start_time']).total_seconds()
        
        # Generate heatmap from attention map
        heatmap_data = []
        if session['attention_map']:
            max_attention = max(session['attention_map'].values())
            for key, value in session['attention_map'].items():
                x, y = map(int, key.split(','))
                heatmap_data.append({
                    'x': x / 10.0,
                    'y': y / 10.0,
                    'intensity': value / max_attention
                })
        
        return {
            'session_id': session_id,
            'duration_seconds': duration,
            'interaction_counts': interaction_counts,
            'total_interactions': len(session['interaction_log']),
            'enabled_methods': session['enabled_methods'],
            'attention_heatmap': heatmap_data,
            'most_used_gesture': max(interaction_counts.items(), key=lambda x: x[1])[0] if interaction_counts else None
        }
    
    async def disable(self, session_id: str) -> Dict[str, Any]:
        """Disable spatial interaction session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session '{session_id}' not found")
        
        session = self.active_sessions[session_id]
        session['status'] = 'disabled'
        session['end_time'] = datetime.utcnow()
        
        # Get final analytics
        analytics = await self.get_interaction_analytics(session_id)
        
        return {
            'session_id': session_id,
            'status': 'disabled',
            'duration': analytics['duration_seconds'],
            'total_interactions': analytics['total_interactions']
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of spatial interaction service"""
        return {
            'status': 'healthy' if self.initialized else 'unhealthy',
            'available_methods': len(self.interaction_methods),
            'active_sessions': len(self.active_sessions),
            'gesture_library_size': len(self.gesture_library),
            'haptic_enabled': settings.ENABLE_HAPTIC_FEEDBACK
        }