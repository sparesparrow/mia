#!/usr/bin/env python3
"""
🚗 MIA Universal Automotive Performance Testing Suite

Comprehensive performance testing for automotive AI voice control systems
Focuses on real-time constraints, edge deployment optimization, and voice processing latency
"""

import asyncio
import json
import logging
import time
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import psutil
import docker
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for automotive AI systems"""
    component: str
    test_type: str
    duration: float
    latency_ms: List[float] = field(default_factory=list)
    throughput_rps: float = 0.0
    cpu_usage_percent: List[float] = field(default_factory=list)
    memory_usage_mb: List[float] = field(default_factory=list)
    voice_processing_latency_ms: List[float] = field(default_factory=list)
    wake_word_detection_rate: float = 0.0
    audio_quality_score: float = 0.0
    edge_optimization_score: float = 0.0
    automotive_compliance: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class AutomotiveRequirements:
    """Automotive-specific performance requirements"""
    max_voice_latency_ms: float = 500.0  # ISO 26262 requirement
    min_wake_word_rate: float = 0.95      # 95% detection rate
    max_cpu_usage_percent: float = 70.0   # Leave headroom for safety systems
    max_memory_usage_mb: float = 1024.0   # Edge device constraints
    min_audio_quality: float = 0.8        # Minimum acceptable quality
    max_startup_time_s: float = 30.0      # Fast boot requirement
    min_uptime_hours: float = 720.0       # 30 days continuous operation


class AutomotivePerformanceTester:
    """Comprehensive performance testing for automotive AI systems"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.requirements = AutomotiveRequirements()
        self.docker_client = docker.from_env()
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[PerformanceMetrics] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_voice_processing_latency(self, duration_s: int = 60) -> PerformanceMetrics:
        """Test voice processing latency under automotive conditions"""
        logger.info(f"Testing voice processing latency for {duration_s} seconds")
        
        metrics = PerformanceMetrics(
            component="ai-audio-assistant",
            test_type="voice_latency",
            duration=duration_s
        )
        
        start_time = time.time()
        
        # Simulate voice commands at realistic intervals (every 2-5 seconds)
        voice_commands = [
            "Navigate to home",
            "Call John Smith",
            "Play my driving playlist",
            "What's the weather like?",
            "Set temperature to 22 degrees",
            "Find nearest gas station",
            "Send message to Sarah",
            "Increase volume",
            "Skip this song",
            "Turn on air conditioning"
        ]
        
        while time.time() - start_time < duration_s:
            command = np.random.choice(voice_commands)
            
            # Measure end-to-end voice processing latency
            request_start = time.time()
            
            try:
                async with self.session.post(
                    f"{self.base_url}/api/voice/process",
                    json={"command": command, "automotive_mode": True},
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        latency_ms = (time.time() - request_start) * 1000
                        metrics.voice_processing_latency_ms.append(latency_ms)
                        
                        # Extract quality metrics
                        if 'audio_quality_score' in result:
                            metrics.audio_quality_score = max(
                                metrics.audio_quality_score, 
                                result['audio_quality_score']
                            )
                    else:
                        metrics.errors.append(f"HTTP {response.status}")
                        
            except asyncio.TimeoutError:
                metrics.errors.append("Voice processing timeout")
                metrics.voice_processing_latency_ms.append(2000.0)  # Timeout penalty
            except Exception as e:
                metrics.errors.append(str(e))
            
            # Realistic interval between commands
            await asyncio.sleep(np.random.uniform(2.0, 5.0))
        
        # Calculate metrics
        if metrics.voice_processing_latency_ms:
            metrics.latency_ms = metrics.voice_processing_latency_ms
            logger.info(f"Voice latency - Mean: {statistics.mean(metrics.latency_ms):.1f}ms, "
                       f"P95: {np.percentile(metrics.latency_ms, 95):.1f}ms, "
                       f"Max: {max(metrics.latency_ms):.1f}ms")
        
        return metrics

    async def test_wake_word_detection(self, iterations: int = 100) -> PerformanceMetrics:
        """Test wake word detection accuracy and performance"""
        logger.info(f"Testing wake word detection with {iterations} iterations")
        
        metrics = PerformanceMetrics(
            component="ai-audio-assistant",
            test_type="wake_word_detection",
            duration=iterations * 0.5  # Approximate duration
        )
        
        wake_words = ["Hey MIA", "MIA", "Computer"]
        false_positives = ["Hey Google", "Alexa", "Siri", "Background noise"]
        
        detected_count = 0
        false_positive_count = 0
        
        for i in range(iterations):
            # Test actual wake words
            if i % 2 == 0:
                wake_word = np.random.choice(wake_words)
                
                try:
                    async with self.session.post(
                        f"{self.base_url}/api/voice/wake-word",
                        json={"audio_data": wake_word, "automotive_mode": True},
                        timeout=aiohttp.ClientTimeout(total=1.0)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("wake_word_detected", False):
                                detected_count += 1
                except Exception as e:
                    metrics.errors.append(str(e))
            
            # Test false positives
            else:
                false_phrase = np.random.choice(false_positives)
                
                try:
                    async with self.session.post(
                        f"{self.base_url}/api/voice/wake-word",
                        json={"audio_data": false_phrase, "automotive_mode": True},
                        timeout=aiohttp.ClientTimeout(total=1.0)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("wake_word_detected", False):
                                false_positive_count += 1
                except Exception as e:
                    metrics.errors.append(str(e))
        
        # Calculate detection rate
        expected_detections = iterations // 2
        metrics.wake_word_detection_rate = detected_count / expected_detections if expected_detections > 0 else 0.0
        
        logger.info(f"Wake word detection rate: {metrics.wake_word_detection_rate:.2%}, "
                   f"False positives: {false_positive_count}")
        
        return metrics

    async def test_concurrent_load(self, concurrent_users: int = 50, duration_s: int = 300) -> PerformanceMetrics:
        """Test system under concurrent automotive load"""
        logger.info(f"Testing concurrent load with {concurrent_users} users for {duration_s} seconds")
        
        metrics = PerformanceMetrics(
            component="core-orchestrator",
            test_type="concurrent_load",
            duration=duration_s
        )
        
        # Monitor system resources
        resource_monitor_task = asyncio.create_task(
            self._monitor_system_resources(metrics, duration_s)
        )
        
        # Create concurrent user sessions
        async def user_session(user_id: int):
            user_latencies = []
            user_errors = []
            
            endpoints = [
                "/api/voice/process",
                "/api/automotive/status",
                "/api/health",
                "/api/metrics"
            ]
            
            session_start = time.time()
            
            while time.time() - session_start < duration_s:
                endpoint = np.random.choice(endpoints)
                request_start = time.time()
                
                try:
                    async with self.session.get(
                        f"{self.base_url}{endpoint}",
                        timeout=aiohttp.ClientTimeout(total=5.0)
                    ) as response:
                        latency_ms = (time.time() - request_start) * 1000
                        user_latencies.append(latency_ms)
                        
                        if response.status != 200:
                            user_errors.append(f"HTTP {response.status}")
                            
                except Exception as e:
                    user_errors.append(str(e))
                
                # Realistic user behavior interval
                await asyncio.sleep(np.random.uniform(0.5, 2.0))
            
            return user_latencies, user_errors
        
        # Run concurrent user sessions
        tasks = [user_session(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_latencies = []
        all_errors = []
        
        for result in user_results:
            if isinstance(result, tuple):
                latencies, errors = result
                all_latencies.extend(latencies)
                all_errors.extend(errors)
        
        metrics.latency_ms = all_latencies
        metrics.errors = all_errors
        metrics.throughput_rps = len(all_latencies) / duration_s
        
        # Wait for resource monitoring to complete
        await resource_monitor_task
        
        logger.info(f"Concurrent load test - Throughput: {metrics.throughput_rps:.1f} RPS, "
                   f"Mean latency: {statistics.mean(all_latencies):.1f}ms, "
                   f"Errors: {len(all_errors)}")
        
        return metrics

    async def _monitor_system_resources(self, metrics: PerformanceMetrics, duration_s: int):
        """Monitor system resources during testing"""
        start_time = time.time()
        
        while time.time() - start_time < duration_s:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.cpu_usage_percent.append(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            metrics.memory_usage_mb.append(memory_mb)
            
            await asyncio.sleep(5)

    async def test_edge_deployment_optimization(self) -> PerformanceMetrics:
        """Test edge deployment optimization for automotive environments"""
        logger.info("Testing edge deployment optimization")
        
        metrics = PerformanceMetrics(
            component="system",
            test_type="edge_optimization",
            duration=60
        )
        
        # Test container startup times
        container_startup_times = []
        
        services = [
            "ai-servis-core-orchestrator",
            "ai-servis-ai-audio-assistant",
            "ai-servis-hardware-bridge"
        ]
        
        for service in services:
            try:
                # Stop container if running
                try:
                    container = self.docker_client.containers.get(service)
                    container.stop()
                    container.remove()
                except docker.errors.NotFound:
                    pass
                
                # Start container and measure startup time
                start_time = time.time()
                
                container = self.docker_client.containers.run(
                    f"ghcr.io/sparesparrow/mia-universal/{service.replace('ai-servis-', '')}:latest",
                    name=service,
                    detach=True,
                    environment={"AUTOMOTIVE_MODE": "true", "EDGE_OPTIMIZATION": "true"}
                )
                
                # Wait for container to be healthy
                while True:
                    container.reload()
                    if container.status == "running":
                        # Check health endpoint
                        try:
                            async with self.session.get(
                                f"http://localhost:8080/health",
                                timeout=aiohttp.ClientTimeout(total=1.0)
                            ) as response:
                                if response.status == 200:
                                    startup_time = time.time() - start_time
                                    container_startup_times.append(startup_time)
                                    logger.info(f"{service} startup time: {startup_time:.2f}s")
                                    break
                        except:
                            pass
                    
                    if time.time() - start_time > 60:  # Timeout after 60 seconds
                        metrics.errors.append(f"{service} startup timeout")
                        break
                    
                    await asyncio.sleep(1)
                
            except Exception as e:
                metrics.errors.append(f"{service}: {str(e)}")
        
        # Calculate edge optimization score
        if container_startup_times:
            avg_startup_time = statistics.mean(container_startup_times)
            max_startup_time = max(container_startup_times)
            
            # Score based on automotive requirements
            startup_score = max(0, 100 - (avg_startup_time / self.requirements.max_startup_time_s) * 100)
            metrics.edge_optimization_score = startup_score
            
            logger.info(f"Edge optimization - Avg startup: {avg_startup_time:.2f}s, "
                       f"Max startup: {max_startup_time:.2f}s, Score: {startup_score:.1f}")
        
        return metrics

    def evaluate_automotive_compliance(self, all_metrics: List[PerformanceMetrics]) -> Dict[str, bool]:
        """Evaluate compliance with automotive requirements"""
        compliance = {}
        
        # Voice processing latency requirement
        voice_metrics = [m for m in all_metrics if m.test_type == "voice_latency"]
        if voice_metrics:
            max_voice_latency = max(max(m.voice_processing_latency_ms, default=[0]) for m in voice_metrics)
            compliance["voice_latency"] = max_voice_latency <= self.requirements.max_voice_latency_ms
        
        # Wake word detection rate requirement
        wake_word_metrics = [m for m in all_metrics if m.test_type == "wake_word_detection"]
        if wake_word_metrics:
            min_detection_rate = min(m.wake_word_detection_rate for m in wake_word_metrics)
            compliance["wake_word_detection"] = min_detection_rate >= self.requirements.min_wake_word_rate
        
        # Resource usage requirements
        load_metrics = [m for m in all_metrics if m.test_type == "concurrent_load"]
        if load_metrics:
            max_cpu = max(max(m.cpu_usage_percent, default=[0]) for m in load_metrics)
            max_memory = max(max(m.memory_usage_mb, default=[0]) for m in load_metrics)
            
            compliance["cpu_usage"] = max_cpu <= self.requirements.max_cpu_usage_percent
            compliance["memory_usage"] = max_memory <= self.requirements.max_memory_usage_mb
        
        # Startup time requirement
        edge_metrics = [m for m in all_metrics if m.test_type == "edge_optimization"]
        if edge_metrics:
            compliance["startup_time"] = all(
                m.edge_optimization_score >= 70 for m in edge_metrics
            )
        
        # Overall compliance
        compliance["overall"] = all(compliance.values())
        
        return compliance

    def generate_performance_report(self, output_file: Path = Path("automotive-performance-report.html")):
        """Generate comprehensive performance report"""
        logger.info(f"Generating performance report: {output_file}")
        
        # Create visualizations
        self._create_performance_charts()
        
        # Evaluate compliance
        compliance = self.evaluate_automotive_compliance(self.results)
        
        # Generate HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MIA Automotive Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
                .pass {{ color: #28a745; }}
                .fail {{ color: #dc3545; }}
                .chart {{ text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚗 MIA Universal</h1>
                <h2>Automotive Performance Test Report</h2>
                <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <div class="metric">
                    <strong>Overall Compliance:</strong> 
                    <span class="{'pass' if compliance.get('overall', False) else 'fail'}">
                        {'✅ PASS' if compliance.get('overall', False) else '❌ FAIL'}
                    </span>
                </div>
                <div class="metric">
                    <strong>Tests Executed:</strong> {len(self.results)}
                </div>
                <div class="metric">
                    <strong>Total Duration:</strong> {sum(m.duration for m in self.results):.1f}s
                </div>
            </div>
            
            <div class="section">
                <h2>Automotive Requirements Compliance</h2>
                {self._generate_compliance_table(compliance)}
            </div>
            
            <div class="section">
                <h2>Performance Metrics</h2>
                {self._generate_metrics_summary()}
            </div>
            
            <div class="section">
                <h2>Performance Charts</h2>
                <div class="chart">
                    <img src="performance_charts.png" alt="Performance Charts" style="max-width: 100%;">
                </div>
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                {self._generate_recommendations(compliance)}
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Performance report saved to {output_file}")

    def _generate_compliance_table(self, compliance: Dict[str, bool]) -> str:
        """Generate compliance table HTML"""
        table_rows = []
        
        requirements = {
            "voice_latency": f"Voice processing latency ≤ {self.requirements.max_voice_latency_ms}ms",
            "wake_word_detection": f"Wake word detection rate ≥ {self.requirements.min_wake_word_rate:.0%}",
            "cpu_usage": f"CPU usage ≤ {self.requirements.max_cpu_usage_percent}%",
            "memory_usage": f"Memory usage ≤ {self.requirements.max_memory_usage_mb}MB",
            "startup_time": f"Startup time ≤ {self.requirements.max_startup_time_s}s"
        }
        
        for key, description in requirements.items():
            status = compliance.get(key, False)
            status_text = '✅ PASS' if status else '❌ FAIL'
            status_class = 'pass' if status else 'fail'
            
            table_rows.append(f"""
                <tr>
                    <td>{description}</td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
            """)
        
        return f"""
        <table border="1" style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f8f9fa;">
                    <th style="padding: 10px;">Requirement</th>
                    <th style="padding: 10px;">Status</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """

    def _generate_metrics_summary(self) -> str:
        """Generate metrics summary HTML"""
        summary_items = []
        
        for metrics in self.results:
            if metrics.latency_ms:
                mean_latency = statistics.mean(metrics.latency_ms)
                p95_latency = np.percentile(metrics.latency_ms, 95)
                
                summary_items.append(f"""
                    <div class="metric">
                        <strong>{metrics.component} - {metrics.test_type}</strong><br>
                        Mean Latency: {mean_latency:.1f}ms<br>
                        P95 Latency: {p95_latency:.1f}ms<br>
                        Throughput: {metrics.throughput_rps:.1f} RPS<br>
                        Errors: {len(metrics.errors)}
                    </div>
                """)
        
        return ''.join(summary_items)

    def _generate_recommendations(self, compliance: Dict[str, bool]) -> str:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if not compliance.get("voice_latency", True):
            recommendations.append("• Optimize voice processing pipeline to reduce latency below 500ms")
        
        if not compliance.get("wake_word_detection", True):
            recommendations.append("• Improve wake word detection model accuracy")
        
        if not compliance.get("cpu_usage", True):
            recommendations.append("• Optimize CPU usage or consider more powerful hardware")
        
        if not compliance.get("memory_usage", True):
            recommendations.append("• Reduce memory footprint for edge deployment")
        
        if not compliance.get("startup_time", True):
            recommendations.append("• Optimize container startup time for automotive requirements")
        
        if not recommendations:
            recommendations.append("• All automotive requirements met - system is ready for deployment")
        
        return '<ul>' + ''.join(f'<li>{rec}</li>' for rec in recommendations) + '</ul>'

    def _create_performance_charts(self):
        """Create performance visualization charts"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('MIA Automotive Performance Metrics', fontsize=16)
        
        # Voice processing latency chart
        voice_metrics = [m for m in self.results if m.test_type == "voice_latency"]
        if voice_metrics and voice_metrics[0].voice_processing_latency_ms:
            axes[0, 0].hist(voice_metrics[0].voice_processing_latency_ms, bins=30, alpha=0.7)
            axes[0, 0].axvline(self.requirements.max_voice_latency_ms, color='red', linestyle='--', 
                              label=f'Requirement: {self.requirements.max_voice_latency_ms}ms')
            axes[0, 0].set_title('Voice Processing Latency Distribution')
            axes[0, 0].set_xlabel('Latency (ms)')
            axes[0, 0].set_ylabel('Frequency')
            axes[0, 0].legend()
        
        # Resource usage over time
        load_metrics = [m for m in self.results if m.test_type == "concurrent_load"]
        if load_metrics and load_metrics[0].cpu_usage_percent:
            time_points = range(len(load_metrics[0].cpu_usage_percent))
            axes[0, 1].plot(time_points, load_metrics[0].cpu_usage_percent, label='CPU %')
            axes[0, 1].axhline(self.requirements.max_cpu_usage_percent, color='red', linestyle='--', 
                              label=f'CPU Limit: {self.requirements.max_cpu_usage_percent}%')
            axes[0, 1].set_title('Resource Usage Over Time')
            axes[0, 1].set_xlabel('Time (5s intervals)')
            axes[0, 1].set_ylabel('Usage %')
            axes[0, 1].legend()
        
        # Throughput vs Latency
        if any(m.throughput_rps > 0 for m in self.results):
            throughput_data = [(m.throughput_rps, statistics.mean(m.latency_ms) if m.latency_ms else 0) 
                             for m in self.results if m.throughput_rps > 0]
            if throughput_data:
                throughput, latency = zip(*throughput_data)
                axes[1, 0].scatter(throughput, latency)
                axes[1, 0].set_title('Throughput vs Latency')
                axes[1, 0].set_xlabel('Throughput (RPS)')
                axes[1, 0].set_ylabel('Latency (ms)')
        
        # Edge optimization scores
        edge_scores = [m.edge_optimization_score for m in self.results if m.edge_optimization_score]
        if edge_scores:
            axes[1, 1].bar(range(len(edge_scores)), edge_scores)
            axes[1, 1].axhline(70, color='red', linestyle='--', label='Minimum Score: 70')
            axes[1, 1].set_title('Edge Optimization Scores')
            axes[1, 1].set_xlabel('Test Run')
            axes[1, 1].set_ylabel('Score')
            axes[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig('performance_charts.png', dpi=300, bbox_inches='tight')
        plt.close()

    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete automotive performance test suite"""
        logger.info("🚗 Starting MIA Automotive Performance Test Suite")
        
        test_start_time = time.time()
        
        # Test 1: Voice Processing Latency
        logger.info("Running voice processing latency test...")
        voice_metrics = await self.test_voice_processing_latency(60)
        self.results.append(voice_metrics)
        
        # Test 2: Wake Word Detection
        logger.info("Running wake word detection test...")
        wake_word_metrics = await self.test_wake_word_detection(100)
        self.results.append(wake_word_metrics)
        
        # Test 3: Concurrent Load
        logger.info("Running concurrent load test...")
        load_metrics = await self.test_concurrent_load(50, 300)
        self.results.append(load_metrics)
        
        # Test 4: Edge Deployment Optimization
        logger.info("Running edge deployment optimization test...")
        edge_metrics = await self.test_edge_deployment_optimization()
        self.results.append(edge_metrics)
        
        total_duration = time.time() - test_start_time
        
        # Evaluate compliance
        compliance = self.evaluate_automotive_compliance(self.results)
        
        # Generate report
        self.generate_performance_report()
        
        # Summary results
        results = {
            "total_duration": total_duration,
            "tests_completed": len(self.results),
            "compliance": compliance,
            "metrics": self.results,
            "summary": {
                "voice_latency_p95": np.percentile(voice_metrics.voice_processing_latency_ms, 95) if voice_metrics.voice_processing_latency_ms else 0,
                "wake_word_detection_rate": wake_word_metrics.wake_word_detection_rate,
                "max_throughput_rps": max(m.throughput_rps for m in self.results),
                "edge_optimization_score": edge_metrics.edge_optimization_score,
                "total_errors": sum(len(m.errors) for m in self.results)
            }
        }
        
        logger.info(f"✅ Performance test suite completed in {total_duration:.1f}s")
        logger.info(f"Overall compliance: {'PASS' if compliance['overall'] else 'FAIL'}")
        
        return results


async def main():
    """Main entry point for automotive performance testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MIA Automotive Performance Testing")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base URL for API testing")
    parser.add_argument("--output", default="automotive-performance-report.html", help="Output report file")
    parser.add_argument("--json-output", help="JSON output file for CI/CD integration")
    
    args = parser.parse_args()
    
    async with AutomotivePerformanceTester(args.base_url) as tester:
        try:
            results = await tester.run_full_test_suite()
            
            # Save JSON results for CI/CD
            if args.json_output:
                with open(args.json_output, 'w') as f:
                    # Convert results to JSON-serializable format
                    json_results = {
                        "total_duration": results["total_duration"],
                        "tests_completed": results["tests_completed"],
                        "compliance": results["compliance"],
                        "summary": results["summary"]
                    }
                    json.dump(json_results, f, indent=2)
                logger.info(f"JSON results saved to {args.json_output}")
            
            # Exit with error code if compliance failed
            if not results["compliance"]["overall"]:
                logger.error("❌ Automotive compliance requirements not met")
                sys.exit(1)
            else:
                logger.info("✅ All automotive compliance requirements met")
                sys.exit(0)
                
        except Exception as e:
            logger.error(f"Performance testing failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())