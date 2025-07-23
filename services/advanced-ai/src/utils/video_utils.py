"""
Video Processing Utilities

Helper functions for video analysis and processing.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import ffmpeg
import structlog


logger = structlog.get_logger()


class VideoProcessor:
    """Video processing utilities"""
    
    async def get_video_info(self, video_path: str) -> Dict:
        """Get video information"""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            # Extract info
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            fps = eval(video_stream['r_frame_rate'])
            duration = float(video_stream.get('duration', 0))
            
            # If duration not in stream, check format
            if duration == 0 and 'format' in probe:
                duration = float(probe['format'].get('duration', 0))
            
            # Get frame count
            frame_count = int(video_stream.get('nb_frames', 0))
            if frame_count == 0 and duration > 0 and fps > 0:
                frame_count = int(duration * fps)
            
            return {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration,
                'frame_count': frame_count,
                'codec': video_stream.get('codec_name', 'unknown'),
                'bitrate': int(video_stream.get('bit_rate', 0)),
                'has_audio': any(s['codec_type'] == 'audio' for s in probe['streams'])
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            # Fallback to OpenCV
            return self._get_video_info_opencv(video_path)
    
    def _get_video_info_opencv(self, video_path: str) -> Dict:
        """Get video info using OpenCV as fallback"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration,
            'frame_count': frame_count,
            'codec': 'unknown',
            'bitrate': 0,
            'has_audio': False  # Cannot determine with OpenCV
        }
    
    async def extract_frames(
        self,
        video_path: str,
        timestamps: List[float],
        output_dir: str
    ) -> List[str]:
        """Extract frames at specific timestamps"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        extracted_paths = []
        
        for i, timestamp in enumerate(timestamps):
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            if ret:
                output_path = f"{output_dir}/frame_{i}_{timestamp:.2f}.jpg"
                cv2.imwrite(output_path, frame)
                extracted_paths.append(output_path)
        
        cap.release()
        return extracted_paths
    
    async def calculate_frame_similarity(
        self,
        frame1: np.ndarray,
        frame2: np.ndarray
    ) -> float:
        """Calculate similarity between two frames"""
        # Resize to same size if needed
        if frame1.shape != frame2.shape:
            frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Calculate structural similarity
        score = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)[0][0]
        
        return float(score)
    
    async def detect_black_frames(
        self,
        video_path: str,
        threshold: int = 10
    ) -> List[Tuple[float, float]]:
        """Detect black frame segments"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        black_segments = []
        in_black = False
        start_time = None
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Check if frame is black
            mean_value = np.mean(frame)
            
            if mean_value < threshold:
                if not in_black:
                    in_black = True
                    start_time = frame_idx / fps
            else:
                if in_black:
                    end_time = frame_idx / fps
                    if end_time - start_time > 0.5:  # Minimum duration
                        black_segments.append((start_time, end_time))
                    in_black = False
            
            frame_idx += 1
        
        cap.release()
        return black_segments
    
    async def calculate_motion_vector(
        self,
        prev_frame: np.ndarray,
        curr_frame: np.ndarray
    ) -> np.ndarray:
        """Calculate motion vectors between frames"""
        # Convert to grayscale
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        # Calculate magnitude
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        return magnitude
    
    async def extract_audio(
        self,
        video_path: str,
        output_path: str
    ) -> str:
        """Extract audio from video"""
        try:
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, output_path, acodec='pcm_s16le', ac=1, ar='16k')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            return output_path
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            raise
    
    def calculate_sharpness(self, frame: np.ndarray) -> float:
        """Calculate frame sharpness using Laplacian variance"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()
    
    def calculate_brightness(self, frame: np.ndarray) -> float:
        """Calculate average brightness"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return np.mean(hsv[:, :, 2])
    
    def calculate_contrast(self, frame: np.ndarray) -> float:
        """Calculate frame contrast"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return gray.std()
    
    def detect_blur(self, frame: np.ndarray, threshold: float = 100.0) -> bool:
        """Detect if frame is blurry"""
        sharpness = self.calculate_sharpness(frame)
        return sharpness < threshold