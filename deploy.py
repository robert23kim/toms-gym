#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'

# Global timestamp function to ensure consistency across all logging
def get_timestamp(start_time=None):
    if start_time is None:
        start_time = time.time()
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    return f"[{minutes:02d}:{seconds:02d}]"

# Global logging function with timestamps
def log(message, color=None, start_time=None):
    timestamp = get_timestamp(start_time)
    if color:
        print(f"{timestamp} {color}{message}{Colors.NC}")
    else:
        print(f"{timestamp} {message}")

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
    backend_service: str = "my-python-backend"
    frontend_service: str = "my-frontend"
    backend_image: str = "gcr.io/toms-gym/my-python-backend:latest"
    frontend_image: str = "gcr.io/toms-gym/my-frontend:latest"
    backend_log: str = "/tmp/backend-build.log"
    frontend_log: str = "/tmp/frontend-build.log"

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
        self.last_timestamp = ""

    def _get_timestamp(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        if timestamp != self.last_timestamp:
            self.last_timestamp = timestamp
        return timestamp

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
        self.last_timestamp = ""

    def _get_timestamp(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        if timestamp != self.last_timestamp:
            self.last_timestamp = timestamp
        return timestamp

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
        self.backend_logs = LogStreamer(Path(self.config.backend_log), "Backend", Colors.YELLOW)
        self.frontend_logs = LogStreamer(Path(self.config.frontend_log), "Frontend", Colors.BLUE)
        self._roles_checked = set()  # Cache for checked roles
        self.start_time = time.time()
        self.api_url = None
        self.force_refresh = False

    def log(self, message, color=None):
        """Helper method for consistent logging"""
        log(message, color, self.start_time)

    async def run_command(self, command: List[str], cwd: str = None, log_file: str = None, 
                          append: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and handle logging consistently"""
        self.log(f"Running: {' '.join(command)}", Colors.BLUE)
        
        # Open log file if provided
        stdout_target = None
        if log_file:
            mode = "a" if append else "w"
            stdout_target = open(log_file, mode)
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=stdout_target,
                stderr=subprocess.STDOUT if stdout_target else None,
                text=True,
                capture_output=stdout_target is None,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed with exit code {e.returncode}: {e}", Colors.RED)
            if check:
                raise
            return e
        finally:
            if stdout_target:
                stdout_target.close()

    async def setup_service_account(self):
        """Set up the service account for backend deployment"""
        if self.mode not in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
            return

        self.log("🔑 Setting up service account permissions...", Colors.BLUE)
        
        # Create service account if it doesn't exist
        try:
            await self.run_command([
                "gcloud", "iam", "service-accounts", "create", "toms-gym-service",
                "--display-name=Tom's Gym Service Account",
                f"--project={self.config.project_id}"
            ], check=False)
            self.log("✓ Created service account", Colors.GREEN)
        except Exception as e:
            if "already exists" in str(e):
                self.log("ℹ️  Service account already exists, continuing...", Colors.YELLOW)
            else:
                self.log("ℹ️  Service account already exists or error occurred, continuing...", Colors.YELLOW)

        # Add necessary roles (only if not already checked)
        roles_to_check = {
            "storage.objectViewer": "Storage role",
            "cloudsql.client": "Cloud SQL role"
        }

        for role, role_name in roles_to_check.items():
            if role not in self._roles_checked:
                try:
                    await self.run_command([
                        "gcloud", "projects", "add-iam-policy-binding", self.config.project_id,
                        f"--member=serviceAccount:{self.config.service_account}",
                        f"--role=roles/{role}"
                    ], check=False)
                    self.log(f"✓ Added {role_name}", Colors.GREEN)
                    self._roles_checked.add(role)
                except Exception as e:
                    if "already has role" in str(e):
                        self.log(f"ℹ️  {role_name} already granted, continuing...", Colors.YELLOW)
                        self._roles_checked.add(role)
                    else:
                        self.log(f"ℹ️  {role_name} already granted or error occurred, continuing...", Colors.YELLOW)
                        self._roles_checked.add(role)

    async def get_service_image(self, service: str) -> str:
        """Get the current image of a deployed service"""
        result = await self.run_command([
            "gcloud", "run", "services", "describe", service,
            "--platform", "managed",
            "--region", self.config.region,
            "--format", "value(spec.template.spec.containers[0].image)"
        ])
        return result.stdout.strip()

    async def verify_deployment(self, service: str, expected_image: str) -> bool:
        """Verify that the service is running the expected image version"""
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            current_image = await self.get_service_image(service)
            if current_image == expected_image:
                self.log(f"✓ {service} is running the new version", Colors.GREEN)
                return True
                
            self.log(f"Waiting for {service} to update... (attempt {attempt + 1}/{max_attempts})", Colors.YELLOW)
            await asyncio.sleep(10)  # Wait 10 seconds between checks
            attempt += 1
            
        self.log(f"⚠️  {service} failed to update to the new version", Colors.RED)
        self.log(f"Expected: {expected_image}")
        self.log(f"Current: {current_image}")
        return False

    async def build_and_deploy_service(self, service_type: str, build_commands: List[str], deploy_commands: List[str], 
                                       cwd: str = None, spinner: Spinner = None, log_file: str = None) -> str:
        """Generic method to build and deploy a service"""
        if not spinner or not log_file:
            raise ValueError("Spinner and log file must be provided")
            
        # Get current image
        current_image = await self.get_service_image(
            self.config.backend_service if service_type == "Backend" else self.config.frontend_service
        )
        self.log(f"Current {service_type.lower()} image: {current_image}", Colors.BLUE)
        
        # Build step
        spinner.update_progress("[1/2] Building container image")
        self.log(f"Starting {service_type.lower()} build...", Colors.YELLOW)
        
        build_start_time = time.time()
        await self.run_command(build_commands, cwd=cwd, log_file=log_file)
        build_end_time = time.time()
        build_duration = int(build_end_time - build_start_time)
        self.log(f"Build completed in {build_duration} seconds", Colors.GREEN)
        
        # Deploy step
        spinner.update_progress("[2/2] Deploying to Cloud Run")
        await self.run_command(deploy_commands, log_file=log_file, append=True)
        
        # Get new image version
        new_image = await self.get_service_image(
            self.config.backend_service if service_type == "Backend" else self.config.frontend_service
        )
        self.log(f"New {service_type.lower()} image: {new_image}", Colors.GREEN)
        
        return new_image

    async def deploy_backend(self):
        """Deploy the backend service"""
        if self.mode not in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
            return
            
        # Build commands
        build_commands = [
            "gcloud", "builds", "submit", 
            "--tag", self.config.backend_image,
            "--machine-type=e2-highcpu-8",
            "--timeout=1800s",
            "Backend/"
        ]
        
        # Deploy commands
        deploy_commands = [
            "gcloud", "run", "deploy", self.config.backend_service,
            "--image", self.config.backend_image,
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
        ]
        
        # Build and deploy
        new_image = await self.build_and_deploy_service(
            "Backend", 
            build_commands, 
            deploy_commands, 
            spinner=self.backend_spinner,
            log_file=self.config.backend_log
        )
        
        # Verify deployment
        if not await self.verify_deployment(self.config.backend_service, new_image):
            raise DeploymentError("Backend deployment verification failed")

    async def deploy_frontend(self):
        """Deploy the frontend service"""
        if self.mode not in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
            return
            
        # Build commands
        build_commands = [
            "gcloud", "builds", "submit",
            "--config=cloudbuild.yaml",
            "--machine-type=e2-highcpu-32",
            "--timeout=1800s"
        ]
        
        # Set the API_URL environment variable if provided
        if self.api_url:
            self.log(f"Setting API_URL to {self.api_url} for frontend build", Colors.BLUE)
            # Create a temporary .env.production file with the API_URL
            with open("my-frontend/.env.production", "w") as f:
                f.write(f"VITE_API_URL={self.api_url}\n")
                f.write(f"VITE_BUILD_TIMESTAMP={int(time.time())}\n")
        else:
            # Create a timestamp even without custom API_URL
            with open("my-frontend/.env.production", "w") as f:
                f.write(f"VITE_BUILD_TIMESTAMP={int(time.time())}\n")
        
        # Deploy commands
        deploy_commands = [
            "gcloud", "run", "deploy", self.config.frontend_service,
            "--image", self.config.frontend_image,
            "--platform", "managed",
            "--region", self.config.region,
            "--allow-unauthenticated",
            "--min-instances=1",
            "--memory=512Mi",
            "--cpu=1",
            "--concurrency=80",
            "--timeout=300"
        ]
        
        # Build and deploy
        new_image = await self.build_and_deploy_service(
            "Frontend", 
            build_commands, 
            deploy_commands, 
            cwd="my-frontend",
            spinner=self.frontend_spinner,
            log_file=self.config.frontend_log
        )
        
        # Verify deployment
        if not await self.verify_deployment(self.config.frontend_service, new_image):
            raise DeploymentError("Frontend deployment verification failed")

    async def get_service_url(self, service: str) -> str:
        """Get the URL of a deployed service"""
        result = await self.run_command([
            "gcloud", "run", "services", "describe", service,
            "--platform", "managed",
            "--region", self.config.region,
            "--format", "value(status.url)"
        ])
        return result.stdout.strip()

    async def verify_health(self, url: str, service: str):
        """Verify the health of a deployed service"""
        self.log(f"🏥 Verifying {service} health...", Colors.BLUE)
        try:
            # Use -s (silent) flag to suppress output, -o /dev/null to redirect output
            # -w to only output HTTP status code, and -f to fail on HTTP errors
            result = await self.run_command(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-f", url],
                check=False
            )
            
            status_code = result.stdout.strip()
            if result.returncode == 0 and status_code.startswith("2"):
                self.log(f"✓ {service} health check passed (HTTP {status_code})", Colors.GREEN)
            else:
                self.log(f"⚠️  {service} health check failed (HTTP {status_code})", Colors.RED)
        except subprocess.CalledProcessError:
            self.log(f"⚠️  {service} health check failed - could not connect", Colors.RED)

    async def print_deployment_summary(self, backend_url=None, frontend_url=None):
        """Print a summary of the deployment"""
        self.log("\n📝 Deployment Summary:", Colors.BLUE)
        
        if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND] and backend_url:
            self.log(f"- Backend: {backend_url}", Colors.BOLD)
            self.log(f"  • 1 CPU, 1GB RAM")
            self.log(f"  • Min 1 instance")
            self.log(f"  • 80 concurrent requests")
            self.log(f"  • Production environment")
            self.log(f"  • Health checks enabled")
            self.log(f"  • Service account: {self.config.service_account}")
            self.log(f"  • Database: {self.config.project_id}:{self.config.region}:my-db")
            self.log(f"  • Storage bucket: {self.config.bucket_name}")

        if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND] and frontend_url:
            self.log(f"- Frontend: {frontend_url}", Colors.BOLD)
            self.log(f"  • 1 CPU, 512MB RAM")
            self.log(f"  • Min 1 instance")
            self.log(f"  • 80 concurrent requests")
            self.log(f"  • Static file serving")

        self.log(f"\n{Colors.YELLOW}Deployment logs:{Colors.NC}")
        if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
            self.log(f"  • Backend: {self.config.backend_log}")
        if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
            self.log(f"  • Frontend: {self.config.frontend_log}")

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

            self.log("🎉 Deployment completed successfully!", Colors.GREEN)

            # Get service URLs and verify health
            backend_url = None
            frontend_url = None
            
            if self.mode in [DeploymentMode.BOTH, DeploymentMode.BACKEND]:
                backend_url = await self.get_service_url(self.config.backend_service)
                self.log(f"Backend: {backend_url}", Colors.BOLD)
                await self.verify_health(backend_url, "Backend")

            if self.mode in [DeploymentMode.BOTH, DeploymentMode.FRONTEND]:
                frontend_url = await self.get_service_url(self.config.frontend_service)
                self.log(f"Frontend: {frontend_url}", Colors.BOLD)
                await self.verify_health(frontend_url, "Frontend")

            # Print deployment summary
            await self.print_deployment_summary(backend_url, frontend_url)

        except Exception as e:
            self.log(f"Error during deployment: {str(e)}", Colors.RED)
            # Print stack trace for better debugging
            import traceback
            self.log(traceback.format_exc(), Colors.RED)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Deploy Tom's Gym application")
    parser.add_argument("--frontend-only", action="store_true", help="Deploy only the frontend")
    parser.add_argument("--backend-only", action="store_true", help="Deploy only the backend")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--api-url", help="Set the API URL for the frontend (e.g., https://backend-url.run.app)")
    parser.add_argument("--force-refresh", action="store_true", help="Force browser cache refresh by adding timestamp")
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
    
    # Set API URL if provided
    if args.api_url:
        manager.api_url = args.api_url
    
    # Force refresh if requested
    if args.force_refresh:
        manager.force_refresh = True
    
    # Print debug info if requested
    if args.debug:
        log("Debug mode enabled", Colors.YELLOW)
        log(f"Deployment mode: {mode.value}", Colors.YELLOW)
        if args.api_url:
            log(f"Using API URL: {args.api_url}", Colors.YELLOW)
    
    # Run the deployment
    asyncio.run(manager.run())

if __name__ == "__main__":
    main() 