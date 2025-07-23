"""Holographic projection service for AR/MR devices"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ..core.config import settings

logger = structlog.get_logger()


class HolographicProjectionService:
    """Service for holographic projection on AR/MR devices"""
    
    def __init__(self):
        self.projection_devices: Dict[str, Any] = {}
        self.active_projections: Dict[str, Any] = {}
        self.initialized = False
        
    async def initialize(self):
        """Initialize holographic projection devices"""
        try:
            # Initialize Microsoft HoloLens
            if settings.MICROSOFT_HOLOLENS_ENABLED:
                self.projection_devices['hololens2'] = {
                    'type': 'ar_headset',
                    'name': 'Microsoft HoloLens 2',
                    'capabilities': {
                        'fov': '52 degrees',
                        'resolution': '2048x1080 per eye',
                        'hand_tracking': True,
                        'eye_tracking': True,
                        'spatial_mapping': True,
                        'gesture_recognition': True,
                        'voice_commands': True,
                        'max_anchors': 100
                    },
                    'status': 'ready'
                }
            
            # Initialize Magic Leap
            if settings.MAGIC_LEAP_ENABLED:
                self.projection_devices['magic_leap_2'] = {
                    'type': 'ar_headset',
                    'name': 'Magic Leap 2',
                    'capabilities': {
                        'fov': '70 degrees',
                        'resolution': '1440x1760 per eye',
                        'hand_tracking': True,
                        'eye_tracking': True,
                        'spatial_computing': True,
                        'segmented_dimming': True,
                        'controller_tracking': True,
                        'max_anchors': 150
                    },
                    'status': 'ready'
                }
            
            # Initialize Realfiction Dreamoc
            if settings.REALFICTION_DREAMOC_ENABLED:
                self.projection_devices['dreamoc_hd3'] = {
                    'type': 'pyramid_display',
                    'name': 'Realfiction Dreamoc HD3',
                    'capabilities': {
                        'display_size': '23 inch',
                        'viewing_angle': '360 degrees',
                        'hologram_size': '30x30x30cm',
                        'resolution': '1920x1080',
                        'multi_user': True,
                        'touch_interaction': False
                    },
                    'status': 'ready'
                }
            
            # Initialize MDH Hologram displays
            if settings.MDH_HOLOGRAM_ENABLED:
                self.projection_devices['mdh_silver'] = {
                    'type': 'pepper_ghost',
                    'name': 'MDH Hologram Silver Series',
                    'capabilities': {
                        'stage_size': '2x2m',
                        'projection_distance': '3-5m',
                        'brightness': '5000 lumens',
                        'resolution': '4K',
                        'life_size': True,
                        'interactive': True
                    },
                    'status': 'ready'
                }
            
            self.initialized = True
            logger.info("Holographic projection service initialized", 
                       device_count=len(self.projection_devices))
            
        except Exception as e:
            logger.error("Failed to initialize holographic projectors", error=str(e))
            raise
    
    async def get_available_projectors(self) -> List[str]:
        """Get list of available projection devices"""
        return list(self.projection_devices.keys())
    
    async def project(self, hologram_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start holographic projection"""
        projection_id = f"holo_proj_{datetime.utcnow().timestamp()}"
        device_name = config.get('device', 'hololens2')
        
        if device_name not in self.projection_devices:
            raise ValueError(f"Projection device '{device_name}' not available")
        
        device = self.projection_devices[device_name]
        
        # Create projection session
        projection_session = {
            'id': projection_id,
            'hologram_id': hologram_id,
            'device': device_name,
            'config': config,
            'status': 'projecting',
            'start_time': datetime.utcnow(),
            'anchors': [],
            'interactions': []
        }
        
        self.active_projections[projection_id] = projection_session
        
        # Start projection based on device type
        if device['type'] == 'ar_headset':
            asyncio.create_task(self._project_ar_headset(projection_id, hologram_id, device, config))
        elif device['type'] == 'pyramid_display':
            asyncio.create_task(self._project_pyramid(projection_id, hologram_id, device, config))
        elif device['type'] == 'pepper_ghost':
            asyncio.create_task(self._project_pepper_ghost(projection_id, hologram_id, device, config))
        
        return {
            'projection_id': projection_id,
            'device': device_name,
            'status': 'started',
            'capabilities': device['capabilities']
        }
    
    async def _project_ar_headset(self, projection_id: str, hologram_id: str, device: Dict[str, Any], config: Dict[str, Any]):
        """Project on AR headset (HoloLens, Magic Leap)"""
        try:
            session = self.active_projections[projection_id]
            
            # Configure AR projection
            ar_config = {
                'hologram_path': f"{hologram_id}_ar.glb",
                'position': config.get('position', [0, 0, 2]),  # 2m in front
                'rotation': config.get('rotation', [0, 0, 0]),
                'scale': config.get('scale', [1, 1, 1]),
                'occlusion': config.get('occlusion', True),
                'physics': config.get('physics', False),
                'persistence': config.get('persistence', True)
            }
            
            # Create spatial anchor
            anchor = {
                'id': f"anchor_{projection_id}",
                'position': ar_config['position'],
                'created_at': datetime.utcnow(),
                'persistent': ar_config['persistence']
            }
            session['anchors'].append(anchor)
            
            # Enable interactions if supported
            if device['capabilities'].get('hand_tracking'):
                session['interactions'].append({
                    'type': 'hand_gesture',
                    'enabled': True,
                    'gestures': ['tap', 'pinch', 'grab', 'rotate']
                })
            
            if device['capabilities'].get('eye_tracking'):
                session['interactions'].append({
                    'type': 'eye_gaze',
                    'enabled': True,
                    'dwell_time': config.get('gaze_dwell_time', 1.5)
                })
            
            if device['capabilities'].get('voice_commands'):
                session['interactions'].append({
                    'type': 'voice',
                    'enabled': True,
                    'commands': config.get('voice_commands', ['play', 'pause', 'rotate', 'scale'])
                })
            
            session['ar_config'] = ar_config
            session['status'] = 'active'
            
            logger.info(f"AR headset projection started", 
                       projection_id=projection_id,
                       device=device['name'])
            
        except Exception as e:
            logger.error(f"AR headset projection failed", projection_id=projection_id, error=str(e))
            session['status'] = 'failed'
            session['error'] = str(e)
    
    async def _project_pyramid(self, projection_id: str, hologram_id: str, device: Dict[str, Any], config: Dict[str, Any]):
        """Project on pyramid holographic display"""
        try:
            session = self.active_projections[projection_id]
            
            # Configure pyramid display
            pyramid_config = {
                'content_path': f"{hologram_id}_pyramid.mp4",
                'rotation_speed': config.get('rotation_speed', 30),  # RPM
                'loop': config.get('loop', True),
                'audio_enabled': config.get('audio', False),
                'brightness': config.get('brightness', 0.8)
            }
            
            # Pyramid displays show content from 4 sides
            session['viewing_angles'] = [0, 90, 180, 270]
            session['pyramid_config'] = pyramid_config
            session['status'] = 'active'
            
            logger.info(f"Pyramid display projection started", projection_id=projection_id)
            
        except Exception as e:
            logger.error(f"Pyramid projection failed", projection_id=projection_id, error=str(e))
            session['status'] = 'failed'
            session['error'] = str(e)
    
    async def _project_pepper_ghost(self, projection_id: str, hologram_id: str, device: Dict[str, Any], config: Dict[str, Any]):
        """Project using Pepper's Ghost technique"""
        try:
            session = self.active_projections[projection_id]
            
            # Configure Pepper's Ghost projection
            pepper_config = {
                'video_path': f"{hologram_id}_pepper.mp4",
                'projection_angle': config.get('angle', 45),
                'screen_brightness': config.get('brightness', 1.0),
                'background': config.get('background', 'black'),
                'life_size': config.get('life_size', True),
                'interactive_mode': config.get('interactive', False)
            }
            
            # Calculate optimal projection parameters
            stage_size = device['capabilities']['stage_size']
            pepper_config['projection_params'] = {
                'distance': device['capabilities']['projection_distance'],
                'screen_size': self._calculate_screen_size(stage_size, pepper_config['projection_angle']),
                'brightness_lumens': device['capabilities']['brightness']
            }
            
            session['pepper_config'] = pepper_config
            session['status'] = 'active'
            
            logger.info(f"Pepper's Ghost projection started", projection_id=projection_id)
            
        except Exception as e:
            logger.error(f"Pepper's Ghost projection failed", projection_id=projection_id, error=str(e))
            session['status'] = 'failed'
            session['error'] = str(e)
    
    def _calculate_screen_size(self, stage_size: str, angle: float) -> str:
        """Calculate optimal screen size for Pepper's Ghost"""
        # Parse stage size (e.g., "2x2m")
        dimensions = stage_size.split('x')
        width = float(dimensions[0].replace('m', ''))
        
        # Calculate screen size based on angle
        import math
        screen_width = width / math.cos(math.radians(angle))
        return f"{screen_width:.1f}x{screen_width:.1f}m"
    
    async def update_projection(self, projection_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update active projection parameters"""
        if projection_id not in self.active_projections:
            raise ValueError(f"Projection '{projection_id}' not found")
        
        session = self.active_projections[projection_id]
        
        # Update position/rotation/scale for AR
        if 'position' in updates:
            session['ar_config']['position'] = updates['position']
        if 'rotation' in updates:
            session['ar_config']['rotation'] = updates['rotation']
        if 'scale' in updates:
            session['ar_config']['scale'] = updates['scale']
        
        # Update display parameters
        if 'brightness' in updates:
            if 'pyramid_config' in session:
                session['pyramid_config']['brightness'] = updates['brightness']
            elif 'pepper_config' in session:
                session['pepper_config']['screen_brightness'] = updates['brightness']
        
        return {
            'projection_id': projection_id,
            'status': 'updated',
            'updates': updates
        }
    
    async def add_spatial_anchor(self, projection_id: str, anchor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add spatial anchor for AR projection"""
        if projection_id not in self.active_projections:
            raise ValueError(f"Projection '{projection_id}' not found")
        
        session = self.active_projections[projection_id]
        
        anchor = {
            'id': f"anchor_{datetime.utcnow().timestamp()}",
            'position': anchor_data['position'],
            'rotation': anchor_data.get('rotation', [0, 0, 0]),
            'created_at': datetime.utcnow(),
            'persistent': anchor_data.get('persistent', True),
            'metadata': anchor_data.get('metadata', {})
        }
        
        session['anchors'].append(anchor)
        
        return {
            'anchor_id': anchor['id'],
            'status': 'created'
        }
    
    async def handle_interaction(self, projection_id: str, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user interaction with projection"""
        if projection_id not in self.active_projections:
            raise ValueError(f"Projection '{projection_id}' not found")
        
        session = self.active_projections[projection_id]
        interaction_type = interaction.get('type')
        
        # Process interaction based on type
        response = {
            'projection_id': projection_id,
            'interaction_type': interaction_type,
            'timestamp': datetime.utcnow()
        }
        
        if interaction_type == 'hand_gesture':
            gesture = interaction.get('gesture')
            response['action'] = self._process_gesture(gesture, interaction.get('params'))
        
        elif interaction_type == 'eye_gaze':
            target = interaction.get('target')
            dwell_time = interaction.get('dwell_time')
            response['action'] = f"Selected {target} after {dwell_time}s gaze"
        
        elif interaction_type == 'voice_command':
            command = interaction.get('command')
            response['action'] = self._process_voice_command(command, interaction.get('params'))
        
        # Log interaction
        session['interactions'].append({
            'timestamp': datetime.utcnow(),
            'type': interaction_type,
            'data': interaction,
            'response': response
        })
        
        return response
    
    def _process_gesture(self, gesture: str, params: Dict[str, Any]) -> str:
        """Process hand gesture"""
        gesture_actions = {
            'tap': 'select',
            'pinch': 'grab',
            'grab': 'move',
            'rotate': 'rotate',
            'spread': 'scale_up',
            'pinch_close': 'scale_down'
        }
        return gesture_actions.get(gesture, 'unknown')
    
    def _process_voice_command(self, command: str, params: Dict[str, Any]) -> str:
        """Process voice command"""
        command_actions = {
            'play': 'start_animation',
            'pause': 'pause_animation',
            'rotate': 'rotate_hologram',
            'scale': 'scale_hologram',
            'reset': 'reset_position',
            'hide': 'hide_hologram',
            'show': 'show_hologram'
        }
        return command_actions.get(command.lower(), 'unknown_command')
    
    async def stop_projection(self, projection_id: str) -> Dict[str, Any]:
        """Stop active projection"""
        if projection_id not in self.active_projections:
            raise ValueError(f"Projection '{projection_id}' not found")
        
        session = self.active_projections[projection_id]
        session['status'] = 'stopped'
        session['end_time'] = datetime.utcnow()
        
        # Clean up spatial anchors if AR
        if session.get('anchors'):
            for anchor in session['anchors']:
                if not anchor.get('persistent'):
                    logger.info(f"Removing non-persistent anchor", anchor_id=anchor['id'])
        
        return {
            'projection_id': projection_id,
            'status': 'stopped',
            'duration': (session['end_time'] - session['start_time']).total_seconds()
        }
    
    async def get_projection_status(self, projection_id: str) -> Dict[str, Any]:
        """Get status of projection session"""
        if projection_id not in self.active_projections:
            raise ValueError(f"Projection '{projection_id}' not found")
        
        session = self.active_projections[projection_id]
        return {
            'projection_id': projection_id,
            'status': session['status'],
            'device': session['device'],
            'start_time': session['start_time'],
            'anchors': len(session.get('anchors', [])),
            'interactions': len(session.get('interactions', []))
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of projection service"""
        return {
            'status': 'healthy' if self.initialized else 'unhealthy',
            'available_devices': len(self.projection_devices),
            'active_projections': len(self.active_projections),
            'devices': {name: dev['status'] for name, dev in self.projection_devices.items()}
        }