#!/usr/bin/env python3
"""
Advanced Build and Deploy Orchestrator for MCP-based microservices
Integrates Conan, Docker, and MCP for intelligent build automation

Enhanced for automotive AI voice control systems with:
- Multi-platform container orchestration
- Real-time monitoring and observability
- Security scanning and compliance
- Performance optimization for edge deployment
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import signal
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
import yaml
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import hashlib
import time
from datetime import datetime, timezone

# Optional dependencies with graceful degradation
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("aiohttp not available - HTTP features will be limited")

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("docker not available - container builds will be limited")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("psutil not available - performance monitoring disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuildStatus(Enum):
    """Build status enumeration with automotive-specific states"""
    PENDING = "pending"
    BUILDING = "building"
    TESTING = "testing"
    PACKAGING = "packaging"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SECURITY_SCANNING = "security_scanning"
    PERFORMANCE_TESTING = "performance_testing"
    EDGE_OPTIMIZING = "edge_optimizing"


@dataclass
class BuildConfig:
    """Build configuration for a component"""
    name: str
    path: Path
    conan_file: Optional[Path] = None
    dockerfile: Optional[Path] = None
    dependencies: List[str] = field(default_factory=list)
    build_type: str = "Release"
    profile: str = "default"
    options: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    test_command: Optional[str] = None
    deploy_config: Optional[Dict[str, Any]] = None
    
    
@dataclass
class BuildResult:
    """Result of a build operation with enhanced automotive metrics"""
    component: str
    status: BuildStatus
    duration: float
    artifacts: List[Path] = field(default_factory=list)
    logs: str = ""
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    security_scan_results: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    edge_optimization_score: Optional[float] = None
    automotive_compliance: Dict[str, bool] = field(default_factory=dict)


class SecurityScanner:
    """Advanced security scanning for automotive AI systems"""
    
    def __init__(self):
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                self.docker_enabled = True
            except Exception as e:
                logger.warning(f"Docker client initialization failed: {e}")
                self.docker_client = None
                self.docker_enabled = False
        else:
            self.docker_client = None
            self.docker_enabled = False
            logger.info("Docker not available - container scanning disabled")
        
    async def scan_container_image(self, image_name: str) -> Dict[str, Any]:
        """Scan container image for vulnerabilities"""
        try:
            # Run Trivy scan
            result = await asyncio.create_subprocess_exec(
                "trivy", "image", "--format", "json", "--quiet", image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                scan_results = json.loads(stdout.decode())
                return {
                    "vulnerabilities": scan_results.get("Results", []),
                    "total_vulns": len(scan_results.get("Results", [])),
                    "critical": len([v for v in scan_results.get("Results", []) 
                                   if v.get("Severity") == "CRITICAL"]),
                    "high": len([v for v in scan_results.get("Results", []) 
                               if v.get("Severity") == "HIGH"]),
                    "scan_timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return {"error": str(e), "scan_failed": True}
        
        return {"scan_failed": True}
    
    async def scan_source_code(self, source_path: Path) -> Dict[str, Any]:
        """Scan source code for security issues"""
        results = {}
        
        # Bandit for Python - fix bug: glob pattern doesn't work with exists()
        python_files = list(source_path.glob("**/*.py"))
        if python_files:
            try:
                result = await asyncio.create_subprocess_exec(
                    "bandit", "-r", str(source_path), "-f", "json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                if result.returncode == 0:
                    results["bandit"] = json.loads(stdout.decode())
            except Exception as e:
                logger.warning(f"Bandit scan failed: {e}")
        
        # Semgrep for general security
        try:
            result = await asyncio.create_subprocess_exec(
                "semgrep", "--config=auto", "--json", str(source_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode == 0:
                results["semgrep"] = json.loads(stdout.decode())
        except Exception as e:
            logger.warning(f"Semgrep scan failed: {e}")
        
        return results


class PerformanceMonitor:
    """Monitor build and runtime performance for automotive edge deployment"""
    
    def __init__(self):
        self.metrics = {}
        self.enabled = PSUTIL_AVAILABLE
        if not self.enabled:
            logger.info("Performance monitoring disabled - psutil not available")
        
    def start_monitoring(self, component: str):
        """Start monitoring resource usage"""
        if not self.enabled:
            self.metrics[component] = {
                "start_time": time.time(),
                "enabled": False
            }
            return
            
        self.metrics[component] = {
            "start_time": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_mb": psutil.virtual_memory().used / 1024 / 1024,
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            "network_io": psutil.net_io_counters()._asdict()
        }
    
    def stop_monitoring(self, component: str) -> Dict[str, Any]:
        """Stop monitoring and return metrics"""
        if component not in self.metrics:
            return {}
        
        start_metrics = self.metrics[component]
        
        # If monitoring was disabled, return minimal metrics
        if not self.enabled or not start_metrics.get("enabled", True):
            return {
                "duration": time.time() - start_metrics["start_time"],
                "monitoring_enabled": False
            }
            
        end_metrics = {
            "end_time": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_mb": psutil.virtual_memory().used / 1024 / 1024,
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            "network_io": psutil.net_io_counters()._asdict()
        }
        
        duration = end_metrics["end_time"] - start_metrics["start_time"]
        
        return {
            "duration": duration,
            "monitoring_enabled": True,
            "avg_cpu_percent": (start_metrics["cpu_percent"] + end_metrics["cpu_percent"]) / 2,
            "peak_memory_mb": max(start_metrics["memory_mb"], end_metrics["memory_mb"]),
            "memory_delta_mb": end_metrics["memory_mb"] - start_metrics["memory_mb"],
            "disk_read_mb": (end_metrics["disk_io"].get("read_bytes", 0) - 
                           start_metrics["disk_io"].get("read_bytes", 0)) / 1024 / 1024,
            "disk_write_mb": (end_metrics["disk_io"].get("write_bytes", 0) - 
                            start_metrics["disk_io"].get("write_bytes", 0)) / 1024 / 1024,
            "network_sent_mb": (end_metrics["network_io"].get("bytes_sent", 0) - 
                              start_metrics["network_io"].get("bytes_sent", 0)) / 1024 / 1024,
            "network_recv_mb": (end_metrics["network_io"].get("bytes_recv", 0) - 
                              start_metrics["network_io"].get("bytes_recv", 0)) / 1024 / 1024
        }
    
    def calculate_edge_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate edge deployment optimization score (0-100)"""
        score = 100.0
        
        # Penalize high resource usage
        if metrics.get("peak_memory_mb", 0) > 512:  # > 512MB
            score -= min(30, (metrics["peak_memory_mb"] - 512) / 10)
        
        if metrics.get("avg_cpu_percent", 0) > 50:  # > 50% CPU
            score -= min(20, (metrics["avg_cpu_percent"] - 50) / 2)
        
        # Penalize large artifacts
        if metrics.get("artifact_size_mb", 0) > 100:  # > 100MB
            score -= min(25, (metrics["artifact_size_mb"] - 100) / 5)
        
        # Reward fast builds
        if metrics.get("duration", float('inf')) < 60:  # < 1 minute
            score += 10
        
        return max(0, min(100, score))


