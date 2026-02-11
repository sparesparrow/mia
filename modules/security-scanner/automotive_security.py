#!/usr/bin/env python3
"""
🔒 MIA Universal: Automotive Security Scanner

Comprehensive security monitoring and vulnerability assessment specifically
designed for automotive AI systems with ISO 26262 compliance and
real-time threat detection.
"""

import asyncio
import json
import logging
import hashlib
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import aiohttp
import docker
from datetime import datetime, timedelta
import ssl
import socket
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityThreatLevel(Enum):
    """Security threat levels for automotive systems"""
    CRITICAL = "critical"      # Immediate safety risk
    HIGH = "high"             # Security breach risk
    MEDIUM = "medium"         # Potential vulnerability
    LOW = "low"              # Informational
    INFO = "info"            # General security info


class AutomotiveSecurityStandard(Enum):
    """Automotive security standards compliance"""
    ISO_26262 = "iso_26262"           # Functional safety
    ISO_21434 = "iso_21434"           # Cybersecurity
    UNECE_WP29 = "unece_wp29"         # Vehicle type approval
    SAE_J3061 = "sae_j3061"           # Cybersecurity guidebook


@dataclass
class SecurityVulnerability:
    """Security vulnerability information"""
    id: str
    title: str
    description: str
    severity: SecurityThreatLevel
    cve_id: Optional[str] = None
    component: str = "unknown"
    automotive_impact: str = "unknown"
    mitigation: str = ""
    compliance_standards: List[AutomotiveSecurityStandard] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class SecurityScanResult:
    """Result of a security scan"""
    scan_id: str
    scan_type: str
    target: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    vulnerabilities: List[SecurityVulnerability] = field(default_factory=list)
    compliance_score: float = 0.0
    automotive_safety_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    scan_successful: bool = True
    error_message: Optional[str] = None


