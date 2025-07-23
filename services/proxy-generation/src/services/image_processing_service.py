"""
Image Processing Service for smart cropping, resizing, and other image operations
"""

import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import tempfile
from enum import Enum
import json

from PIL import Image, ImageDraw, ImageOps
import cv2
import numpy as np

from ..core.config import settings
from ..core.exceptions import InvalidMediaError, ProcessingTimeoutError
from ..core.logging import get_logger

logger = get_logger(__name__)


class CropMode(str, Enum):
    """Smart cropping modes"""
    CENTER = "center"          # Simple center crop
    SMART = "smart"           # Content-aware cropping
    FACE = "face"             # Face detection based cropping
    SALIENCY = "saliency"     # Saliency detection based cropping
    ENTROPY = "entropy"       # Entropy-based cropping
    EDGE = "edge"             # Edge detection based cropping


class ImageProcessingService:
    """Service for advanced image processing operations"""
    
    def __init__(self):
        self.face_cascade = None
        self._load_models()
    
    def _load_models(self):
        """Load computer vision models"""
        try:
            # Load Haar Cascade for face detection
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("image_processing_models_loaded")
        except Exception as e:
            logger.warning(f"Failed to load CV models: {e}")
    
    async def smart_crop(
        self,
        input_path: str,
        output_size: Tuple[int, int],
        crop_mode: CropMode = CropMode.SMART,
        quality: int = 95,
        face_padding: float = 1.5,
        custom_focus_point: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        Perform smart cropping on an image
        
        Args:
            input_path: Path to input image
            output_size: Target size (width, height)
            crop_mode: Cropping algorithm to use
            quality: Output JPEG quality (1-100)
            face_padding: Padding factor for face detection (1.0 = no padding)
            custom_focus_point: Custom focus point (x, y) as percentages (0-1)
            
        Returns:
            Dict containing cropped image path and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            if not os.path.exists(input_path):
                raise InvalidMediaError(f"Input file not found: {input_path}")
            
            # Open image
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                original_size = img.size
                
                # Determine crop region based on mode
                if crop_mode == CropMode.CENTER:
                    crop_box = self._get_center_crop(img.size, output_size)
                elif crop_mode == CropMode.FACE:
                    crop_box = await self._get_face_crop(img, output_size, face_padding)
                elif crop_mode == CropMode.SMART:
                    crop_box = await self._get_smart_crop(img, output_size)
                elif crop_mode == CropMode.SALIENCY:
                    crop_box = await self._get_saliency_crop(img, output_size)
                elif crop_mode == CropMode.ENTROPY:
                    crop_box = self._get_entropy_crop(img, output_size)
                elif crop_mode == CropMode.EDGE:
                    crop_box = await self._get_edge_crop(img, output_size)
                else:
                    crop_box = self._get_center_crop(img.size, output_size)
                
                # Apply custom focus point if provided
                if custom_focus_point:
                    crop_box = self._adjust_crop_for_focus(
                        img.size,
                        output_size,
                        crop_box,
                        custom_focus_point
                    )
                
                # Perform crop
                cropped = img.crop(crop_box)
                
                # Resize to exact output size if needed
                if cropped.size != output_size:
                    cropped = cropped.resize(output_size, Image.Resampling.LANCZOS)
                
                # Save cropped image
                with tempfile.NamedTemporaryFile(
                    suffix='.jpg',
                    delete=False
                ) as temp_file:
                    output_path = temp_file.name
                    cropped.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                processing_time = asyncio.get_event_loop().time() - start_time
                
                logger.info(
                    "smart_crop_completed",
                    input_path=input_path,
                    output_size=output_size,
                    crop_mode=crop_mode,
                    crop_box=crop_box,
                    processing_time=processing_time
                )
                
                return {
                    "output_path": output_path,
                    "original_size": original_size,
                    "output_size": output_size,
                    "crop_mode": crop_mode,
                    "crop_box": crop_box,
                    "quality": quality,
                    "processing_time": processing_time
                }
                
        except Exception as e:
            logger.error(
                "smart_crop_failed",
                error=str(e),
                input_path=input_path,
                crop_mode=crop_mode
            )
            raise
    
    def _get_center_crop(
        self,
        img_size: Tuple[int, int],
        output_size: Tuple[int, int]
    ) -> Tuple[int, int, int, int]:
        """Calculate center crop coordinates"""
        img_w, img_h = img_size
        out_w, out_h = output_size
        
        # Calculate aspect ratios
        img_aspect = img_w / img_h
        out_aspect = out_w / out_h
        
        if img_aspect > out_aspect:
            # Image is wider than output
            new_width = int(img_h * out_aspect)
            left = (img_w - new_width) // 2
            return (left, 0, left + new_width, img_h)
        else:
            # Image is taller than output
            new_height = int(img_w / out_aspect)
            top = (img_h - new_height) // 2
            return (0, top, img_w, top + new_height)
    
    async def _get_face_crop(
        self,
        img: Image.Image,
        output_size: Tuple[int, int],
        padding: float = 1.5
    ) -> Tuple[int, int, int, int]:
        """Get crop region based on face detection"""
        # Convert PIL image to OpenCV format
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        if len(faces) == 0:
            # No faces found, fall back to center crop
            return self._get_center_crop(img.size, output_size)
        
        # Find bounding box for all faces
        min_x = min(face[0] for face in faces)
        min_y = min(face[1] for face in faces)
        max_x = max(face[0] + face[2] for face in faces)
        max_y = max(face[1] + face[3] for face in faces)
        
        # Calculate center and size of face region
        face_center_x = (min_x + max_x) // 2
        face_center_y = (min_y + max_y) // 2
        face_width = max_x - min_x
        face_height = max_y - min_y
        
        # Apply padding
        face_width = int(face_width * padding)
        face_height = int(face_height * padding)
        
        # Calculate crop region maintaining aspect ratio
        out_aspect = output_size[0] / output_size[1]
        face_aspect = face_width / face_height
        
        if face_aspect > out_aspect:
            # Face region is wider
            crop_width = face_width
            crop_height = int(crop_width / out_aspect)
        else:
            # Face region is taller
            crop_height = face_height
            crop_width = int(crop_height * out_aspect)
        
        # Center crop on face region
        left = max(0, face_center_x - crop_width // 2)
        top = max(0, face_center_y - crop_height // 2)
        right = min(img.size[0], left + crop_width)
        bottom = min(img.size[1], top + crop_height)
        
        # Adjust if crop goes out of bounds
        if right - left < crop_width:
            if left == 0:
                right = min(img.size[0], crop_width)
            else:
                left = max(0, img.size[0] - crop_width)
        
        if bottom - top < crop_height:
            if top == 0:
                bottom = min(img.size[1], crop_height)
            else:
                top = max(0, img.size[1] - crop_height)
        
        return (left, top, right, bottom)
    
    async def _get_smart_crop(
        self,
        img: Image.Image,
        output_size: Tuple[int, int]
    ) -> Tuple[int, int, int, int]:
        """Get crop using combined smart detection methods"""
        # Try face detection first
        face_crop = await self._get_face_crop(img, output_size)
        
        # Check if face was detected (not center crop)
        center_crop = self._get_center_crop(img.size, output_size)
        if face_crop != center_crop:
            return face_crop
        
        # Try saliency detection
        try:
            saliency_crop = await self._get_saliency_crop(img, output_size)
            if saliency_crop != center_crop:
                return saliency_crop
        except Exception:
            pass
        
        # Fall back to entropy-based crop
        return self._get_entropy_crop(img, output_size)
    
    async def _get_saliency_crop(
        self,
        img: Image.Image,
        output_size: Tuple[int, int]
    ) -> Tuple[int, int, int, int]:
        """Get crop based on saliency detection"""
        # Convert to OpenCV format
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Create saliency detector
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        success, saliency_map = saliency.computeSaliency(cv_img)
        
        if not success:
            return self._get_center_crop(img.size, output_size)
        
        # Convert to uint8
        saliency_map = (saliency_map * 255).astype(np.uint8)
        
        # Threshold to get most salient regions
        _, thresh = cv2.threshold(saliency_map, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return self._get_center_crop(img.size, output_size)
        
        # Find bounding box of all salient regions
        all_points = np.vstack(contours)
        x, y, w, h = cv2.boundingRect(all_points)
        
        # Calculate crop centered on salient region
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Calculate crop dimensions
        out_aspect = output_size[0] / output_size[1]
        img_aspect = img.size[0] / img.size[1]
        
        if img_aspect > out_aspect:
            crop_height = img.size[1]
            crop_width = int(crop_height * out_aspect)
        else:
            crop_width = img.size[0]
            crop_height = int(crop_width / out_aspect)
        
        # Center on salient region
        left = max(0, center_x - crop_width // 2)
        top = max(0, center_y - crop_height // 2)
        right = min(img.size[0], left + crop_width)
        bottom = min(img.size[1], top + crop_height)
        
        # Adjust if necessary
        if right - left < crop_width:
            left = max(0, img.size[0] - crop_width)
            right = img.size[0]
        
        if bottom - top < crop_height:
            top = max(0, img.size[1] - crop_height)
            bottom = img.size[1]
        
        return (left, top, right, bottom)
    
    def _get_entropy_crop(
        self,
        img: Image.Image,
        output_size: Tuple[int, int]
    ) -> Tuple[int, int, int, int]:
        """Get crop based on image entropy (information content)"""
        # Convert to grayscale for entropy calculation
        gray_img = img.convert('L')
        
        # Calculate target crop dimensions
        out_aspect = output_size[0] / output_size[1]
        img_aspect = img.size[0] / img.size[1]
        
        if img_aspect > out_aspect:
            crop_height = img.size[1]
            crop_width = int(crop_height * out_aspect)
        else:
            crop_width = img.size[0]
            crop_height = int(crop_width / out_aspect)
        
        # Calculate entropy for different crop positions
        best_entropy = -1
        best_crop = self._get_center_crop(img.size, output_size)
        
        # Sample positions (avoid checking every pixel for performance)
        step_x = max(1, (img.size[0] - crop_width) // 10)
        step_y = max(1, (img.size[1] - crop_height) // 10)
        
        for x in range(0, img.size[0] - crop_width + 1, step_x):
            for y in range(0, img.size[1] - crop_height + 1, step_y):
                # Crop region
                crop_box = (x, y, x + crop_width, y + crop_height)
                cropped = gray_img.crop(crop_box)
                
                # Calculate entropy
                histogram = cropped.histogram()
                histogram_length = sum(histogram)
                
                entropy = 0
                for h in histogram:
                    if h > 0:
                        probability = h / histogram_length
                        entropy -= probability * np.log2(probability)
                
                if entropy > best_entropy:
                    best_entropy = entropy
                    best_crop = crop_box
        
        return best_crop
    
    async def _get_edge_crop(
        self,
        img: Image.Image,
        output_size: Tuple[int, int]
    ) -> Tuple[int, int, int, int]:
        """Get crop based on edge detection"""
        # Convert to OpenCV format
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find regions with most edges
        kernel_size = 50
        kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
        edge_density = cv2.filter2D(edges.astype(np.float32), -1, kernel)
        
        # Find maximum edge density location
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(edge_density)
        
        # Calculate crop centered on highest edge density
        center_x, center_y = max_loc
        
        # Calculate crop dimensions
        out_aspect = output_size[0] / output_size[1]
        img_aspect = img.size[0] / img.size[1]
        
        if img_aspect > out_aspect:
            crop_height = img.size[1]
            crop_width = int(crop_height * out_aspect)
        else:
            crop_width = img.size[0]
            crop_height = int(crop_width / out_aspect)
        
        # Center on edge region
        left = max(0, center_x - crop_width // 2)
        top = max(0, center_y - crop_height // 2)
        right = min(img.size[0], left + crop_width)
        bottom = min(img.size[1], top + crop_height)
        
        # Adjust if necessary
        if right - left < crop_width:
            if center_x < img.size[0] // 2:
                left = 0
                right = crop_width
            else:
                right = img.size[0]
                left = img.size[0] - crop_width
        
        if bottom - top < crop_height:
            if center_y < img.size[1] // 2:
                top = 0
                bottom = crop_height
            else:
                bottom = img.size[1]
                top = img.size[1] - crop_height
        
        return (left, top, right, bottom)
    
    def _adjust_crop_for_focus(
        self,
        img_size: Tuple[int, int],
        output_size: Tuple[int, int],
        crop_box: Tuple[int, int, int, int],
        focus_point: Tuple[float, float]
    ) -> Tuple[int, int, int, int]:
        """Adjust crop box to include custom focus point"""
        focus_x = int(img_size[0] * focus_point[0])
        focus_y = int(img_size[1] * focus_point[1])
        
        crop_width = crop_box[2] - crop_box[0]
        crop_height = crop_box[3] - crop_box[1]
        
        # Check if focus point is already in crop
        if (crop_box[0] <= focus_x <= crop_box[2] and
            crop_box[1] <= focus_y <= crop_box[3]):
            return crop_box
        
        # Adjust crop to include focus point
        new_left = max(0, min(focus_x - crop_width // 2, img_size[0] - crop_width))
        new_top = max(0, min(focus_y - crop_height // 2, img_size[1] - crop_height))
        
        return (new_left, new_top, new_left + crop_width, new_top + crop_height)
    
    async def batch_smart_crop(
        self,
        images: List[Dict[str, Any]],
        default_output_size: Tuple[int, int],
        default_crop_mode: CropMode = CropMode.SMART,
        parallel_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Process multiple images with smart cropping
        
        Args:
            images: List of image configurations
            default_output_size: Default output size if not specified
            default_crop_mode: Default crop mode if not specified
            parallel_workers: Number of parallel processing workers
            
        Returns:
            List of results for each image
        """
        semaphore = asyncio.Semaphore(parallel_workers)
        
        async def process_image(img_config):
            async with semaphore:
                try:
                    result = await self.smart_crop(
                        input_path=img_config["input_path"],
                        output_size=img_config.get("output_size", default_output_size),
                        crop_mode=img_config.get("crop_mode", default_crop_mode),
                        quality=img_config.get("quality", 95),
                        face_padding=img_config.get("face_padding", 1.5),
                        custom_focus_point=img_config.get("focus_point")
                    )
                    result["input_path"] = img_config["input_path"]
                    result["success"] = True
                    return result
                except Exception as e:
                    logger.error(f"Batch crop failed for {img_config['input_path']}: {e}")
                    return {
                        "input_path": img_config["input_path"],
                        "success": False,
                        "error": str(e)
                    }
        
        tasks = [process_image(img) for img in images]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def add_watermark(
        self,
        input_path: str,
        watermark_path: str,
        position: str = "bottom-right",
        opacity: float = 0.8,
        scale: float = 0.2,
        margin: int = 20,
        output_format: str = "same",
        quality: int = 95
    ) -> Dict[str, Any]:
        """
        Add watermark to an image
        
        Args:
            input_path: Path to input image
            watermark_path: Path to watermark image/logo
            position: Watermark position (top-left, top-right, bottom-left, bottom-right, center)
            opacity: Watermark opacity (0.0-1.0)
            scale: Scale factor for watermark relative to main image (0.0-1.0)
            margin: Margin from edges in pixels
            output_format: Output format ('same', 'jpg', 'png')
            quality: Output quality for JPEG (1-100)
            
        Returns:
            Dict containing watermarked image path and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate inputs
            if not os.path.exists(input_path):
                raise InvalidMediaError(f"Input file not found: {input_path}")
            if not os.path.exists(watermark_path):
                raise InvalidMediaError(f"Watermark file not found: {watermark_path}")
            
            # Open images
            with Image.open(input_path) as base_img:
                with Image.open(watermark_path) as watermark_img:
                    # Convert to RGBA for transparency support
                    if base_img.mode != 'RGBA':
                        base_img = base_img.convert('RGBA')
                    if watermark_img.mode != 'RGBA':
                        watermark_img = watermark_img.convert('RGBA')
                    
                    # Calculate watermark size
                    watermark_width = int(base_img.width * scale)
                    watermark_height = int(watermark_width * watermark_img.height / watermark_img.width)
                    
                    # Resize watermark
                    watermark_img = watermark_img.resize(
                        (watermark_width, watermark_height),
                        Image.Resampling.LANCZOS
                    )
                    
                    # Apply opacity
                    if opacity < 1.0:
                        watermark_img = self._apply_opacity(watermark_img, opacity)
                    
                    # Calculate position
                    x, y = self._calculate_watermark_position(
                        base_img.size,
                        (watermark_width, watermark_height),
                        position,
                        margin
                    )
                    
                    # Create a new image for composition
                    output_img = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
                    output_img.paste(base_img, (0, 0))
                    
                    # Paste watermark
                    output_img.paste(watermark_img, (x, y), watermark_img)
                    
                    # Determine output format
                    if output_format == "same":
                        _, ext = os.path.splitext(input_path)
                        output_format = ext[1:].lower() if ext else "jpg"
                    
                    # Save watermarked image
                    with tempfile.NamedTemporaryFile(
                        suffix=f'.{output_format}',
                        delete=False
                    ) as temp_file:
                        output_path = temp_file.name
                        
                        if output_format in ['jpg', 'jpeg']:
                            # Convert to RGB for JPEG
                            rgb_img = Image.new('RGB', output_img.size, (255, 255, 255))
                            rgb_img.paste(output_img, (0, 0), output_img)
                            rgb_img.save(output_path, 'JPEG', quality=quality, optimize=True)
                        else:
                            output_img.save(output_path, output_format.upper())
                    
                    processing_time = asyncio.get_event_loop().time() - start_time
                    
                    logger.info(
                        "watermark_added",
                        input_path=input_path,
                        watermark_path=watermark_path,
                        position=position,
                        opacity=opacity,
                        scale=scale,
                        processing_time=processing_time
                    )
                    
                    return {
                        "output_path": output_path,
                        "original_size": base_img.size,
                        "watermark_size": (watermark_width, watermark_height),
                        "watermark_position": (x, y),
                        "position": position,
                        "opacity": opacity,
                        "scale": scale,
                        "quality": quality,
                        "output_format": output_format,
                        "processing_time": processing_time
                    }
                    
        except Exception as e:
            logger.error(
                "watermark_failed",
                error=str(e),
                input_path=input_path,
                watermark_path=watermark_path
            )
            raise
    
    def _apply_opacity(self, img: Image.Image, opacity: float) -> Image.Image:
        """Apply opacity to an image"""
        # Create a new image with adjusted alpha channel
        img_data = img.getdata()
        new_data = []
        
        for item in img_data:
            if len(item) == 4:  # RGBA
                new_data.append((item[0], item[1], item[2], int(item[3] * opacity)))
            else:  # RGB
                new_data.append(item)
        
        new_img = Image.new(img.mode, img.size)
        new_img.putdata(new_data)
        return new_img
    
    def _calculate_watermark_position(
        self,
        base_size: Tuple[int, int],
        watermark_size: Tuple[int, int],
        position: str,
        margin: int
    ) -> Tuple[int, int]:
        """Calculate watermark position based on position string"""
        base_width, base_height = base_size
        wm_width, wm_height = watermark_size
        
        if position == "top-left":
            x = margin
            y = margin
        elif position == "top-right":
            x = base_width - wm_width - margin
            y = margin
        elif position == "bottom-left":
            x = margin
            y = base_height - wm_height - margin
        elif position == "bottom-right":
            x = base_width - wm_width - margin
            y = base_height - wm_height - margin
        elif position == "center":
            x = (base_width - wm_width) // 2
            y = (base_height - wm_height) // 2
        else:
            # Default to bottom-right
            x = base_width - wm_width - margin
            y = base_height - wm_height - margin
        
        # Ensure watermark stays within bounds
        x = max(0, min(x, base_width - wm_width))
        y = max(0, min(y, base_height - wm_height))
        
        return (x, y)
    
    async def add_text_watermark(
        self,
        input_path: str,
        text: str,
        font_path: Optional[str] = None,
        font_size: int = 36,
        font_color: Tuple[int, int, int, int] = (255, 255, 255, 180),
        position: str = "bottom-right",
        margin: int = 20,
        background_color: Optional[Tuple[int, int, int, int]] = None,
        background_padding: int = 10,
        output_format: str = "same",
        quality: int = 95
    ) -> Dict[str, Any]:
        """
        Add text watermark to an image
        
        Args:
            input_path: Path to input image
            text: Text to use as watermark
            font_path: Path to TrueType font file (optional)
            font_size: Font size in pixels
            font_color: Font color as RGBA tuple
            position: Watermark position
            margin: Margin from edges in pixels
            background_color: Optional background color for text
            background_padding: Padding around text background
            output_format: Output format
            quality: Output quality for JPEG
            
        Returns:
            Dict containing watermarked image path and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            if not os.path.exists(input_path):
                raise InvalidMediaError(f"Input file not found: {input_path}")
            
            # Import additional requirements
            from PIL import ImageDraw, ImageFont
            
            # Open image
            with Image.open(input_path) as img:
                # Convert to RGBA for transparency
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create drawing context
                txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(txt_layer)
                
                # Load font
                if font_path and os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    # Try to use a default font
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                
                # Get text dimensions
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Calculate position
                x, y = self._calculate_watermark_position(
                    img.size,
                    (text_width + 2 * background_padding, text_height + 2 * background_padding),
                    position,
                    margin
                )
                
                # Draw background if specified
                if background_color:
                    draw.rectangle(
                        [
                            x - background_padding,
                            y - background_padding,
                            x + text_width + background_padding,
                            y + text_height + background_padding
                        ],
                        fill=background_color
                    )
                
                # Draw text
                draw.text((x, y), text, font=font, fill=font_color)
                
                # Composite the text layer onto the image
                output_img = Image.alpha_composite(img, txt_layer)
                
                # Determine output format
                if output_format == "same":
                    _, ext = os.path.splitext(input_path)
                    output_format = ext[1:].lower() if ext else "jpg"
                
                # Save watermarked image
                with tempfile.NamedTemporaryFile(
                    suffix=f'.{output_format}',
                    delete=False
                ) as temp_file:
                    output_path = temp_file.name
                    
                    if output_format in ['jpg', 'jpeg']:
                        # Convert to RGB for JPEG
                        rgb_img = Image.new('RGB', output_img.size, (255, 255, 255))
                        rgb_img.paste(output_img, (0, 0), output_img)
                        rgb_img.save(output_path, 'JPEG', quality=quality, optimize=True)
                    else:
                        output_img.save(output_path, output_format.upper())
                
                processing_time = asyncio.get_event_loop().time() - start_time
                
                logger.info(
                    "text_watermark_added",
                    input_path=input_path,
                    text=text,
                    position=position,
                    font_size=font_size,
                    processing_time=processing_time
                )
                
                return {
                    "output_path": output_path,
                    "original_size": img.size,
                    "text": text,
                    "text_size": (text_width, text_height),
                    "text_position": (x, y),
                    "position": position,
                    "font_size": font_size,
                    "font_color": font_color,
                    "background_color": background_color,
                    "quality": quality,
                    "output_format": output_format,
                    "processing_time": processing_time
                }
                
        except Exception as e:
            logger.error(
                "text_watermark_failed",
                error=str(e),
                input_path=input_path,
                text=text
            )
            raise
    
    async def batch_watermark(
        self,
        images: List[Dict[str, Any]],
        default_watermark_path: str,
        default_position: str = "bottom-right",
        default_opacity: float = 0.8,
        default_scale: float = 0.2,
        parallel_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Add watermark to multiple images in batch
        
        Args:
            images: List of image configurations
            default_watermark_path: Default watermark image path
            default_position: Default position
            default_opacity: Default opacity
            default_scale: Default scale
            parallel_workers: Number of parallel workers
            
        Returns:
            List of results for each image
        """
        semaphore = asyncio.Semaphore(parallel_workers)
        
        async def process_image(img_config):
            async with semaphore:
                try:
                    result = await self.add_watermark(
                        input_path=img_config["input_path"],
                        watermark_path=img_config.get("watermark_path", default_watermark_path),
                        position=img_config.get("position", default_position),
                        opacity=img_config.get("opacity", default_opacity),
                        scale=img_config.get("scale", default_scale),
                        margin=img_config.get("margin", 20),
                        output_format=img_config.get("output_format", "same"),
                        quality=img_config.get("quality", 95)
                    )
                    result["input_path"] = img_config["input_path"]
                    result["success"] = True
                    return result
                except Exception as e:
                    logger.error(f"Batch watermark failed for {img_config['input_path']}: {e}")
                    return {
                        "input_path": img_config["input_path"],
                        "success": False,
                        "error": str(e)
                    }
        
        tasks = [process_image(img) for img in images]
        results = await asyncio.gather(*tasks)
        
        return results


# Singleton instance
_image_service: Optional[ImageProcessingService] = None


async def get_image_processing_service() -> ImageProcessingService:
    """Get image processing service instance"""
    global _image_service
    
    if _image_service is None:
        _image_service = ImageProcessingService()
    
    return _image_service