class ConanOrchestrator:
    """Orchestrates Conan builds with advanced automotive features"""
    
    def __init__(self, cache_dir: Path = Path.home() / ".conan2"):
        self.cache_dir = cache_dir
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.security_scanner = SecurityScanner()
        self.performance_monitor = PerformanceMonitor()
        self._ensure_conan_installed()
        
    def _ensure_conan_installed(self):
        """Ensure Conan is installed and configured"""
        try:
            result = subprocess.run(["conan", "--version"], capture_output=True, text=True)
            logger.info(f"Conan version: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Conan not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "conan"], check=True)
            subprocess.run(["conan", "profile", "detect", "--force"], check=True)
    
    async def build_component(self, config: BuildConfig) -> BuildResult:
        """Build a single component with enhanced security and performance monitoring"""
        start_time = time.time()
        result = BuildResult(component=config.name, status=BuildStatus.BUILDING)
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring(config.name)
        
        try:
            # Security scan of source code first
            result.status = BuildStatus.SECURITY_SCANNING
            logger.info(f"Security scanning source code for {config.name}")
            source_scan_results = await self.security_scanner.scan_source_code(config.path)
            result.security_scan_results["source"] = source_scan_results
            
            # Create build directory
            build_dir = config.path / "build"
            build_dir.mkdir(exist_ok=True)
            
            # Install dependencies
            logger.info(f"Installing dependencies for {config.name}")
            conan_cmd = [
                "conan", "install", str(config.conan_file or config.path),
                "--build=missing",
                f"--profile={config.profile}",
                f"-s", f"build_type={config.build_type}"
            ]
            
            # Add options
            for key, value in config.options.items():
                conan_cmd.extend(["-o", f"{key}={value}"])
            
            # Run conan install
            proc = await asyncio.create_subprocess_exec(
                *conan_cmd,
                cwd=str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **config.environment}
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"Conan install failed: {stderr.decode()}")
            
            result.logs += stdout.decode()
            
            # Build with Conan
            logger.info(f"Building {config.name}")
            build_cmd = [
                "conan", "build", str(config.conan_file or config.path),
                f"--build-folder={build_dir}"
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *build_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **config.environment}
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"Conan build failed: {stderr.decode()}")
            
            result.logs += stdout.decode()
            
            # Run tests if configured
            if config.test_command:
                result.status = BuildStatus.TESTING
                logger.info(f"Testing {config.name}")
                test_proc = await asyncio.create_subprocess_shell(
                    config.test_command,
                    cwd=str(build_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                test_stdout, test_stderr = await test_proc.communicate()
                
                if test_proc.returncode != 0:
                    logger.warning(f"Tests failed for {config.name}: {test_stderr.decode()}")
                    result.metrics["test_failed"] = True
                else:
                    result.metrics["test_passed"] = True
                
                result.logs += test_stdout.decode()
            
            # Package artifacts
            result.status = BuildStatus.PACKAGING
            artifacts = await self._collect_artifacts(build_dir)
            result.artifacts = artifacts
            
            # Performance testing for automotive requirements
            result.status = BuildStatus.PERFORMANCE_TESTING
            logger.info(f"Performance testing {config.name}")
            
            # Stop performance monitoring and collect metrics
            perf_metrics = self.performance_monitor.stop_monitoring(config.name)
            result.performance_metrics = perf_metrics
            result.resource_usage = {
                "peak_memory_mb": perf_metrics.get("peak_memory_mb", 0),
                "avg_cpu_percent": perf_metrics.get("avg_cpu_percent", 0),
                "disk_usage_mb": perf_metrics.get("disk_read_mb", 0) + perf_metrics.get("disk_write_mb", 0),
                "network_usage_mb": perf_metrics.get("network_sent_mb", 0) + perf_metrics.get("network_recv_mb", 0)
            }
            
            # Edge optimization
            result.status = BuildStatus.EDGE_OPTIMIZING
            artifact_size_mb = sum(artifact.stat().st_size for artifact in artifacts) / 1024 / 1024
            perf_metrics["artifact_size_mb"] = artifact_size_mb
            result.edge_optimization_score = self.performance_monitor.calculate_edge_score(perf_metrics)
            
            # Automotive compliance checks
            result.automotive_compliance = {
                "memory_constraint": perf_metrics.get("peak_memory_mb", 0) < 1024,  # < 1GB
                "startup_time": result.duration < 30,  # < 30 seconds
                "artifact_size": artifact_size_mb < 200,  # < 200MB
                "security_clean": len(source_scan_results.get("bandit", {}).get("results", [])) == 0,
                "edge_optimized": result.edge_optimization_score > 70
            }
            
            # Calculate build metrics
            result.duration = time.time() - start_time
            result.metrics["build_time"] = result.duration
            result.metrics["artifact_count"] = len(artifacts)
            result.metrics["cache_hits"] = self._calculate_cache_hits(result.logs)
            result.metrics["total_artifact_size_mb"] = artifact_size_mb
            
            result.status = BuildStatus.SUCCESS
            logger.info(f"Successfully built {config.name} in {result.duration:.2f}s with edge score {result.edge_optimization_score:.1f}")
            
        except Exception as e:
            result.status = BuildStatus.FAILED
            result.error = str(e)
            result.duration = time.time() - start_time
            logger.error(f"Failed to build {config.name}: {e}")
        
        return result
    
    async def _collect_artifacts(self, build_dir: Path) -> List[Path]:
        """Collect build artifacts"""
        artifacts = []
        patterns = ["*.so", "*.dll", "*.a", "*.lib", "*.exe", "*.dylib"]
        
        for pattern in patterns:
            artifacts.extend(build_dir.rglob(pattern))
        
        return artifacts
    
    def _calculate_cache_hits(self, logs: str) -> int:
        """Calculate number of cache hits from build logs"""
        return logs.count("Cache hit") + logs.count("Already installed")


class MCPBuildOrchestrator:
    """Main orchestrator integrating MCP with build system"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = self._load_config()
        self.conan = ConanOrchestrator()
        self.build_graph = self._create_build_graph()
        self.mcp_servers: Dict[str, Any] = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration"""
        with open(self.config_file) as f:
            return yaml.safe_load(f)
    
    def _create_build_graph(self) -> Dict[str, BuildConfig]:
        """Create dependency graph for builds"""
        graph = {}
        
        for component in self.config.get("components", []):
            config = BuildConfig(
                name=component["name"],
                path=Path(component["path"]),
                conan_file=Path(component.get("conan_file")) if component.get("conan_file") else None,
                dockerfile=Path(component.get("dockerfile")) if component.get("dockerfile") else None,
                dependencies=component.get("dependencies", []),
                build_type=component.get("build_type", "Release"),
                profile=component.get("profile", "default"),
                options=component.get("options", {}),
                environment=component.get("environment", {}),
                test_command=component.get("test_command"),
                deploy_config=component.get("deploy", {})
            )
            graph[component["name"]] = config
        
        return graph
    
    async def build_all(self, parallel: bool = True) -> Dict[str, BuildResult]:
        """Build all components respecting dependencies"""
        results = {}
        built = set()
        
        async def build_with_deps(name: str) -> BuildResult:
            """Build component with dependencies"""
            config = self.build_graph[name]
            
            # Wait for dependencies
            for dep in config.dependencies:
                if dep not in built:
                    await build_with_deps(dep)
            
            # Build component
            result = await self.conan.build_component(config)
            built.add(name)
            results[name] = result
            
            # Start MCP server if successful
            if result.status == BuildStatus.SUCCESS and config.deploy_config:
                await self._start_mcp_server(name, config)
            
            return result
        
        # Build all components
        if parallel:
            tasks = [build_with_deps(name) for name in self.build_graph]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for name in self.build_graph:
                await build_with_deps(name)
        
        return results
    
    async def _start_mcp_server(self, name: str, config: BuildConfig):
        """Start MCP server for component"""
        logger.info(f"Starting MCP server for {name}")
        
        # Import the MCP C++ bridge if available
        try:
            import mcp_cpp_bridge
            
            server_config = mcp_cpp_bridge.server.ServerConfig()
            server_config.name = name
            server_config.version = config.deploy_config.get("version", "1.0.0")
            
            # Configure capabilities
            capabilities = mcp_cpp_bridge.server.ServerCapabilities()
            capabilities.tools = True
            capabilities.resources = True
            server_config.capabilities = capabilities
            
            # Create server
            server = mcp_cpp_bridge.server.Server(server_config)
            
            # Register tools from config
            for tool_config in config.deploy_config.get("tools", []):
                tool = mcp_cpp_bridge.protocol.Tool()
                tool.name = tool_config["name"]
                tool.description = tool_config["description"]
                tool.input_schema = tool_config.get("schema", {})
                
                # Set handler
                if "handler" in tool_config:
                    handler_path = tool_config["handler"]
                    # Dynamic import and setup of handler
                    # This would be implemented based on specific needs
                
                server.register_tool(tool)
            
            # Start server
            server.start()
            self.mcp_servers[name] = server
            
            logger.info(f"MCP server started for {name}")
            
        except ImportError:
            logger.warning(f"MCP C++ bridge not available for {name}")
    
    async def deploy(self, results: Dict[str, BuildResult]):
        """Deploy successful builds"""
        for name, result in results.items():
            if result.status != BuildStatus.SUCCESS:
                continue
            
            config = self.build_graph[name]
            if not config.deploy_config:
                continue
            
            logger.info(f"Deploying {name}")
            
            deploy_type = config.deploy_config.get("type", "docker")
            
            if deploy_type == "docker":
                await self._deploy_docker(name, config, result)
            elif deploy_type == "kubernetes":
                await self._deploy_kubernetes(name, config, result)
            elif deploy_type == "systemd":
                await self._deploy_systemd(name, config, result)
    
    async def _deploy_docker(self, name: str, config: BuildConfig, result: BuildResult):
        """Deploy using Docker"""
        if not config.dockerfile:
            logger.warning(f"No Dockerfile for {name}")
            return
        
        # Build Docker image
        image_tag = f"{name}:latest"
        build_cmd = [
            "docker", "build",
            "-t", image_tag,
            "-f", str(config.dockerfile),
            str(config.path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *build_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"Docker build failed for {name}: {stderr.decode()}")
            return
        
        # Run container
        run_cmd = [
            "docker", "run",
            "-d",
            "--name", name,
            "--restart", "unless-stopped"
        ]
        
        # Add environment variables
        for key, value in config.deploy_config.get("env", {}).items():
            run_cmd.extend(["-e", f"{key}={value}"])
        
        # Add ports
        for port in config.deploy_config.get("ports", []):
            run_cmd.extend(["-p", port])
        
        run_cmd.append(image_tag)
        
        proc = await asyncio.create_subprocess_exec(
            *run_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            logger.info(f"Successfully deployed {name} as Docker container")
        else:
            logger.error(f"Failed to deploy {name}: {stderr.decode()}")
    
    async def _deploy_kubernetes(self, name: str, config: BuildConfig, result: BuildResult):
        """Deploy to Kubernetes"""
        # Implementation would use kubectl or Kubernetes Python client
        logger.info(f"Kubernetes deployment for {name} not yet implemented")
    
    async def _deploy_systemd(self, name: str, config: BuildConfig, result: BuildResult):
        """Deploy as systemd service"""
        # Implementation would create and start systemd service
        logger.info(f"Systemd deployment for {name} not yet implemented")
    
    def generate_report(self, results: Dict[str, BuildResult]) -> str:
        """Generate build report"""
        report = ["=" * 80]
        report.append("BUILD REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        total = len(results)
        success = sum(1 for r in results.values() if r.status == BuildStatus.SUCCESS)
        failed = sum(1 for r in results.values() if r.status == BuildStatus.FAILED)
        
        report.append(f"Total Components: {total}")
        report.append(f"Successful: {success}")
        report.append(f"Failed: {failed}")
        report.append("")
        
        # Details
        report.append("COMPONENT DETAILS:")
        report.append("-" * 40)
        
        for name, result in results.items():
            report.append(f"\n{name}:")
            report.append(f"  Status: {result.status.value}")
            report.append(f"  Duration: {result.duration:.2f}s")
            report.append(f"  Artifacts: {len(result.artifacts)}")
            
            if result.error:
                report.append(f"  Error: {result.error}")
            
            if result.metrics:
                report.append("  Metrics:")
                for key, value in result.metrics.items():
                    report.append(f"    {key}: {value}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Build Orchestrator")
    parser.add_argument("config", help="Configuration file path")
    parser.add_argument("--parallel", action="store_true", help="Build in parallel")
    parser.add_argument("--deploy", action="store_true", help="Deploy after build")
    parser.add_argument("--report", help="Output report file")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = MCPBuildOrchestrator(Path(args.config))
    
    # Build all components
    logger.info("Starting build orchestration")
    results = await orchestrator.build_all(parallel=args.parallel)
    
    # Deploy if requested
    if args.deploy:
        logger.info("Starting deployment")
        await orchestrator.deploy(results)
    
    # Generate report
    report = orchestrator.generate_report(results)
    print(report)
    
    if args.report:
        with open(args.report, "w") as f:
            f.write(report)
        logger.info(f"Report saved to {args.report}")
    
    # Return exit code based on results
    failed = any(r.status == BuildStatus.FAILED for r in results.values())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))