class AutomotiveSecurityScanner:
    """Comprehensive security scanner for automotive AI systems"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.docker_client = docker.from_env()
        self.scan_results: List[SecurityScanResult] = []
        self.active_threats: List[SecurityVulnerability] = []
        
        # Automotive-specific configuration
        self.iso_26262_enabled = config.get("iso_26262_compliance", True)
        self.real_time_monitoring = config.get("real_time_monitoring", True)
        self.automotive_threat_db = config.get("automotive_threat_db", "automotive_threats.json")
        
        # Security tools configuration
        self.security_tools = {
            "trivy": {"enabled": True, "timeout": 300},
            "bandit": {"enabled": True, "timeout": 120},
            "semgrep": {"enabled": True, "timeout": 180},
            "nmap": {"enabled": True, "timeout": 600},
            "owasp_zap": {"enabled": False, "timeout": 1800}  # Disabled by default for performance
        }

    async def scan_container_image(self, image_name: str) -> SecurityScanResult:
        """Scan container image for automotive-specific vulnerabilities"""
        scan_id = f"container_{int(time.time())}"
        logger.info(f"🔍 Starting container security scan: {image_name}")
        
        result = SecurityScanResult(
            scan_id=scan_id,
            scan_type="container_image",
            target=image_name,
            start_time=datetime.now()
        )
        
        try:
            # Trivy vulnerability scan
            if self.security_tools["trivy"]["enabled"]:
                trivy_vulns = await self._run_trivy_scan(image_name)
                result.vulnerabilities.extend(trivy_vulns)
            
            # Custom automotive vulnerability checks
            automotive_vulns = await self._check_automotive_vulnerabilities(image_name)
            result.vulnerabilities.extend(automotive_vulns)
            
            # Calculate compliance scores
            result.compliance_score = self._calculate_compliance_score(result.vulnerabilities)
            result.automotive_safety_score = self._calculate_automotive_safety_score(result.vulnerabilities)
            
            # Generate recommendations
            result.recommendations = self._generate_security_recommendations(result.vulnerabilities)
            
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            logger.info(f"✅ Container scan completed: {len(result.vulnerabilities)} vulnerabilities found")
            
        except Exception as e:
            result.scan_successful = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"❌ Container scan failed: {e}")
        
        self.scan_results.append(result)
        return result

    async def scan_source_code(self, source_path: Path) -> SecurityScanResult:
        """Scan source code for security vulnerabilities"""
        scan_id = f"source_{int(time.time())}"
        logger.info(f"🔍 Starting source code security scan: {source_path}")
        
        result = SecurityScanResult(
            scan_id=scan_id,
            scan_type="source_code",
            target=str(source_path),
            start_time=datetime.now()
        )
        
        try:
            # Bandit scan for Python
            if self.security_tools["bandit"]["enabled"]:
                bandit_vulns = await self._run_bandit_scan(source_path)
                result.vulnerabilities.extend(bandit_vulns)
            
            # Semgrep scan for multiple languages
            if self.security_tools["semgrep"]["enabled"]:
                semgrep_vulns = await self._run_semgrep_scan(source_path)
                result.vulnerabilities.extend(semgrep_vulns)
            
            # Custom automotive security patterns
            automotive_code_vulns = await self._check_automotive_code_patterns(source_path)
            result.vulnerabilities.extend(automotive_code_vulns)
            
            # Calculate scores
            result.compliance_score = self._calculate_compliance_score(result.vulnerabilities)
            result.automotive_safety_score = self._calculate_automotive_safety_score(result.vulnerabilities)
            
            result.recommendations = self._generate_security_recommendations(result.vulnerabilities)
            
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            logger.info(f"✅ Source code scan completed: {len(result.vulnerabilities)} issues found")
            
        except Exception as e:
            result.scan_successful = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"❌ Source code scan failed: {e}")
        
        self.scan_results.append(result)
        return result

    async def scan_network_services(self, target_host: str = "localhost") -> SecurityScanResult:
        """Scan network services for automotive security vulnerabilities"""
        scan_id = f"network_{int(time.time())}"
        logger.info(f"🔍 Starting network security scan: {target_host}")
        
        result = SecurityScanResult(
            scan_id=scan_id,
            scan_type="network_services",
            target=target_host,
            start_time=datetime.now()
        )
        
        try:
            # Port scan with nmap
            if self.security_tools["nmap"]["enabled"]:
                network_vulns = await self._run_nmap_scan(target_host)
                result.vulnerabilities.extend(network_vulns)
            
            # Check automotive-specific ports and services
            automotive_services = await self._check_automotive_services(target_host)
            result.vulnerabilities.extend(automotive_services)
            
            # SSL/TLS security check
            ssl_vulns = await self._check_ssl_security(target_host)
            result.vulnerabilities.extend(ssl_vulns)
            
            result.compliance_score = self._calculate_compliance_score(result.vulnerabilities)
            result.automotive_safety_score = self._calculate_automotive_safety_score(result.vulnerabilities)
            result.recommendations = self._generate_security_recommendations(result.vulnerabilities)
            
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            logger.info(f"✅ Network scan completed: {len(result.vulnerabilities)} issues found")
            
        except Exception as e:
            result.scan_successful = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"❌ Network scan failed: {e}")
        
        self.scan_results.append(result)
        return result

    async def _run_trivy_scan(self, image_name: str) -> List[SecurityVulnerability]:
        """Run Trivy vulnerability scanner"""
        vulnerabilities = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "trivy", "image", "--format", "json", "--quiet", image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                trivy_results = json.loads(stdout.decode())
                
                for result in trivy_results.get("Results", []):
                    for vuln in result.get("Vulnerabilities", []):
                        vulnerability = SecurityVulnerability(
                            id=f"trivy_{vuln.get('VulnerabilityID', 'unknown')}",
                            title=vuln.get("Title", "Unknown vulnerability"),
                            description=vuln.get("Description", ""),
                            severity=self._map_severity(vuln.get("Severity", "UNKNOWN")),
                            cve_id=vuln.get("VulnerabilityID"),
                            component=vuln.get("PkgName", "unknown"),
                            automotive_impact=self._assess_automotive_impact(vuln),
                            compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                        )
                        vulnerabilities.append(vulnerability)
            
        except Exception as e:
            logger.error(f"Trivy scan failed: {e}")
        
        return vulnerabilities

    async def _run_bandit_scan(self, source_path: Path) -> List[SecurityVulnerability]:
        """Run Bandit security scanner for Python code"""
        vulnerabilities = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "bandit", "-r", str(source_path), "-f", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode in [0, 1]:  # Bandit returns 1 when issues found
                bandit_results = json.loads(stdout.decode())
                
                for result in bandit_results.get("results", []):
                    vulnerability = SecurityVulnerability(
                        id=f"bandit_{result.get('test_id', 'unknown')}",
                        title=result.get("test_name", "Python security issue"),
                        description=result.get("issue_text", ""),
                        severity=self._map_bandit_severity(result.get("issue_severity", "LOW")),
                        component=result.get("filename", "unknown"),
                        automotive_impact=self._assess_python_automotive_impact(result),
                        compliance_standards=[AutomotiveSecurityStandard.ISO_26262, AutomotiveSecurityStandard.ISO_21434]
                    )
                    vulnerabilities.append(vulnerability)
            
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
        
        return vulnerabilities

    async def _run_semgrep_scan(self, source_path: Path) -> List[SecurityVulnerability]:
        """Run Semgrep security scanner"""
        vulnerabilities = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "semgrep", "--config=auto", "--json", str(source_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                semgrep_results = json.loads(stdout.decode())
                
                for result in semgrep_results.get("results", []):
                    vulnerability = SecurityVulnerability(
                        id=f"semgrep_{result.get('check_id', 'unknown')}",
                        title=result.get("message", "Security pattern detected"),
                        description=f"File: {result.get('path', 'unknown')}, Line: {result.get('start', {}).get('line', 'unknown')}",
                        severity=self._map_semgrep_severity(result.get("extra", {}).get("severity", "INFO")),
                        component=result.get("path", "unknown"),
                        automotive_impact="Code pattern may affect automotive safety",
                        compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                    )
                    vulnerabilities.append(vulnerability)
            
        except Exception as e:
            logger.error(f"Semgrep scan failed: {e}")
        
        return vulnerabilities

    async def _run_nmap_scan(self, target_host: str) -> List[SecurityVulnerability]:
        """Run Nmap network security scan"""
        vulnerabilities = []
        
        try:
            # Basic port scan
            proc = await asyncio.create_subprocess_exec(
                "nmap", "-sV", "-sC", "-oX", "-", target_host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                # Parse nmap XML output (simplified)
                nmap_output = stdout.decode()
                
                # Check for common automotive vulnerabilities
                if "22/tcp open" in nmap_output:
                    vulnerabilities.append(SecurityVulnerability(
                        id="nmap_ssh_open",
                        title="SSH service exposed",
                        description="SSH service is accessible, ensure proper authentication",
                        severity=SecurityThreatLevel.MEDIUM,
                        component="ssh",
                        automotive_impact="Remote access to automotive system possible",
                        compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                    ))
                
                if "80/tcp open" in nmap_output and "443/tcp" not in nmap_output:
                    vulnerabilities.append(SecurityVulnerability(
                        id="nmap_http_no_https",
                        title="HTTP without HTTPS",
                        description="Web service running on HTTP without HTTPS encryption",
                        severity=SecurityThreatLevel.HIGH,
                        component="web_server",
                        automotive_impact="Unencrypted communication in automotive system",
                        compliance_standards=[AutomotiveSecurityStandard.ISO_21434, AutomotiveSecurityStandard.UNECE_WP29]
                    ))
            
        except Exception as e:
            logger.error(f"Nmap scan failed: {e}")
        
        return vulnerabilities

    async def _check_automotive_vulnerabilities(self, image_name: str) -> List[SecurityVulnerability]:
        """Check for automotive-specific vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Inspect Docker image
            image = self.docker_client.images.get(image_name)
            config = image.attrs.get("Config", {})
            
            # Check for automotive-specific security issues
            
            # 1. Check if running as root (critical for automotive)
            user = config.get("User")
            if not user or user == "root" or user == "0":
                vulnerabilities.append(SecurityVulnerability(
                    id="automotive_root_user",
                    title="Container running as root user",
                    description="Container is configured to run as root, violating automotive security principles",
                    severity=SecurityThreatLevel.CRITICAL,
                    component="container_config",
                    automotive_impact="Root access in automotive system poses safety risk",
                    compliance_standards=[AutomotiveSecurityStandard.ISO_26262, AutomotiveSecurityStandard.ISO_21434]
                ))
            
            # 2. Check for exposed automotive ports
            exposed_ports = config.get("ExposedPorts", {})
            automotive_ports = ["1883/tcp", "5555/tcp", "8080/tcp", "50051/tcp"]  # MQTT, ZMQ, HTTP, gRPC
            
            for port in automotive_ports:
                if port in exposed_ports:
                    vulnerabilities.append(SecurityVulnerability(
                        id=f"automotive_port_{port.replace('/', '_')}",
                        title=f"Automotive service port exposed: {port}",
                        description=f"Port {port} is exposed, ensure proper access controls",
                        severity=SecurityThreatLevel.MEDIUM,
                        component="network_config",
                        automotive_impact="Automotive service accessible without proper authentication",
                        compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                    ))
            
            # 3. Check environment variables for secrets
            env_vars = config.get("Env", [])
            for env_var in env_vars:
                if any(secret in env_var.upper() for secret in ["PASSWORD", "SECRET", "KEY", "TOKEN"]):
                    vulnerabilities.append(SecurityVulnerability(
                        id="automotive_env_secrets",
                        title="Secrets in environment variables",
                        description="Sensitive information found in environment variables",
                        severity=SecurityThreatLevel.HIGH,
                        component="container_config",
                        automotive_impact="Automotive system credentials exposed",
                        compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                    ))
            
        except Exception as e:
            logger.error(f"Automotive vulnerability check failed: {e}")
        
        return vulnerabilities

    async def _check_automotive_code_patterns(self, source_path: Path) -> List[SecurityVulnerability]:
        """Check for automotive-specific insecure code patterns"""
        vulnerabilities = []
        
        try:
            # Search for automotive-specific security anti-patterns
            automotive_patterns = [
                {
                    "pattern": r"time\.sleep\(\s*[0-9]+\s*\)",
                    "title": "Blocking sleep in automotive code",
                    "severity": SecurityThreatLevel.MEDIUM,
                    "impact": "Blocking operations can affect real-time automotive responses"
                },
                {
                    "pattern": r"subprocess\.call\(",
                    "title": "Unsafe subprocess call",
                    "severity": SecurityThreatLevel.HIGH,
                    "impact": "Unsafe subprocess execution in automotive system"
                },
                {
                    "pattern": r"eval\(",
                    "title": "Dynamic code execution",
                    "severity": SecurityThreatLevel.CRITICAL,
                    "impact": "Code injection vulnerability in automotive system"
                }
            ]
            
            for py_file in source_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for pattern_info in automotive_patterns:
                        import re
                        if re.search(pattern_info["pattern"], content):
                            vulnerabilities.append(SecurityVulnerability(
                                id=f"automotive_pattern_{hashlib.md5(pattern_info['pattern'].encode()).hexdigest()[:8]}",
                                title=pattern_info["title"],
                                description=f"Found in {py_file}",
                                severity=pattern_info["severity"],
                                component=str(py_file),
                                automotive_impact=pattern_info["impact"],
                                compliance_standards=[AutomotiveSecurityStandard.ISO_26262]
                            ))
                            
                except Exception as e:
                    logger.warning(f"Could not scan file {py_file}: {e}")
            
        except Exception as e:
            logger.error(f"Automotive code pattern check failed: {e}")
        
        return vulnerabilities

    async def _check_automotive_services(self, target_host: str) -> List[SecurityVulnerability]:
        """Check automotive-specific services and protocols"""
        vulnerabilities = []
        
        # Check for automotive communication protocols
        automotive_services = {
            1883: "MQTT (unsecured)",
            8883: "MQTT (secured)",
            5555: "ZeroMQ",
            50051: "gRPC",
            8080: "HTTP API",
            8443: "HTTPS API"
        }
        
        for port, service in automotive_services.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((target_host, port))
                sock.close()
                
                if result == 0:  # Port is open
                    severity = SecurityThreatLevel.INFO
                    impact = f"Automotive service {service} is accessible"
                    
                    # Assess security based on service type
                    if port in [1883, 8080]:  # Unsecured protocols
                        severity = SecurityThreatLevel.HIGH
                        impact = f"Unsecured automotive service {service} accessible"
                    
                    vulnerabilities.append(SecurityVulnerability(
                        id=f"automotive_service_{port}",
                        title=f"Automotive service detected: {service}",
                        description=f"Service {service} is running on port {port}",
                        severity=severity,
                        component=f"service_{port}",
                        automotive_impact=impact,
                        compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                    ))
                    
            except Exception as e:
                logger.debug(f"Could not check port {port}: {e}")
        
        return vulnerabilities

    async def _check_ssl_security(self, target_host: str) -> List[SecurityVulnerability]:
        """Check SSL/TLS security configuration"""
        vulnerabilities = []
        
        ssl_ports = [443, 8443, 8883]  # HTTPS, secure MQTT
        
        for port in ssl_ports:
            try:
                context = ssl.create_default_context()
                
                with socket.create_connection((target_host, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=target_host) as ssock:
                        cert = ssock.getpeercert()
                        cipher = ssock.cipher()
                        
                        # Check certificate validity
                        not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        if not_after < datetime.now() + timedelta(days=30):
                            vulnerabilities.append(SecurityVulnerability(
                                id=f"ssl_cert_expiry_{port}",
                                title=f"SSL certificate expiring soon on port {port}",
                                description=f"Certificate expires on {not_after}",
                                severity=SecurityThreatLevel.HIGH,
                                component=f"ssl_port_{port}",
                                automotive_impact="SSL certificate expiry will break automotive communications",
                                compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                            ))
                        
                        # Check cipher strength
                        if cipher and cipher[1] < 256:  # Key length less than 256 bits
                            vulnerabilities.append(SecurityVulnerability(
                                id=f"ssl_weak_cipher_{port}",
                                title=f"Weak SSL cipher on port {port}",
                                description=f"Using cipher with {cipher[1]} bit key",
                                severity=SecurityThreatLevel.MEDIUM,
                                component=f"ssl_port_{port}",
                                automotive_impact="Weak encryption may be vulnerable to attacks",
                                compliance_standards=[AutomotiveSecurityStandard.ISO_21434]
                            ))
                            
            except (socket.timeout, ConnectionRefusedError, ssl.SSLError):
                # Service not available or SSL not configured
                continue
            except Exception as e:
                logger.debug(f"SSL check failed for port {port}: {e}")
        
        return vulnerabilities

    def _map_severity(self, severity: str) -> SecurityThreatLevel:
        """Map external severity levels to automotive threat levels"""
        severity_map = {
            "CRITICAL": SecurityThreatLevel.CRITICAL,
            "HIGH": SecurityThreatLevel.HIGH,
            "MEDIUM": SecurityThreatLevel.MEDIUM,
            "LOW": SecurityThreatLevel.LOW,
            "UNKNOWN": SecurityThreatLevel.INFO,
            "NEGLIGIBLE": SecurityThreatLevel.INFO
        }
        return severity_map.get(severity.upper(), SecurityThreatLevel.INFO)

    def _map_bandit_severity(self, severity: str) -> SecurityThreatLevel:
        """Map Bandit severity to automotive threat levels"""
        severity_map = {
            "HIGH": SecurityThreatLevel.HIGH,
            "MEDIUM": SecurityThreatLevel.MEDIUM,
            "LOW": SecurityThreatLevel.LOW
        }
        return severity_map.get(severity.upper(), SecurityThreatLevel.INFO)

    def _map_semgrep_severity(self, severity: str) -> SecurityThreatLevel:
        """Map Semgrep severity to automotive threat levels"""
        severity_map = {
            "ERROR": SecurityThreatLevel.HIGH,
            "WARNING": SecurityThreatLevel.MEDIUM,
            "INFO": SecurityThreatLevel.LOW
        }
        return severity_map.get(severity.upper(), SecurityThreatLevel.INFO)

    def _assess_automotive_impact(self, vuln: Dict[str, Any]) -> str:
        """Assess automotive impact of a vulnerability"""
        pkg_name = vuln.get("PkgName", "").lower()
        description = vuln.get("Description", "").lower()
        
        # High impact packages for automotive
        critical_packages = ["openssl", "curl", "systemd", "kernel", "glibc"]
        network_packages = ["nginx", "apache", "mqtt", "grpc"]
        
        if any(pkg in pkg_name for pkg in critical_packages):
            return "Critical automotive system component affected"
        elif any(pkg in pkg_name for pkg in network_packages):
            return "Automotive communication component affected"
        elif "remote" in description or "network" in description:
            return "Remote access vulnerability in automotive system"
        else:
            return "General automotive system vulnerability"

    def _assess_python_automotive_impact(self, result: Dict[str, Any]) -> str:
        """Assess automotive impact of Python security issues"""
        test_id = result.get("test_id", "").lower()
        issue_text = result.get("issue_text", "").lower()
        
        if "subprocess" in test_id or "shell" in test_id:
            return "Command injection risk in automotive system"
        elif "sql" in test_id:
            return "SQL injection risk in automotive database"
        elif "hardcoded" in test_id:
            return "Hardcoded credentials in automotive system"
        elif "random" in test_id:
            return "Weak randomness may affect automotive security"
        else:
            return "Python security issue in automotive code"

    def _calculate_compliance_score(self, vulnerabilities: List[SecurityVulnerability]) -> float:
        """Calculate compliance score based on vulnerabilities"""
        if not vulnerabilities:
            return 100.0
        
        total_score = 100.0
        
        for vuln in vulnerabilities:
            # Deduct points based on severity
            if vuln.severity == SecurityThreatLevel.CRITICAL:
                total_score -= 25.0
            elif vuln.severity == SecurityThreatLevel.HIGH:
                total_score -= 15.0
            elif vuln.severity == SecurityThreatLevel.MEDIUM:
                total_score -= 8.0
            elif vuln.severity == SecurityThreatLevel.LOW:
                total_score -= 3.0
        
        return max(0.0, total_score)

    def _calculate_automotive_safety_score(self, vulnerabilities: List[SecurityVulnerability]) -> float:
        """Calculate automotive safety score based on ISO 26262 principles"""
        if not vulnerabilities:
            return 100.0
        
        safety_score = 100.0
        
        for vuln in vulnerabilities:
            # Higher penalty for safety-critical issues
            if AutomotiveSecurityStandard.ISO_26262 in vuln.compliance_standards:
                if vuln.severity == SecurityThreatLevel.CRITICAL:
                    safety_score -= 40.0  # Critical safety issue
                elif vuln.severity == SecurityThreatLevel.HIGH:
                    safety_score -= 20.0
                elif vuln.severity == SecurityThreatLevel.MEDIUM:
                    safety_score -= 10.0
            else:
                # Standard deductions for non-safety issues
                if vuln.severity == SecurityThreatLevel.CRITICAL:
                    safety_score -= 15.0
                elif vuln.severity == SecurityThreatLevel.HIGH:
                    safety_score -= 8.0
                elif vuln.severity == SecurityThreatLevel.MEDIUM:
                    safety_score -= 4.0
        
        return max(0.0, safety_score)

    def _generate_security_recommendations(self, vulnerabilities: List[SecurityVulnerability]) -> List[str]:
        """Generate security recommendations based on found vulnerabilities"""
        recommendations = []
        
        # Group vulnerabilities by type
        vuln_types = {}
        for vuln in vulnerabilities:
            vuln_type = vuln.component
            if vuln_type not in vuln_types:
                vuln_types[vuln_type] = []
            vuln_types[vuln_type].append(vuln)
        
        # Generate recommendations
        if any(v.severity == SecurityThreatLevel.CRITICAL for v in vulnerabilities):
            recommendations.append("🚨 CRITICAL: Address critical vulnerabilities immediately - system not safe for automotive deployment")
        
        if "container_config" in vuln_types:
            recommendations.append("🐳 Configure containers to run as non-root user for automotive security")
        
        if any("ssl" in v.id for v in vulnerabilities):
            recommendations.append("🔒 Update SSL/TLS configuration and certificates for secure automotive communications")
        
        if any("password" in v.description.lower() or "secret" in v.description.lower() for v in vulnerabilities):
            recommendations.append("🔐 Implement proper secrets management for automotive credentials")
        
        if any(AutomotiveSecurityStandard.ISO_26262 in v.compliance_standards for v in vulnerabilities):
            recommendations.append("⚠️ Review ISO 26262 functional safety requirements for identified issues")
        
        if any(AutomotiveSecurityStandard.ISO_21434 in v.compliance_standards for v in vulnerabilities):
            recommendations.append("🛡️ Address ISO 21434 cybersecurity requirements for automotive deployment")
        
        if not recommendations:
            recommendations.append("✅ No critical security issues found - system meets basic automotive security requirements")
        
        return recommendations

    async def generate_security_report(self, output_path: Path = Path("automotive_security_report.json")) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        
        total_vulnerabilities = sum(len(result.vulnerabilities) for result in self.scan_results)
        critical_count = sum(1 for result in self.scan_results for vuln in result.vulnerabilities if vuln.severity == SecurityThreatLevel.CRITICAL)
        high_count = sum(1 for result in self.scan_results for vuln in result.vulnerabilities if vuln.severity == SecurityThreatLevel.HIGH)
        
        # Calculate overall scores
        compliance_scores = [result.compliance_score for result in self.scan_results if result.scan_successful]
        safety_scores = [result.automotive_safety_score for result in self.scan_results if result.scan_successful]
        
        overall_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0
        overall_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 0
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scan_count": len(self.scan_results),
                "total_vulnerabilities": total_vulnerabilities,
                "automotive_optimized": True
            },
            "executive_summary": {
                "overall_compliance_score": round(overall_compliance, 2),
                "overall_safety_score": round(overall_safety, 2),
                "critical_vulnerabilities": critical_count,
                "high_vulnerabilities": high_count,
                "automotive_ready": critical_count == 0 and overall_safety >= 80.0
            },
            "compliance_status": {
                "iso_26262": overall_safety >= 90.0,
                "iso_21434": overall_compliance >= 85.0,
                "unece_wp29": overall_compliance >= 80.0,
                "sae_j3061": overall_compliance >= 75.0
            },
            "scan_results": [
                {
                    "scan_id": result.scan_id,
                    "scan_type": result.scan_type,
                    "target": result.target,
                    "duration_seconds": result.duration_seconds,
                    "vulnerabilities_count": len(result.vulnerabilities),
                    "compliance_score": result.compliance_score,
                    "safety_score": result.automotive_safety_score,
                    "successful": result.scan_successful
                }
                for result in self.scan_results
            ],
            "vulnerabilities": [
                {
                    "id": vuln.id,
                    "title": vuln.title,
                    "severity": vuln.severity.value,
                    "component": vuln.component,
                    "automotive_impact": vuln.automotive_impact,
                    "compliance_standards": [std.value for std in vuln.compliance_standards],
                    "detected_at": vuln.detected_at.isoformat(),
                    "resolved": vuln.resolved
                }
                for result in self.scan_results
                for vuln in result.vulnerabilities
            ],
            "recommendations": list(set(
                rec for result in self.scan_results for rec in result.recommendations
            ))
        }
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Security report saved to {output_path}")
        return report


