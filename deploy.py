#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'

class DeploymentMode(Enum):
    BOTH = "both"
    FRONTEND = "frontend"
    BACKEND = "backend"

@dataclass
class DeploymentConfig:
    project_id: str = "toms-gym"
    region: str = "us-east1"
    service_account: str = "toms-gym-service@toms-gym.iam.gserviceaccount.com"
    db_pass: str = "test"
    bucket_name: str = "jtr-lift-u-4ever-cool-bucket"

class DeploymentError(Exception):
    """Custom exception for deployment errors"""
    pass

class Spinner:
    def __init__(self, service: str, color: str):
        self.service = service
        self.color = color
        self.spinner_chars = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
        self.current_char = 0
        self.progress = "[0/2] Starting"
        self.running = False
        self.last_progress = ""
        self.start_time = time.time()

    def _get_timestamp(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"[{minutes:02d}:{seconds:02d}]"

    def update_progress(self, progress: str):
        if progress != self.last_progress:
            print()  # New line for new progress
            self.last_progress = progress
        self.progress = progress

    async def spin(self):
        self.running = True
        while self.running:
            char = self.spinner_chars[self.current_char]
            timestamp = self._get_timestamp()
            print(f"\r{timestamp} {self.color}[{self.service}]{Colors.NC} {Colors.BOLD}{self.progress}{Colors.NC} [{char}]  ", end="", flush=True)
            self.current_char = (self.current_char + 1) % len(self.spinner_chars)
            await asyncio.sleep(0.1)

    def stop(self):
        self.running = False
        timestamp = self._get_timestamp()
        print(f"\n{timestamp} {self.color}[{self.service}]{Colors.NC} {Colors.GREEN}Completed ✓{Colors.NC}")

class LogStreamer:
    def __init__(self, log_file: Path, service: str, color: str):
        self.log_file = log_file
        self.service = service
        self.color = color
        self.running = False
        self.last_line = ""
        self.start_time = time.time()

    def _get_timestamp(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"[{minutes:02d}:{seconds:02d}]"

    async def stream(self):
        self.running = True
        with open(self.log_file, 'r') as f:
            while self.running:
                line = f.readline()
                if line and line != self.last_line:
                    # Only print if it's a new line and not empty
                    if line.strip():
                        timestamp = self._get_timestamp()
                        print(f"{timestamp} {self.color}[{self.service} Log]{Colors.NC} {line.strip()}")
                    self.last_line = line
                else:
                    await asyncio.sleep(0.1)

    def stop(self):
        self.running = False

class DeploymentManager:
    def __init__(self, config: DeploymentConfig, mode: DeploymentMode):
        self.config = config
        self.mode = mode
        self.backend_spinner = Spinner("Backend", Colors.YELLOW)
        self.frontend_spinner = Spinner("Frontend", Colors.BLUE)
        self.backend_logs = LogStreamer(Path("/tmp/backend-build.log"), "Backend", Colors.YELLOW)
        self.frontend_logs = LogStreamer(Path("/tmp/frontend-build.log"), "Frontend", Colors.BLUE)
        self._roles_checked = set()  # Cache for checked roles

    async def setup_service_account(self):
        """Set up the service account for backend deployment"""
        if self.mode not in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
            return

        print(f"{Colors.BLUE}🔑 Setting up service account permissions...{Colors.NC}")
        
        # Create service account if it doesn't exist
        try:
            subprocess.run([
                "gcloud", "iam", "service-accounts", "create", "toms-gym-service",
                "--display-name=Tom's Gym Service Account",
                f"--project={self.config.project_id}"
            ], check=False, stderr=subprocess.DEVNULL)
            print(f"{Colors.GREEN}✓ Created service account{Colors.NC}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"{Colors.YELLOW}ℹ️  Service account already exists, continuing...{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}ℹ️  Service account already exists or error occurred, continuing...{Colors.NC}")

        # Add necessary roles (only if not already checked)
        roles_to_check = {
            "storage.objectViewer": "Storage role",
            "cloudsql.client": "Cloud SQL role"
        }

        for role, role_name in roles_to_check.items():
            if role not in self._roles_checked:
                try:
                    subprocess.run([
                        "gcloud", "projects", "add-iam-policy-binding", self.config.project_id,
                        f"--member=serviceAccount:{self.config.service_account}",
                        f"--role=roles/{role}"
                    ], check=False, stderr=subprocess.DEVNULL)
                    print(f"{Colors.GREEN}✓ Added {role_name}{Colors.NC}")
                    self._roles_checked.add(role)
                except Exception as e:
                    if "already has role" in str(e):
                        print(f"{Colors.YELLOW}ℹ️  {role_name} already granted, continuing...{Colors.NC}")
                        self._roles_checked.add(role)
                    else:
                        print(f"{Colors.YELLOW}ℹ️  {role_name} already granted or error occurred, continuing...{Colors.NC}")
                        self._roles_checked.add(role)

    async def get_service_image(self, service: str) -> str:
        """Get the current image of a deployed service"""
        result = subprocess.run([
            "gcloud", "run", "services", "describe", service,
            "--platform", "managed",
            "--region", self.config.region,
            "--format", "value(spec.template.spec.containers[0].image)"
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    async def verify_deployment(self, service: str, expected_image: str) -> bool:
        """Verify that the service is running the expected image version"""
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            current_image = await self.get_service_image(service)
            if current_image == expected_image:
                print(f"{Colors.GREEN}✓ {service} is running the new version{Colors.NC}")
                return True
                
            print(f"{Colors.YELLOW}Waiting for {service} to update... (attempt {attempt + 1}/{max_attempts}){Colors.NC}")
            await asyncio.sleep(10)  # Wait 10 seconds between checks
            attempt += 1
            
        print(f"{Colors.RED}⚠️  {service} failed to update to the new version{Colors.NC}")
        print(f"Expected: {expected_image}")
        print(f"Current: {current_image}")
        return False

    async def deploy_backend(self):
        """Deploy the backend service"""
        if self.mode not in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
            return

        self.backend_spinner.update_progress("[1/2] Building container image")
        # Get current image version
        current_image = await self.get_service_image("my-python-backend")
        print(f"{Colors.BLUE}Current backend image: {current_image}{Colors.NC}")

        # Get the latest build number
        latest_build = subprocess.run([
            "gcloud", "builds", "list",
            "--filter", f"images=gcr.io/{self.config.project_id}/my-python-backend",
            "--format", "value(id)",
            "--limit", "1"
        ], capture_output=True, text=True, check=True).stdout.strip()

        # Build the new version
        build_result = subprocess.run([
            "gcloud", "builds", "submit", "--tag", f"gcr.io/{self.config.project_id}/my-python-backend",
            "--machine-type=e2-highcpu-8",
            "--timeout=1800s",
            "Backend/"
        ], stdout=open("/tmp/backend-build.log", "w"), stderr=subprocess.STDOUT, check=True)

        # Get the new build number
        new_build = subprocess.run([
            "gcloud", "builds", "list",
            "--filter", f"images=gcr.io/{self.config.project_id}/my-python-backend",
            "--format", "value(id)",
            "--limit", "1"
        ], capture_output=True, text=True, check=True).stdout.strip()

        if latest_build == new_build:
            print(f"{Colors.RED}⚠️  Warning: New build has the same ID as the latest build{Colors.NC}")
            return

        self.backend_spinner.update_progress("[2/2] Deploying to Cloud Run")
        subprocess.run([
            "gcloud", "run", "deploy", "my-python-backend",
            "--image", f"gcr.io/{self.config.project_id}/my-python-backend",
            "--platform", "managed",
            "--region", self.config.region,
            "--allow-unauthenticated",
            "--min-instances=1",
            "--memory=1Gi",
            "--cpu=1",
            "--concurrency=80",
            "--timeout=3600",
            f"--service-account={self.config.service_account}",
            f"--set-env-vars=FLASK_ENV=production,DB_INSTANCE={self.config.project_id}:{self.config.region}:my-db,DB_USER=postgres,DB_PASS={self.config.db_pass},DB_NAME=postgres,GCS_BUCKET_NAME={self.config.bucket_name}"
        ], stdout=open("/tmp/backend-build.log", "a"), stderr=subprocess.STDOUT, check=True)

        # Get new image version
        new_image = await self.get_service_image("my-python-backend")
        print(f"{Colors.GREEN}New backend image: {new_image}{Colors.NC}")

        # Verify deployment
        if not await self.verify_deployment("my-python-backend", new_image):
            raise DeploymentError("Backend deployment verification failed")

    async def deploy_frontend(self):
        """Deploy the frontend service"""
        if self.mode not in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
            return

        self.frontend_spinner.update_progress("[1/2] Building container image")
        # Get current image version
        current_image = await self.get_service_image("my-frontend")
        print(f"{Colors.BLUE}Current frontend image: {current_image}{Colors.NC}")

        # Get the latest build number
        latest_build = subprocess.run([
            "gcloud", "builds", "list",
            "--filter", f"images=gcr.io/{self.config.project_id}/my-frontend",
            "--format", "value(id)",
            "--limit", "1"
        ], capture_output=True, text=True, check=True).stdout.strip()

        # Build the new version
        subprocess.run([
            "gcloud", "builds", "submit",
            "--config=cloudbuild.yaml",
            "--machine-type=e2-highcpu-32",
            "--timeout=1800s"
        ], cwd="my-frontend", stdout=open("/tmp/frontend-build.log", "w"), stderr=subprocess.STDOUT, check=True)

        # Get the new build number
        new_build = subprocess.run([
            "gcloud", "builds", "list",
            "--filter", f"images=gcr.io/{self.config.project_id}/my-frontend",
            "--format", "value(id)",
            "--limit", "1"
        ], capture_output=True, text=True, check=True).stdout.strip()

        if latest_build == new_build:
            print(f"{Colors.RED}⚠️  Warning: New build has the same ID as the latest build{Colors.NC}")
            return

        self.frontend_spinner.update_progress("[2/2] Deploying to Cloud Run")
        subprocess.run([
            "gcloud", "run", "deploy", "my-frontend",
            "--image", f"gcr.io/{self.config.project_id}/my-frontend",
            "--platform", "managed",
            "--region", self.config.region,
            "--allow-unauthenticated",
            "--min-instances=1",
            "--memory=512Mi",
            "--cpu=1",
            "--concurrency=80",
            "--timeout=300"
        ], stdout=open("/tmp/frontend-build.log", "a"), stderr=subprocess.STDOUT, check=True)

        # Get new image version
        new_image = await self.get_service_image("my-frontend")
        print(f"{Colors.GREEN}New frontend image: {new_image}{Colors.NC}")

        # Verify deployment
        if not await self.verify_deployment("my-frontend", new_image):
            raise DeploymentError("Frontend deployment verification failed")

    async def get_service_url(self, service: str) -> str:
        """Get the URL of a deployed service"""
        result = subprocess.run([
            "gcloud", "run", "services", "describe", service,
            "--platform", "managed",
            "--region", self.config.region,
            "--format", "value(status.url)"
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    async def verify_health(self, url: str, service: str):
        """Verify the health of a deployed service"""
        print(f"{Colors.BLUE}🏥 Verifying {service} health...{Colors.NC}")
        try:
            subprocess.run(["curl", "-f", url], check=True)
        except subprocess.CalledProcessError:
            print(f"{Colors.RED}⚠️  {service} health check failed{Colors.NC}")

    async def run(self):
        """Run the deployment process"""
        try:
            # Start spinners and log streaming
            tasks = []
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                tasks.extend([
                    asyncio.create_task(self.backend_spinner.spin()),
                    asyncio.create_task(self.backend_logs.stream())
                ])
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                tasks.extend([
                    asyncio.create_task(self.frontend_spinner.spin()),
                    asyncio.create_task(self.frontend_logs.stream())
                ])

            # Run deployments
            await self.setup_service_account()
            deployment_tasks = []
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                deployment_tasks.append(self.deploy_backend())
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                deployment_tasks.append(self.deploy_frontend())
            
            await asyncio.gather(*deployment_tasks)

            # Stop spinners and log streaming
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                self.backend_spinner.stop()
                self.backend_logs.stop()
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                self.frontend_spinner.stop()
                self.frontend_logs.stop()

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

            print(f"{Colors.GREEN}🎉 Deployment completed successfully!{Colors.NC}")

            # Print service URLs and verify health
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                backend_url = await self.get_service_url("my-python-backend")
                print(f"{Colors.BOLD}Backend:{Colors.NC} {backend_url}")
                await self.verify_health(backend_url, "Backend")

            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                frontend_url = await self.get_service_url("my-frontend")
                print(f"{Colors.BOLD}Frontend:{Colors.NC} {frontend_url}")
                await self.verify_health(frontend_url, "Frontend")

            # Print deployment summary
            print(f"\n{Colors.BLUE}📝 Deployment Summary:{Colors.NC}")
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                print(f"{Colors.BOLD}- Backend: {Colors.NC}{backend_url}")
                print("  • 1 CPU, 1GB RAM")
                print("  • Min 1 instance")
                print("  • 80 concurrent requests")
                print("  • Production environment")
                print("  • Health checks enabled")
                print(f"  • Service account: {self.config.service_account}")
                print(f"  • Database: {self.config.project_id}:{self.config.region}:my-db")
                print(f"  • Storage bucket: {self.config.bucket_name}")

            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                print(f"{Colors.BOLD}- Frontend: {Colors.NC}{frontend_url}")
                print("  • 1 CPU, 512MB RAM")
                print("  • Min 1 instance")
                print("  • 80 concurrent requests")
                print("  • Static file serving")

            print(f"\n{Colors.YELLOW}Deployment logs:{Colors.NC}")
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                print("  • Backend: /tmp/backend-build.log")
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                print("  • Frontend: /tmp/frontend-build.log")

        except Exception as e:
            print(f"{Colors.RED}Error during deployment: {str(e)}{Colors.NC}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Deploy Tom's Gym application")
    parser.add_argument("--frontend-only", action="store_true", help="Deploy only the frontend")
    parser.add_argument("--backend-only", action="store_true", help="Deploy only the backend")
    args = parser.parse_args()

    # Determine deployment mode
    if args.frontend_only:
        mode = DeploymentMode.FRONTEND
    elif args.backend_only:
        mode = DeploymentMode.BACKEND
    else:
        mode = DeploymentMode.BOTH

    # Create deployment manager and run deployment
    config = DeploymentConfig()
    manager = DeploymentManager(config, mode)
    asyncio.run(manager.run())

if __name__ == "__main__":
    main() 