"""
Image Processing Utilities

Helper functions for image analysis and processing.
"""

import cv2
import numpy as np
from PIL import Image, ExifTags
from typing import Dict, List, Tuple, Optional
import structlog


logger = structlog.get_logger()


class ImageProcessor:
    """Image processing utilities for auto-tagging"""
    
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    def extract_exif_data(self, image_path: str) -> Dict:
        """Extract EXIF metadata from image"""
        try:
            image = Image.open(image_path)
            exif_data = {}
            
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value
            
            return exif_data
            
        except Exception as e:
            logger.error("Error extracting EXIF data", error=str(e))
            return {}
    
    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        """Detect faces in image"""
        try:
            # Load face cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Convert to list of dictionaries
            face_list = []
            for (x, y, w, h) in faces:
                face_list.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': 0.8  # OpenCV doesn't provide confidence
                })
            
            return face_list
            
        except Exception as e:
            logger.error("Error detecting faces", error=str(e))
            return []
    
    def calculate_histogram(self, image: np.ndarray) -> Dict:
        """Calculate color histogram"""
        try:
            # Calculate histogram for each channel
            histograms = {}
            
            # RGB histograms
            for i, color in enumerate(['blue', 'green', 'red']):
                hist = cv2.calcHist([image], [i], None, [256], [0, 256])
                histograms[color] = hist.flatten().tolist()
            
            # Overall brightness histogram
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness_hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            histograms['brightness'] = brightness_hist.flatten().tolist()
            
            return histograms
            
        except Exception as e:
            logger.error("Error calculating histogram", error=str(e))
            return {}
    
    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Detect edges using Canny edge detection"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            return edges
            
        except Exception as e:
            logger.error("Error detecting edges", error=str(e))
            return np.zeros_like(image[:, :, 0])
    
    def calculate_sharpness(self, image: np.ndarray) -> float:
        """Calculate image sharpness using Laplacian variance"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            return float(laplacian_var)
            
        except Exception as e:
            logger.error("Error calculating sharpness", error=str(e))
            return 0.0
    
    def detect_blur(self, image: np.ndarray, threshold: float = 100.0) -> bool:
        """Detect if image is blurry"""
        sharpness = self.calculate_sharpness(image)
        return sharpness < threshold
    
    def calculate_noise_level(self, image: np.ndarray) -> float:
        """Estimate noise level in image"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Use standard deviation of Laplacian as noise estimate
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            noise_level = np.std(laplacian)
            
            return float(noise_level)
            
        except Exception as e:
            logger.error("Error calculating noise level", error=str(e))
            return 0.0
    
    def analyze_composition(self, image: np.ndarray) -> Dict:
        """Analyze image composition"""
        try:
            height, width = image.shape[:2]
            
            composition_data = {
                'width': width,
                'height': height,
                'aspect_ratio': width / height,
                'total_pixels': width * height
            }
            
            # Rule of thirds analysis
            third_x = width // 3
            third_y = height // 3
            
            # Define regions
            regions = {
                'top_left': image[0:third_y, 0:third_x],
                'top_center': image[0:third_y, third_x:2*third_x],
                'top_right': image[0:third_y, 2*third_x:width],
                'middle_left': image[third_y:2*third_y, 0:third_x],
                'center': image[third_y:2*third_y, third_x:2*third_x],
                'middle_right': image[third_y:2*third_y, 2*third_x:width],
                'bottom_left': image[2*third_y:height, 0:third_x],
                'bottom_center': image[2*third_y:height, third_x:2*third_x],
                'bottom_right': image[2*third_y:height, 2*third_x:width]
            }
            
            # Calculate interest points (high contrast areas)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            corners = cv2.goodFeaturesToTrack(
                gray, maxCorners=100, qualityLevel=0.01, minDistance=10
            )
            
            if corners is not None:
                # Count corners in each region
                region_interest = {}
                for region_name, bounds in [
                    ('top_third', (0, third_y)),
                    ('middle_third', (third_y, 2*third_y)),
                    ('bottom_third', (2*third_y, height)),
                    ('left_third', (0, third_x)),
                    ('center_third', (third_x, 2*third_x)),
                    ('right_third', (2*third_x, width))
                ]:
                    count = 0
                    for corner in corners:
                        x, y = corner.ravel()
                        if region_name.endswith('_third'):
                            if 'top' in region_name and bounds[0] <= y < bounds[1]:
                                count += 1
                            elif 'middle' in region_name and bounds[0] <= y < bounds[1]:
                                count += 1
                            elif 'bottom' in region_name and bounds[0] <= y < bounds[1]:
                                count += 1
                            elif 'left' in region_name and bounds[0] <= x < bounds[1]:
                                count += 1
                            elif 'center' in region_name and bounds[0] <= x < bounds[1]:
                                count += 1
                            elif 'right' in region_name and bounds[0] <= x < bounds[1]:
                                count += 1
                    
                    region_interest[region_name] = count
                
                composition_data['interest_distribution'] = region_interest
                composition_data['total_interest_points'] = len(corners)
            
            return composition_data
            
        except Exception as e:
            logger.error("Error analyzing composition", error=str(e))
            return {}
    
    def extract_dominant_colors(self, image: np.ndarray, k: int = 5) -> List[Dict]:
        """Extract dominant colors using K-means clustering"""
        try:
            from sklearn.cluster import KMeans
            
            # Reshape image to be a list of pixels
            pixels = image.reshape(-1, 3)
            
            # Apply K-means clustering
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get colors and their percentages
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            percentages = np.bincount(labels) / len(labels)
            
            # Sort by percentage
            sorted_indices = np.argsort(percentages)[::-1]
            
            dominant_colors = []
            for i in sorted_indices:
                color_info = {
                    'rgb': colors[i].tolist(),
                    'percentage': float(percentages[i]),
                    'rank': len(dominant_colors) + 1
                }
                dominant_colors.append(color_info)
            
            return dominant_colors
            
        except Exception as e:
            logger.error("Error extracting dominant colors", error=str(e))
            return []
    
    def detect_text_regions(self, image: np.ndarray) -> List[Dict]:
        """Detect potential text regions using MSER"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Create MSER detector
            mser = cv2.MSER_create()
            
            # Detect regions
            regions, _ = mser.detectRegions(gray)
            
            text_regions = []
            for region in regions:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
                
                # Filter by aspect ratio and size
                aspect_ratio = w / h
                area = w * h
                
                if 0.1 < aspect_ratio < 10 and area > 100:
                    text_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h),
                        'area': int(area),
                        'aspect_ratio': float(aspect_ratio)
                    })
            
            return text_regions
            
        except Exception as e:
            logger.error("Error detecting text regions", error=str(e))
            return []
    
    def calculate_complexity(self, image: np.ndarray) -> float:
        """Calculate visual complexity of image"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate edge density
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Calculate texture complexity using local binary patterns
            # Simplified version using gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            texture_complexity = np.mean(gradient_magnitude) / 255.0
            
            # Combine metrics
            complexity = (edge_density + texture_complexity) / 2
            
            return float(complexity)
            
        except Exception as e:
            logger.error("Error calculating complexity", error=str(e))
            return 0.0
    
    def resize_for_analysis(self, image: np.ndarray, max_size: int = 1024) -> np.ndarray:
        """Resize image for analysis while maintaining aspect ratio"""
        try:
            height, width = image.shape[:2]
            
            if max(height, width) <= max_size:
                return image
            
            # Calculate new dimensions
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            return resized
            
        except Exception as e:
            logger.error("Error resizing image", error=str(e))
            return image