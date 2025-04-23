#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'
    END = '\033[0m'  # Alias for NC for compatibility

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
    """Configuration for deployment."""
    project_id: str
    region: str
    backend_service: str = "my-python-backend"
    frontend_service: str = "my-frontend"
    backend_image: str = "gcr.io/toms-gym/my-python-backend:latest"
    frontend_image: str = "gcr.io/toms-gym/my-frontend:latest"
    service_account: str = "toms-gym-service@toms-gym.iam.gserviceaccount.com"
    min_instances: int = 1
    backend_memory: str = "1Gi"
    backend_cpu: int = 1
    backend_concurrency: int = 80
    backend_timeout: int = 3600
    frontend_memory: str = "512Mi"
    frontend_cpu: int = 1
    frontend_concurrency: int = 80
    frontend_timeout: int = 300
    api_url: Optional[str] = None
    force_refresh: bool = False
    backend_log: str = "backend_deploy.log"
    frontend_log: str = "frontend_deploy.log"
    db_pass: str = ""
    bucket_name: str = "jtr-lift-u-4ever-cool-bucket"
    
    @classmethod
    def from_file(cls, config_file: str) -> 'DeploymentConfig':
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Create basic config
            config = cls(
                project_id=config_data.get('project_id', 'toms-gym'),
                region=config_data.get('region', 'us-east1'),
            )
            
            # Load backend config
            if 'backend' in config_data:
                backend = config_data['backend']
                config.backend_service = backend.get('service_name', config.backend_service)
                config.backend_image = f"gcr.io/{config.project_id}/{config.backend_service}:latest"
                config.min_instances = backend.get('min_instances', config.min_instances)
                config.backend_memory = backend.get('memory', config.backend_memory)
                config.backend_cpu = backend.get('cpu', config.backend_cpu)
                config.backend_concurrency = backend.get('concurrency', config.backend_concurrency)
                config.backend_timeout = backend.get('timeout', config.backend_timeout)
                config.service_account = backend.get('service_account', config.service_account)
                
                # Extract environment variables
                if 'env_vars' in backend:
                    env_vars = backend['env_vars']
                    config.bucket_name = env_vars.get('GCS_BUCKET_NAME', config.bucket_name)
                    config.db_pass = env_vars.get('DB_PASS', config.db_pass)
            
            # Load frontend config
            if 'frontend' in config_data:
                frontend = config_data['frontend']
                config.frontend_service = frontend.get('service_name', config.frontend_service)
                config.frontend_image = f"gcr.io/{config.project_id}/{config.frontend_service}:latest"
                config.frontend_memory = frontend.get('memory', config.frontend_memory)
                config.frontend_cpu = frontend.get('cpu', config.frontend_cpu)
                config.frontend_concurrency = frontend.get('concurrency', config.frontend_concurrency)
                config.frontend_timeout = frontend.get('timeout', config.frontend_timeout)
            
            return config
        except Exception as e:
            print(f"{Colors.RED}Error loading config file: {e}{Colors.END}")
            return cls(project_id="toms-gym", region="us-east1")  # Default config

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
    """Streams log files in real-time."""
    def __init__(self, log_file: Path, service: str, color: str):
        self.log_file = log_file
        self.service = service
        self.color = color
        self.running = True
        self.last_line = None
        
        # Create the log file if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write(f"=== {service} Deployment Log ===\n")
    
    def _get_timestamp(self):
        """Get a formatted timestamp for log output."""
        return get_timestamp()
        
    async def stream(self):
        """Stream the log file content in real-time."""
        while self.running:
            try:
                with open(self.log_file, 'r') as f:
                    # Go to the end of the file
                    if self.last_line:
                        f.seek(0, os.SEEK_END)
                    
                    while self.running:
                        line = f.readline()
                        if line:
                            if line.strip():
                                timestamp = self._get_timestamp()
                                print(f"{timestamp} {self.color}[{self.service} Log]{Colors.NC} {line.strip()}")
                            self.last_line = line
                        else:
                            await asyncio.sleep(0.1)
            except FileNotFoundError:
                # Create the log file if it doesn't exist
                with open(self.log_file, 'w') as f:
                    f.write(f"=== {self.service} Deployment Log ===\n")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error reading log file {self.log_file}: {e}")
                await asyncio.sleep(1)

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
                          append: bool = False, check: bool = True, show_output: bool = False) -> subprocess.CompletedProcess:
        """Run a command and handle logging consistently"""
        self.log(f"Running: {' '.join(command)}", Colors.BLUE)
        
        # For commands where we want to show output in real time
        if show_output:
            # Run the command with output streaming to terminal
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Open log file if provided
            log_file_handle = None
            if log_file:
                mode = "a" if append else "w"
                log_file_handle = open(log_file, mode)
            
            # Process output in real-time
            async def read_stream(stream, prefix, log_handle):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8').rstrip()
                    timestamp = get_timestamp(self.start_time)
                    
                    # Check if stderr line contains expected information messages
                    if prefix.startswith(f"{Colors.RED}[ERR]"):
                        # Common informational patterns from gcloud that appear in stderr
                        info_patterns = [
                            "already exists",
                            "already has role",
                            "Creating service account",
                            "Setting IAM policy",
                            "Beginning deployment",
                            "Deploying container",
                            "Deploying...",
                            "Revision",
                            "Setting IAM",
                            "Created",
                            "Creating revision",
                            "Routing traffic",
                            "Done.",
                            "Service [",
                            "revision [",
                            "has been deployed",
                            "percent of traffic",
                            "Service URL:",
                            "Creating",
                            "waiting for",
                            "Created service",
                            "Waiting for",
                            "https://",
                            "Check the gcloud log",
                            "Some files were not included",
                            "Logs are available at",
                            "Uploading tarball"
                        ]
                        
                        if any(pattern in line_str for pattern in info_patterns):
                            # Show as warning instead of error
                            print(f"{timestamp} {Colors.YELLOW}[WARN]{Colors.NC} {line_str}")
                        else:
                            # Actual error
                            print(f"{timestamp} {prefix} {line_str}")
                    else:
                        # Regular stdout messages
                        print(f"{timestamp} {prefix} {line_str}")
                        
                    if log_handle:
                        log_handle.write(f"{line_str}\n")
                        log_handle.flush()
            
            # Create tasks to read stdout and stderr
            stdout_task = asyncio.create_task(
                read_stream(process.stdout, f"{Colors.BLUE}[LOG]{Colors.NC}", log_file_handle)
            )
            stderr_task = asyncio.create_task(
                read_stream(process.stderr, f"{Colors.RED}[ERR]{Colors.NC}", log_file_handle)
            )
            
            # Wait for the command to complete
            exit_code = await process.wait()
            
            # Wait for the output processing to complete
            await stdout_task
            await stderr_task
            
            # Close log file if opened
            if log_file_handle:
                log_file_handle.close()
            
            # Handle command result
            if exit_code != 0 and check:
                self.log(f"Command failed with exit code {exit_code}", Colors.RED)
                raise subprocess.CalledProcessError(exit_code, command)
            
            # Create a CompletedProcess-like result
            class Result:
                def __init__(self, returncode, stdout):
                    self.returncode = returncode
                    self.stdout = stdout
            
            return Result(exit_code, "")
        
        # Original implementation for commands where we don't need real-time output
        else:
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
                self.log("⚠️  Service account setup yielded a warning, continuing...", Colors.YELLOW)

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
                        self.log(f"⚠️  {role_name} assignment yielded a warning, continuing...", Colors.YELLOW)
                        self._roles_checked.add(role)
        
        # Add specific bucket permissions
        self.log("🪣 Setting up GCS bucket permissions...", Colors.BLUE)
        try:
            # Grant storage.objects.create permission to the specific bucket
            await self.run_command([
                "gsutil", "iam", "ch", 
                f"serviceAccount:{self.config.service_account}:roles/storage.objectAdmin",
                f"gs://{self.config.bucket_name}"
            ], show_output=True)
            self.log(f"✓ Added storage.objectAdmin role for bucket {self.config.bucket_name}", Colors.GREEN)
        except Exception as e:
            if "already has role" in str(e):
                self.log(f"ℹ️  Bucket permissions already granted, continuing...", Colors.YELLOW)
            else:
                self.log(f"⚠️  Error setting bucket permissions: {str(e)}", Colors.RED)

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
        await self.run_command(build_commands, cwd=cwd, log_file=log_file, show_output=True)
        build_end_time = time.time()
        build_duration = int(build_end_time - build_start_time)
        self.log(f"Build completed in {build_duration} seconds", Colors.GREEN)
        
        # Deploy step
        spinner.update_progress("[2/2] Deploying to Cloud Run")
        self.log(f"Starting {service_type.lower()} deployment...", Colors.YELLOW)
        deploy_start_time = time.time()
        await self.run_command(deploy_commands, log_file=log_file, append=True, show_output=True)
        deploy_end_time = time.time()
        deploy_duration = int(deploy_end_time - deploy_start_time)
        self.log(f"Deployment completed in {deploy_duration} seconds", Colors.GREEN)
        
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
            f"--set-env-vars=FLASK_ENV=production,DB_INSTANCE={self.config.project_id}:{self.config.region}:my-db,DB_USER=postgres,DB_PASS=test,DB_NAME=postgres,GCS_BUCKET_NAME={self.config.bucket_name},JWT_SECRET_KEY=your-secret-key-here,DATABASE_URL=postgresql://postgres:test@/postgres?host=/cloudsql/{self.config.project_id}:{self.config.region}:my-db"
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
            
        # Route traffic to the latest revision
        self.log("Routing traffic to the latest backend revision...", Colors.YELLOW)
        await self.route_traffic_to_latest(self.config.backend_service)

    async def route_traffic_to_latest(self, service: str):
        """Route 100% of traffic to the latest revision of a service"""
        spinner = None
        if service == self.config.backend_service:
            spinner = self.backend_spinner
            spinner.update_progress("[3/3] Routing traffic to latest revision")
        elif service == self.config.frontend_service:
            spinner = self.frontend_spinner
            spinner.update_progress("[3/3] Routing traffic to latest revision")
        
        try:
            result = await self.run_command([
                "gcloud", "run", "services", "update-traffic", service,
                "--platform", "managed",
                "--region", self.config.region,
                "--to-latest"
            ])
            
            self.log(f"✅ Successfully routed 100% traffic to latest revision of {service}", Colors.GREEN)
            return True
        except Exception as e:
            self.log(f"❌ Failed to route traffic to latest revision of {service}: {e}", Colors.RED)
            return False

    async def deploy_frontend(self):
        """Deploy the frontend to Cloud Run"""
        self.log("Deploying frontend...", Colors.BLUE)
        
        build_commands = [
            "gcloud", "builds", "submit",
            "--config=cloudbuild.yaml",
            "--machine-type=e2-highcpu-32",
            "--timeout=1800s",
        ]
        
        # Get the production backend URL if not explicitly provided
        backend_url = self.api_url
        if not backend_url:
            # Get the backend service URL if it's already deployed
            try:
                backend_url = await self.get_service_url(self.config.backend_service)
                self.log(f"Using backend URL from deployed service: {backend_url}", Colors.BLUE)
            except Exception as e:
                # Default to the standard production backend URL if we can't get it
                backend_url = "https://my-python-backend-quyiiugyoq-ue.a.run.app"
                self.log(f"Using default backend URL: {backend_url}", Colors.BLUE)
        
        # Always set the API_URL in the production environment
        self.log(f"Setting API_URL to {backend_url} for frontend build", Colors.BLUE)
        # Create a temporary .env.production file with the API_URL
        with open("my-frontend/.env.production", "w") as f:
            f.write(f"VITE_API_URL={backend_url}\n")
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
            
        # Route traffic to the latest revision
        self.log("Routing traffic to the latest frontend revision...", Colors.BLUE)
        await self.route_traffic_to_latest(self.config.frontend_service)

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
    """Main function to parse arguments and run deployment."""
    parser = argparse.ArgumentParser(description='Deploy Tom\'s Gym application to Cloud Run')
    parser.add_argument('--frontend-only', action='store_true', help='Deploy only the frontend')
    parser.add_argument('--backend-only', action='store_true', help='Deploy only the backend')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--api-url', type=str, help='Set the API URL for the frontend')
    parser.add_argument('--force-refresh', action='store_true', help='Force browser cache refresh by adding a timestamp')
    parser.add_argument('--config', type=str, default='deploy-config.json', help='Path to deployment configuration file')
    args = parser.parse_args()
    
    # Set deployment mode
    if args.frontend_only and args.backend_only:
        print(f"{Colors.RED}Error: Cannot specify both --frontend-only and --backend-only{Colors.END}")
        sys.exit(1)
    elif args.frontend_only:
        mode = DeploymentMode.FRONTEND
    elif args.backend_only:
        mode = DeploymentMode.BACKEND
    else:
        mode = DeploymentMode.BOTH
        
    # Set debug mode
    if args.debug:
        os.environ['DEBUG'] = '1'
        
    # Load configuration
    try:
        # Try different paths for the config file - current directory, absolute path, or relative to script
        config_paths = [
            args.config,
            os.path.abspath(args.config),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), args.config)
        ]
        
        config = None
        for path in config_paths:
            if os.path.exists(path):
                print(f"Using config file: {path}")
                config = DeploymentConfig.from_file(path)
                break
                
        if not config:
            print(f"{Colors.YELLOW}Warning: Config file {args.config} not found, using defaults{Colors.END}")
            config = DeploymentConfig(project_id="toms-gym", region="us-east1")
            
        # Override config with command line arguments
        if args.api_url:
            config.api_url = args.api_url
            
        config.force_refresh = args.force_refresh
        
        # Create deployment manager and run deployment
        manager = DeploymentManager(config, mode)
        asyncio.run(manager.run())
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.END}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 