async def main():
    """Main entry point for automotive security scanner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MIA Automotive Security Scanner")
    parser.add_argument("--scan-type", choices=["container", "source", "network", "all"], default="all")
    parser.add_argument("--target", help="Target to scan (image name, source path, or host)")
    parser.add_argument("--output", default="automotive_security_report.json", help="Output report file")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        "iso_26262_compliance": True,
        "real_time_monitoring": True,
        "automotive_threat_db": "automotive_threats.json"
    }
    
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config.update(json.load(f))
    
    # Initialize scanner
    scanner = AutomotiveSecurityScanner(config)
    
    try:
        if args.scan_type in ["container", "all"]:
            if args.target:
                await scanner.scan_container_image(args.target)
            else:
                # Scan default automotive images
                default_images = [
                    "ai-servis/core-orchestrator:latest",
                    "ai-servis/ai-audio-assistant:latest", 
                    "ai-servis/hardware-bridge:latest"
                ]
                for image in default_images:
                    try:
                        await scanner.scan_container_image(image)
                    except Exception as e:
                        logger.warning(f"Could not scan {image}: {e}")
        
        if args.scan_type in ["source", "all"]:
            source_path = Path(args.target) if args.target else Path(".")
            await scanner.scan_source_code(source_path)
        
        if args.scan_type in ["network", "all"]:
            target_host = args.target if args.target else "localhost"
            await scanner.scan_network_services(target_host)
        
        # Generate comprehensive report
        report = await scanner.generate_security_report(Path(args.output))
        
        # Print summary
        print(f"\n🔒 MIA Automotive Security Scan Complete")
        print(f"📊 Overall Compliance Score: {report['executive_summary']['overall_compliance_score']:.1f}%")
        print(f"🚗 Automotive Safety Score: {report['executive_summary']['overall_safety_score']:.1f}%")
        print(f"⚠️  Critical Vulnerabilities: {report['executive_summary']['critical_vulnerabilities']}")
        print(f"🚨 High Vulnerabilities: {report['executive_summary']['high_vulnerabilities']}")
        print(f"✅ Automotive Ready: {report['executive_summary']['automotive_ready']}")
        
        # Exit with appropriate code
        if report['executive_summary']['critical_vulnerabilities'] > 0:
            print("❌ CRITICAL vulnerabilities found - not safe for automotive deployment")
            return 1
        elif not report['executive_summary']['automotive_ready']:
            print("⚠️  System not ready for automotive deployment")
            return 1
        else:
            print("✅ System meets automotive security requirements")
            return 0
            
    except Exception as e:
        logger.error(f"Security scanning failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))