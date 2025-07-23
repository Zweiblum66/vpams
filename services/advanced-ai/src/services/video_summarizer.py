"""
Video Summarization Service

Generates intelligent video summaries using multiple techniques:
- Scene detection and keyframe extraction
- Visual importance scoring
- Audio transcript analysis
- Motion-based selection
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis import Redis
import structlog
import numpy as np
import cv2
from moviepy.editor import VideoFileClip, concatenate_videoclips
from scenedetect import detect, ContentDetector, ThresholdDetector
import torch
from transformers import pipeline
import whisper

from ..core.config import settings
from ..models.schemas import (
    VideoSummary, SummarySegment, SummaryType, KeyFrame,
    TranscriptHighlight, ModelType
)
from ..db.models import VideoSummaryModel, SummarySegmentModel
from ..utils.metrics import ai_metrics
from ..utils.video_utils import VideoProcessor


logger = structlog.get_logger()


class VideoSummarizer:
    """Generates intelligent video summaries"""
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.video_processor = VideoProcessor()
        self.whisper_model = None
        self.summarization_pipeline = None
        self.importance_model = None
        
    async def initialize(self):
        """Initialize video summarizer"""
        logger.info("Initializing video summarizer")
        
        # Load models
        await self._load_models()
        
    async def summarize_video(
        self,
        asset_id: str,
        video_path: str,
        target_duration_percent: int = 10,
        summary_type: SummaryType = SummaryType.HIGHLIGHTS,
        options: Optional[Dict] = None
    ) -> VideoSummary:
        """Generate video summary"""
        logger.info(
            "Generating video summary",
            asset_id=asset_id,
            target_percent=target_duration_percent,
            summary_type=summary_type
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Get video info
            video_info = await self.video_processor.get_video_info(video_path)
            duration = video_info['duration']
            fps = video_info['fps']
            
            # Target duration in seconds
            target_duration = duration * (target_duration_percent / 100)
            
            # Generate summary based on type
            if summary_type == SummaryType.HIGHLIGHTS:
                segments = await self._generate_highlights_summary(
                    video_path, target_duration, fps, options
                )
            elif summary_type == SummaryType.SCENES:
                segments = await self._generate_scene_based_summary(
                    video_path, target_duration, fps, options
                )
            elif summary_type == SummaryType.TRANSCRIPT:
                segments = await self._generate_transcript_based_summary(
                    video_path, target_duration, fps, options
                )
            elif summary_type == SummaryType.ACTION:
                segments = await self._generate_action_based_summary(
                    video_path, target_duration, fps, options
                )
            else:  # INTELLIGENT - combines all methods
                segments = await self._generate_intelligent_summary(
                    video_path, target_duration, fps, options
                )
            
            # Extract keyframes
            keyframes = await self._extract_keyframes(video_path, segments, fps)
            
            # Get transcript highlights if available
            transcript_highlights = await self._get_transcript_highlights(
                video_path, segments
            )
            
            # Calculate actual duration
            actual_duration = sum(s.duration for s in segments)
            
            # Create summary object
            summary = VideoSummary(
                asset_id=asset_id,
                original_duration=duration,
                summary_duration=actual_duration,
                target_duration_percent=target_duration_percent,
                actual_duration_percent=(actual_duration / duration) * 100,
                summary_type=summary_type,
                segments=segments,
                keyframes=keyframes,
                transcript_highlights=transcript_highlights,
                confidence_score=self._calculate_confidence(segments),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                model_used=ModelType.CUSTOM
            )
            
            # Store summary
            await self._store_summary(summary)
            
            # Update metrics
            ai_metrics.video_summaries_generated.labels(
                type=summary_type.value
            ).inc()
            ai_metrics.video_processing_time.labels(
                operation="summarize"
            ).observe(summary.processing_time)
            
            return summary
            
        except Exception as e:
            logger.error("Error generating video summary", error=str(e))
            raise
    
    async def _generate_highlights_summary(
        self,
        video_path: str,
        target_duration: float,
        fps: float,
        options: Optional[Dict] = None
    ) -> List[SummarySegment]:
        """Generate highlights-based summary"""
        logger.info("Generating highlights summary")
        
        # Detect scenes
        scenes = await self._detect_scenes(video_path)
        
        # Score each scene for importance
        scored_scenes = []
        for scene in scenes:
            score = await self._score_scene_importance(
                video_path, scene, fps
            )
            scored_scenes.append((scene, score))
        
        # Sort by score
        scored_scenes.sort(key=lambda x: x[1], reverse=True)
        
        # Select top scenes up to target duration
        selected_segments = []
        current_duration = 0
        
        for (start_time, end_time), score in scored_scenes:
            scene_duration = end_time - start_time
            
            if current_duration + scene_duration <= target_duration * 1.2:  # Allow 20% over
                segment = SummarySegment(
                    start_time=start_time,
                    end_time=end_time,
                    duration=scene_duration,
                    importance_score=score,
                    scene_type="highlight",
                    description=f"Important scene (score: {score:.2f})"
                )
                selected_segments.append(segment)
                current_duration += scene_duration
                
                if current_duration >= target_duration:
                    break
        
        # Sort by time
        selected_segments.sort(key=lambda s: s.start_time)
        
        return selected_segments
    
    async def _generate_scene_based_summary(
        self,
        video_path: str,
        target_duration: float,
        fps: float,
        options: Optional[Dict] = None
    ) -> List[SummarySegment]:
        """Generate scene-based summary"""
        logger.info("Generating scene-based summary")
        
        # Detect scenes
        scenes = await self._detect_scenes(video_path)
        
        # Calculate how many scenes to include
        total_scenes = len(scenes)
        avg_scene_duration = sum(e - s for s, e in scenes) / total_scenes
        target_scenes = int(target_duration / avg_scene_duration)
        
        # Sample scenes evenly
        if target_scenes >= total_scenes:
            selected_scenes = scenes
        else:
            step = total_scenes / target_scenes
            indices = [int(i * step) for i in range(target_scenes)]
            selected_scenes = [scenes[i] for i in indices]
        
        # Convert to segments
        segments = []
        for start_time, end_time in selected_scenes:
            segment = SummarySegment(
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                importance_score=0.7,  # Default score
                scene_type="scene_change",
                description="Scene transition"
            )
            segments.append(segment)
        
        return segments
    
    async def _generate_transcript_based_summary(
        self,
        video_path: str,
        target_duration: float,
        fps: float,
        options: Optional[Dict] = None
    ) -> List[SummarySegment]:
        """Generate transcript-based summary"""
        logger.info("Generating transcript-based summary")
        
        # Extract transcript
        transcript = await self._extract_transcript(video_path)
        
        if not transcript:
            # Fallback to scene-based
            return await self._generate_scene_based_summary(
                video_path, target_duration, fps, options
            )
        
        # Identify important segments from transcript
        important_segments = await self._identify_important_transcript_segments(
            transcript, target_duration
        )
        
        # Convert to video segments
        segments = []
        for text_segment in important_segments:
            segment = SummarySegment(
                start_time=text_segment['start'],
                end_time=text_segment['end'],
                duration=text_segment['end'] - text_segment['start'],
                importance_score=text_segment['score'],
                scene_type="dialogue",
                description=text_segment['text'][:100]
            )
            segments.append(segment)
        
        return segments
    
    async def _generate_action_based_summary(
        self,
        video_path: str,
        target_duration: float,
        fps: float,
        options: Optional[Dict] = None
    ) -> List[SummarySegment]:
        """Generate action-based summary focusing on motion"""
        logger.info("Generating action-based summary")
        
        # Analyze motion in video
        motion_segments = await self._detect_high_motion_segments(
            video_path, fps
        )
        
        # Score and filter segments
        scored_segments = []
        for segment in motion_segments:
            score = segment['motion_score']
            duration = segment['end'] - segment['start']
            
            if duration > 0.5:  # Minimum segment duration
                scored_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'duration': duration,
                    'score': score
                })
        
        # Sort by score
        scored_segments.sort(key=lambda x: x['score'], reverse=True)
        
        # Select top segments
        selected_segments = []
        current_duration = 0
        
        for segment in scored_segments:
            if current_duration + segment['duration'] <= target_duration * 1.2:
                summary_segment = SummarySegment(
                    start_time=segment['start'],
                    end_time=segment['end'],
                    duration=segment['duration'],
                    importance_score=segment['score'],
                    scene_type="action",
                    description=f"High motion segment (score: {segment['score']:.2f})"
                )
                selected_segments.append(summary_segment)
                current_duration += segment['duration']
                
                if current_duration >= target_duration:
                    break
        
        # Sort by time
        selected_segments.sort(key=lambda s: s.start_time)
        
        return selected_segments
    
    async def _generate_intelligent_summary(
        self,
        video_path: str,
        target_duration: float,
        fps: float,
        options: Optional[Dict] = None
    ) -> List[SummarySegment]:
        """Generate intelligent summary combining multiple methods"""
        logger.info("Generating intelligent summary")
        
        # Get segments from different methods
        scene_segments = await self._detect_scenes(video_path)
        motion_data = await self._detect_high_motion_segments(video_path, fps)
        transcript = await self._extract_transcript(video_path)
        
        # Score all segments using multiple factors
        all_segments = []
        
        # Process scene segments
        for start, end in scene_segments:
            # Calculate composite score
            visual_score = await self._score_scene_importance(
                video_path, (start, end), fps
            )
            
            # Check motion in this segment
            motion_score = self._get_motion_score_for_segment(
                motion_data, start, end
            )
            
            # Check transcript importance
            transcript_score = 0.5  # Default
            if transcript:
                transcript_score = self._get_transcript_score_for_segment(
                    transcript, start, end
                )
            
            # Composite score
            composite_score = (
                visual_score * 0.4 +
                motion_score * 0.3 +
                transcript_score * 0.3
            )
            
            all_segments.append({
                'start': start,
                'end': end,
                'duration': end - start,
                'score': composite_score,
                'visual_score': visual_score,
                'motion_score': motion_score,
                'transcript_score': transcript_score
            })
        
        # Sort by composite score
        all_segments.sort(key=lambda x: x['score'], reverse=True)
        
        # Select best segments
        selected_segments = []
        current_duration = 0
        
        for segment in all_segments:
            if current_duration + segment['duration'] <= target_duration * 1.1:
                # Determine primary type
                scores = {
                    'visual': segment['visual_score'],
                    'action': segment['motion_score'],
                    'dialogue': segment['transcript_score']
                }
                scene_type = max(scores, key=scores.get)
                
                summary_segment = SummarySegment(
                    start_time=segment['start'],
                    end_time=segment['end'],
                    duration=segment['duration'],
                    importance_score=segment['score'],
                    scene_type=scene_type,
                    description=f"Intelligent selection (score: {segment['score']:.2f})"
                )
                selected_segments.append(summary_segment)
                current_duration += segment['duration']
                
                if current_duration >= target_duration:
                    break
        
        # Sort by time
        selected_segments.sort(key=lambda s: s.start_time)
        
        return selected_segments
    
    async def _detect_scenes(self, video_path: str) -> List[Tuple[float, float]]:
        """Detect scene changes in video"""
        try:
            # Use PySceneDetect
            scene_list = detect(
                video_path,
                ContentDetector(threshold=30.0)
            )
            
            # Convert to seconds
            scenes = []
            for (start_time, end_time) in scene_list:
                scenes.append((
                    start_time.get_seconds(),
                    end_time.get_seconds()
                ))
            
            return scenes
            
        except Exception as e:
            logger.error("Error detecting scenes", error=str(e))
            # Fallback to fixed intervals
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps
            cap.release()
            
            # Create 10-second intervals
            scenes = []
            interval = 10.0
            current = 0
            while current < duration:
                end = min(current + interval, duration)
                scenes.append((current, end))
                current = end
            
            return scenes
    
    async def _score_scene_importance(
        self,
        video_path: str,
        scene: Tuple[float, float],
        fps: float
    ) -> float:
        """Score importance of a scene"""
        start_time, end_time = scene
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        
        # Seek to start
        start_frame = int(start_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Analyze frames in scene
        scores = []
        frame_count = int((end_time - start_time) * fps)
        sample_rate = max(1, frame_count // 10)  # Sample 10 frames
        
        for i in range(0, frame_count, sample_rate):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate frame score based on:
            # 1. Sharpness (Laplacian variance)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 1000, 1.0)
            
            # 2. Color diversity (histogram spread)
            hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist_norm = hist.flatten() / hist.sum()
            color_score = -np.sum(hist_norm * np.log(hist_norm + 1e-10))  # Entropy
            color_score = min(color_score / 3.0, 1.0)  # Normalize
            
            # 3. Face detection (if enabled)
            face_score = 0.5  # Default
            if settings.ENABLE_FACE_DETECTION:
                face_score = await self._detect_faces_score(frame)
            
            # Combine scores
            frame_score = (sharpness_score * 0.3 + color_score * 0.3 + face_score * 0.4)
            scores.append(frame_score)
        
        cap.release()
        
        # Return average score
        return np.mean(scores) if scores else 0.5
    
    async def _detect_high_motion_segments(
        self,
        video_path: str,
        fps: float
    ) -> List[Dict]:
        """Detect segments with high motion"""
        cap = cv2.VideoCapture(video_path)
        
        # Initialize motion detector
        prev_frame = None
        motion_scores = []
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # Calculate frame difference
                diff = cv2.absdiff(prev_frame, gray)
                motion_score = np.mean(diff) / 255.0
                
                motion_scores.append({
                    'frame': frame_idx,
                    'time': frame_idx / fps,
                    'score': motion_score
                })
            
            prev_frame = gray
            frame_idx += 1
        
        cap.release()
        
        # Find high motion segments
        segments = []
        in_segment = False
        segment_start = None
        threshold = 0.1  # Motion threshold
        
        for i, data in enumerate(motion_scores):
            if data['score'] > threshold:
                if not in_segment:
                    in_segment = True
                    segment_start = i
            else:
                if in_segment:
                    # End segment
                    start_time = motion_scores[segment_start]['time']
                    end_time = data['time']
                    avg_score = np.mean([
                        m['score'] for m in motion_scores[segment_start:i]
                    ])
                    
                    segments.append({
                        'start': start_time,
                        'end': end_time,
                        'motion_score': avg_score
                    })
                    
                    in_segment = False
        
        return segments
    
    async def _extract_transcript(self, video_path: str) -> Optional[List[Dict]]:
        """Extract transcript from video using Whisper"""
        try:
            if self.whisper_model is None:
                return None
            
            # Extract audio
            result = self.whisper_model.transcribe(video_path)
            
            # Convert to segments
            segments = []
            for segment in result['segments']:
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                    'confidence': segment.get('confidence', 0.8)
                })
            
            return segments
            
        except Exception as e:
            logger.error("Error extracting transcript", error=str(e))
            return None
    
    async def _identify_important_transcript_segments(
        self,
        transcript: List[Dict],
        target_duration: float
    ) -> List[Dict]:
        """Identify important segments from transcript"""
        if not self.summarization_pipeline:
            # Fallback to simple selection
            return transcript[:int(len(transcript) * 0.3)]
        
        # Combine transcript text
        full_text = " ".join([s['text'] for s in transcript])
        
        # Get summary
        try:
            summary = self.summarization_pipeline(
                full_text,
                max_length=150,
                min_length=50,
                do_sample=False
            )[0]['summary_text']
            
            # Find segments that match summary content
            summary_words = set(summary.lower().split())
            
            scored_segments = []
            for segment in transcript:
                segment_words = set(segment['text'].lower().split())
                overlap = len(summary_words & segment_words)
                score = overlap / len(segment_words) if segment_words else 0
                
                scored_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                    'score': score
                })
            
            # Sort by score
            scored_segments.sort(key=lambda x: x['score'], reverse=True)
            
            # Select top segments
            selected = []
            current_duration = 0
            
            for segment in scored_segments:
                duration = segment['end'] - segment['start']
                if current_duration + duration <= target_duration:
                    selected.append(segment)
                    current_duration += duration
            
            return selected
            
        except Exception as e:
            logger.error("Error in transcript analysis", error=str(e))
            return transcript[:int(len(transcript) * 0.3)]
    
    def _get_motion_score_for_segment(
        self,
        motion_data: List[Dict],
        start_time: float,
        end_time: float
    ) -> float:
        """Get motion score for a time segment"""
        scores = []
        for data in motion_data:
            if data['start'] >= start_time and data['end'] <= end_time:
                scores.append(data['motion_score'])
        
        return np.mean(scores) if scores else 0.3
    
    def _get_transcript_score_for_segment(
        self,
        transcript: List[Dict],
        start_time: float,
        end_time: float
    ) -> float:
        """Get transcript importance score for a segment"""
        relevant_text = []
        
        for segment in transcript:
            # Check overlap
            if segment['start'] < end_time and segment['end'] > start_time:
                relevant_text.append(segment['text'])
        
        if not relevant_text:
            return 0.3
        
        # Simple heuristic: longer text = more important
        total_length = sum(len(text) for text in relevant_text)
        score = min(total_length / 200, 1.0)  # Normalize
        
        return score
    
    async def _extract_keyframes(
        self,
        video_path: str,
        segments: List[SummarySegment],
        fps: float
    ) -> List[KeyFrame]:
        """Extract keyframes from segments"""
        keyframes = []
        
        cap = cv2.VideoCapture(video_path)
        
        for segment in segments[:10]:  # Limit keyframes
            # Get frame from middle of segment
            timestamp = (segment.start_time + segment.end_time) / 2
            frame_number = int(timestamp * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                # Save frame temporarily
                temp_path = Path(tempfile.gettempdir()) / f"keyframe_{segment.segment_id}.jpg"
                cv2.imwrite(str(temp_path), frame)
                
                keyframe = KeyFrame(
                    timestamp=timestamp,
                    frame_number=frame_number,
                    thumbnail_path=str(temp_path),
                    importance_score=segment.importance_score
                )
                keyframes.append(keyframe)
        
        cap.release()
        
        return keyframes
    
    async def _get_transcript_highlights(
        self,
        video_path: str,
        segments: List[SummarySegment]
    ) -> List[TranscriptHighlight]:
        """Get transcript highlights for segments"""
        transcript = await self._extract_transcript(video_path)
        
        if not transcript:
            return []
        
        highlights = []
        
        for segment in segments:
            # Find transcript in this segment
            segment_text = []
            
            for trans in transcript:
                if trans['start'] >= segment.start_time and trans['end'] <= segment.end_time:
                    segment_text.append(trans['text'])
            
            if segment_text:
                highlight = TranscriptHighlight(
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    text=" ".join(segment_text),
                    confidence=0.8
                )
                highlights.append(highlight)
        
        return highlights
    
    def _calculate_confidence(self, segments: List[SummarySegment]) -> float:
        """Calculate overall confidence score"""
        if not segments:
            return 0.0
        
        # Average importance scores
        avg_importance = np.mean([s.importance_score for s in segments])
        
        # Check coverage (how well distributed segments are)
        total_duration = segments[-1].end_time
        coverage_gaps = []
        
        for i in range(1, len(segments)):
            gap = segments[i].start_time - segments[i-1].end_time
            coverage_gaps.append(gap)
        
        avg_gap = np.mean(coverage_gaps) if coverage_gaps else 0
        coverage_score = max(0, 1 - (avg_gap / 30))  # Penalize gaps > 30s
        
        # Combined confidence
        confidence = (avg_importance * 0.7 + coverage_score * 0.3)
        
        return float(confidence)
    
    async def _detect_faces_score(self, frame: np.ndarray) -> float:
        """Detect faces and return score"""
        # Simple face detection using OpenCV
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Score based on number and size of faces
            if len(faces) == 0:
                return 0.3
            
            # Calculate face area ratio
            frame_area = frame.shape[0] * frame.shape[1]
            face_area = sum(w * h for (x, y, w, h) in faces)
            area_ratio = face_area / frame_area
            
            # Score: more faces and larger faces = higher score
            score = min(0.3 + len(faces) * 0.2 + area_ratio * 2, 1.0)
            
            return score
            
        except Exception as e:
            logger.error("Error in face detection", error=str(e))
            return 0.5
    
    async def _store_summary(self, summary: VideoSummary):
        """Store video summary in database"""
        db_summary = VideoSummaryModel(
            summary_id=summary.summary_id,
            asset_id=summary.asset_id,
            original_duration=summary.original_duration,
            summary_duration=summary.summary_duration,
            target_duration_percent=summary.target_duration_percent,
            actual_duration_percent=summary.actual_duration_percent,
            summary_type=summary.summary_type,
            confidence_score=summary.confidence_score,
            processing_time=summary.processing_time,
            model_used=summary.model_used
        )
        
        self.db.add(db_summary)
        
        # Store segments
        for segment in summary.segments:
            db_segment = SummarySegmentModel(
                segment_id=segment.segment_id,
                summary_id=summary.summary_id,
                start_time=segment.start_time,
                end_time=segment.end_time,
                duration=segment.duration,
                importance_score=segment.importance_score,
                scene_type=segment.scene_type,
                description=segment.description
            )
            self.db.add(db_segment)
        
        await self.db.commit()
    
    async def _load_models(self):
        """Load AI models for video analysis"""
        logger.info("Loading video summarization models")
        
        try:
            # Load Whisper for transcription
            if settings.ENABLE_TRANSCRIPTION:
                self.whisper_model = whisper.load_model("base")
            
            # Load summarization model
            if settings.ENABLE_TEXT_SUMMARIZATION:
                self.summarization_pipeline = pipeline(
                    "summarization",
                    model="facebook/bart-large-cnn"
                )
            
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error("Error loading models", error=str(e))
            # Continue without models - will use fallback methods
    
    async def generate_summary_video(
        self,
        video_path: str,
        segments: List[SummarySegment],
        output_path: str
    ) -> str:
        """Generate actual summary video file"""
        logger.info("Generating summary video file")
        
        try:
            # Load video
            video = VideoFileClip(video_path)
            
            # Extract clips for each segment
            clips = []
            for segment in segments:
                clip = video.subclip(segment.start_time, segment.end_time)
                clips.append(clip)
            
            # Concatenate clips
            final_video = concatenate_videoclips(clips)
            
            # Write output
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac'
            )
            
            # Cleanup
            video.close()
            final_video.close()
            
            return output_path
            
        except Exception as e:
            logger.error("Error generating summary video", error=str(e))
            raise