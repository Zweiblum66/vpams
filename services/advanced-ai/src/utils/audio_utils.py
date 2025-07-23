"""
Audio Processing Utilities

Helper functions for audio analysis and processing.
"""

import librosa
import numpy as np
from typing import Dict, List, Tuple, Optional
import structlog
import tempfile
import subprocess


logger = structlog.get_logger()


class AudioProcessor:
    """Audio processing utilities for auto-tagging"""
    
    def __init__(self):
        self.sample_rate = 22050
        self.supported_formats = ['.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a']
    
    def extract_audio_features(self, audio_path: str) -> Dict:
        """Extract comprehensive audio features"""
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            features = {}
            
            # Basic properties
            features['duration'] = float(librosa.get_duration(y=y, sr=sr))
            features['sample_rate'] = sr
            features['channels'] = 1  # librosa loads as mono by default
            
            # Spectral features
            features.update(self._extract_spectral_features(y, sr))
            
            # Temporal features
            features.update(self._extract_temporal_features(y, sr))
            
            # Harmonic features
            features.update(self._extract_harmonic_features(y, sr))
            
            # Rhythm features
            features.update(self._extract_rhythm_features(y, sr))
            
            return features
            
        except Exception as e:
            logger.error("Error extracting audio features", error=str(e))
            return {}
    
    def _extract_spectral_features(self, y: np.ndarray, sr: int) -> Dict:
        """Extract spectral features"""
        features = {}
        
        try:
            # Spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            features['spectral_centroid_mean'] = float(np.mean(spectral_centroids))
            features['spectral_centroid_std'] = float(np.std(spectral_centroids))
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            features['spectral_rolloff_mean'] = float(np.mean(spectral_rolloff))
            features['spectral_rolloff_std'] = float(np.std(spectral_rolloff))
            
            # Spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
            features['spectral_bandwidth_mean'] = float(np.mean(spectral_bandwidth))
            features['spectral_bandwidth_std'] = float(np.std(spectral_bandwidth))
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            features['zero_crossing_rate_mean'] = float(np.mean(zcr))
            features['zero_crossing_rate_std'] = float(np.std(zcr))
            
            # MFCCs
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            for i in range(13):
                features[f'mfcc_{i}_mean'] = float(np.mean(mfccs[i]))
                features[f'mfcc_{i}_std'] = float(np.std(mfccs[i]))
            
        except Exception as e:
            logger.error("Error extracting spectral features", error=str(e))
        
        return features
    
    def _extract_temporal_features(self, y: np.ndarray, sr: int) -> Dict:
        """Extract temporal features"""
        features = {}
        
        try:
            # RMS energy
            rms = librosa.feature.rms(y=y)[0]
            features['rms_mean'] = float(np.mean(rms))
            features['rms_std'] = float(np.std(rms))
            
            # Energy
            features['energy'] = float(np.sum(y**2))
            
            # Dynamic range
            features['dynamic_range'] = float(np.max(y) - np.min(y))
            
            # Silence ratio (percentage of frames below threshold)
            silence_threshold = 0.01
            silence_frames = np.sum(rms < silence_threshold)
            features['silence_ratio'] = float(silence_frames / len(rms))
            
        except Exception as e:
            logger.error("Error extracting temporal features", error=str(e))
        
        return features
    
    def _extract_harmonic_features(self, y: np.ndarray, sr: int) -> Dict:
        """Extract harmonic features"""
        features = {}
        
        try:
            # Harmonic-percussive separation
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            # Harmonic ratio
            harmonic_energy = np.sum(y_harmonic**2)
            percussive_energy = np.sum(y_percussive**2)
            total_energy = harmonic_energy + percussive_energy
            
            if total_energy > 0:
                features['harmonic_ratio'] = float(harmonic_energy / total_energy)
                features['percussive_ratio'] = float(percussive_energy / total_energy)
            else:
                features['harmonic_ratio'] = 0.0
                features['percussive_ratio'] = 0.0
            
            # Pitch estimation
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr, threshold=0.1)
            
            # Extract pitch statistics
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                features['pitch_mean'] = float(np.mean(pitch_values))
                features['pitch_std'] = float(np.std(pitch_values))
                features['pitch_min'] = float(np.min(pitch_values))
                features['pitch_max'] = float(np.max(pitch_values))
            else:
                features['pitch_mean'] = 0.0
                features['pitch_std'] = 0.0
                features['pitch_min'] = 0.0
                features['pitch_max'] = 0.0
            
        except Exception as e:
            logger.error("Error extracting harmonic features", error=str(e))
        
        return features
    
    def _extract_rhythm_features(self, y: np.ndarray, sr: int) -> Dict:
        """Extract rhythm and tempo features"""
        features = {}
        
        try:
            # Tempo estimation
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            features['tempo'] = float(tempo)
            features['beat_count'] = len(beats)
            
            # Beat consistency
            if len(beats) > 1:
                beat_intervals = np.diff(beats)
                features['beat_consistency'] = float(1.0 / (1.0 + np.std(beat_intervals)))
            else:
                features['beat_consistency'] = 0.0
            
            # Onset detection
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.times_like(onset_frames, sr=sr)
            features['onset_rate'] = float(len(onset_frames) / librosa.get_duration(y=y, sr=sr))
            
        except Exception as e:
            logger.error("Error extracting rhythm features", error=str(e))
        
        return features
    
    def classify_audio_content(self, audio_path: str) -> Dict:
        """Classify audio content type"""
        try:
            features = self.extract_audio_features(audio_path)
            
            classification = {
                'speech_probability': 0.0,
                'music_probability': 0.0,
                'noise_probability': 0.0,
                'silence_probability': 0.0
            }
            
            # Simple rule-based classification
            if features:
                # Speech indicators
                if (features.get('zero_crossing_rate_mean', 0) > 0.1 and
                    features.get('spectral_centroid_mean', 0) > 1000 and
                    features.get('spectral_centroid_mean', 0) < 4000):
                    classification['speech_probability'] = 0.7
                
                # Music indicators
                if (features.get('harmonic_ratio', 0) > 0.6 and
                    features.get('tempo', 0) > 60 and
                    features.get('beat_consistency', 0) > 0.5):
                    classification['music_probability'] = 0.8
                
                # Silence indicators
                if features.get('silence_ratio', 0) > 0.8:
                    classification['silence_probability'] = 0.9
                
                # Noise indicators
                if (features.get('spectral_bandwidth_mean', 0) > 2000 and
                    features.get('zero_crossing_rate_mean', 0) > 0.2):
                    classification['noise_probability'] = 0.6
            
            # Normalize probabilities
            total_prob = sum(classification.values())
            if total_prob > 0:
                for key in classification:
                    classification[key] /= total_prob
            
            return classification
            
        except Exception as e:
            logger.error("Error classifying audio content", error=str(e))
            return {}
    
    def detect_speech_segments(self, audio_path: str) -> List[Dict]:
        """Detect speech segments in audio"""
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Simple voice activity detection based on energy and spectral features
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = int(0.01 * sr)     # 10ms hop
            
            # Calculate features per frame
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            zcr = librosa.feature.zero_crossing_rate(y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Thresholds for speech detection
            energy_threshold = np.mean(rms) * 0.5
            zcr_threshold = 0.1
            
            # Detect speech frames
            speech_frames = (rms > energy_threshold) & (zcr > zcr_threshold)
            
            # Convert to time segments
            frame_times = librosa.times_like(speech_frames, sr=sr, hop_length=hop_length)
            
            segments = []
            in_speech = False
            start_time = 0
            
            for i, is_speech in enumerate(speech_frames):
                if is_speech and not in_speech:
                    # Start of speech segment
                    start_time = frame_times[i]
                    in_speech = True
                elif not is_speech and in_speech:
                    # End of speech segment
                    end_time = frame_times[i]
                    if end_time - start_time > 0.5:  # Minimum 0.5 second segments
                        segments.append({
                            'start_time': float(start_time),
                            'end_time': float(end_time),
                            'duration': float(end_time - start_time),
                            'confidence': 0.7
                        })
                    in_speech = False
            
            return segments
            
        except Exception as e:
            logger.error("Error detecting speech segments", error=str(e))
            return []
    
    def analyze_music_properties(self, audio_path: str) -> Dict:
        """Analyze musical properties"""
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            properties = {}
            
            # Key and mode estimation
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            
            # Simple key estimation (major keys)
            key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            estimated_key = key_names[np.argmax(chroma_mean)]
            properties['estimated_key'] = estimated_key
            
            # Tempo and rhythm
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            properties['tempo'] = float(tempo)
            
            # Tempo category
            if tempo < 60:
                properties['tempo_category'] = 'very_slow'
            elif tempo < 90:
                properties['tempo_category'] = 'slow'
            elif tempo < 120:
                properties['tempo_category'] = 'moderate'
            elif tempo < 160:
                properties['tempo_category'] = 'fast'
            else:
                properties['tempo_category'] = 'very_fast'
            
            # Rhythm stability
            if len(beats) > 1:
                beat_intervals = np.diff(beats)
                rhythm_stability = 1.0 / (1.0 + np.std(beat_intervals))
                properties['rhythm_stability'] = float(rhythm_stability)
            
            # Dynamic range (loudness variation)
            rms = librosa.feature.rms(y=y)[0]
            properties['dynamic_range'] = float(np.max(rms) - np.min(rms))
            
            return properties
            
        except Exception as e:
            logger.error("Error analyzing music properties", error=str(e))
            return {}
    
    def extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """Extract audio track from video file"""
        try:
            # Create temporary audio file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            # Use ffmpeg to extract audio
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '22050',  # Sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                temp_audio_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return temp_audio_path
            else:
                logger.error("ffmpeg failed", error=result.stderr)
                return None
                
        except Exception as e:
            logger.error("Error extracting audio from video", error=str(e))
            return None
    
    def detect_audio_events(self, audio_path: str) -> List[Dict]:
        """Detect audio events (applause, laughter, etc.)"""
        try:
            features = self.extract_audio_features(audio_path)
            events = []
            
            # Simple rule-based event detection
            if features:
                # High energy bursts (could be applause)
                if (features.get('rms_mean', 0) > 0.1 and
                    features.get('spectral_bandwidth_mean', 0) > 1000):
                    events.append({
                        'event_type': 'high_energy',
                        'confidence': 0.6,
                        'description': 'High energy audio event (applause, crowd noise)'
                    })
                
                # Periodic patterns (could be music)
                if (features.get('beat_consistency', 0) > 0.7 and
                    features.get('tempo', 0) > 60):
                    events.append({
                        'event_type': 'rhythmic_pattern',
                        'confidence': 0.8,
                        'description': 'Rhythmic pattern detected (music, drumming)'
                    })
            
            return events
            
        except Exception as e:
            logger.error("Error detecting audio events", error=str(e))
            return []
    
    def calculate_audio_similarity(self, audio1_path: str, audio2_path: str) -> float:
        """Calculate similarity between two audio files"""
        try:
            # Extract features from both files
            features1 = self.extract_audio_features(audio1_path)
            features2 = self.extract_audio_features(audio2_path)
            
            if not features1 or not features2:
                return 0.0
            
            # Compare key features
            similarity_scores = []
            
            key_features = [
                'spectral_centroid_mean', 'spectral_rolloff_mean',
                'tempo', 'harmonic_ratio', 'zero_crossing_rate_mean'
            ]
            
            for feature in key_features:
                if feature in features1 and feature in features2:
                    val1 = features1[feature]
                    val2 = features2[feature]
                    
                    # Normalize difference
                    max_val = max(abs(val1), abs(val2))
                    if max_val > 0:
                        diff = abs(val1 - val2) / max_val
                        similarity = 1.0 - min(diff, 1.0)
                        similarity_scores.append(similarity)
            
            if similarity_scores:
                return float(np.mean(similarity_scores))
            else:
                return 0.0
                
        except Exception as e:
            logger.error("Error calculating audio similarity", error=str(e))
            return 0.0