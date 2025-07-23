"""
Performance tests using Locust
"""
from locust import HttpUser, task, between
import json
import random
import string


class MAMSUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get auth token"""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "test@example.com",
            "password": "TestPassword123!"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(3)
    def view_assets(self):
        """Browse assets - most common operation"""
        self.client.get("/api/v1/assets", headers=self.headers)
    
    @task(2)
    def search_assets(self):
        """Search for assets"""
        search_terms = ["video", "image", "document", "project", "media"]
        query = random.choice(search_terms)
        self.client.get(f"/api/v1/search?q={query}", headers=self.headers)
    
    @task(1)
    def view_asset_details(self):
        """View specific asset details"""
        # In real test, would get actual asset IDs
        asset_id = f"test-asset-{random.randint(1, 100)}"
        self.client.get(f"/api/v1/assets/{asset_id}", headers=self.headers, name="/api/v1/assets/[id]")
    
    @task(1)
    def upload_asset(self):
        """Upload a new asset"""
        asset_data = {
            "name": f"test_asset_{''.join(random.choices(string.ascii_lowercase, k=10))}.mp4",
            "file_size": random.randint(1000000, 100000000),
            "mime_type": "video/mp4"
        }
        self.client.post("/api/v1/assets", json=asset_data, headers=self.headers)
    
    @task(2)
    def get_user_profile(self):
        """Get user profile"""
        self.client.get("/api/v1/users/me", headers=self.headers)
    
    @task(1)
    def create_project(self):
        """Create a new project"""
        project_data = {
            "name": f"Test Project {random.randint(1, 1000)}",
            "description": "Performance test project"
        }
        self.client.post("/api/v1/projects", json=project_data, headers=self.headers)


class AdminUser(HttpUser):
    """Simulate admin operations"""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login as admin"""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "admin@example.com",
            "password": "AdminPassword123!"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(2)
    def view_system_metrics(self):
        """Check system metrics"""
        self.client.get("/api/v1/monitoring/metrics", headers=self.headers)
    
    @task(1)
    def manage_users(self):
        """User management operations"""
        self.client.get("/api/v1/users", headers=self.headers)
    
    @task(1)
    def view_audit_logs(self):
        """Check audit logs"""
        self.client.get("/api/v1/monitoring/audit", headers=self.headers)


class ApiStressTest(HttpUser):
    """Stress test specific endpoints"""
    wait_time = between(0.1, 0.5)
    
    @task
    def health_check(self):
        """Rapid health checks"""
        self.client.get("/health")
    
    @task
    def api_info(self):
        """API info endpoint"""
        self.client.get("/api/v1/info")