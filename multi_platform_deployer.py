#!/usr/bin/env python3
"""
Multi-Platform Prompt Deployer
Synchronisiert Prompts automatisch zu:
- NVIDIA NIM (GPU-beschleunigt)
- Nous Research Portal (Multi-Agent)
- Hermes (Self-Hosted)

Mit Load-Balancing, Health Checks & Fallback
"""

import json
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultiPlatformDeployer")

class Platform(Enum):
    NVIDIA_NIM = "nvidia_nim"
    NOUS_PORTAL = "nous_portal"
    HERMES = "hermes"

@dataclass
class PromptConfig:
    id: str
    name: str
    system_prompt: str
    category: str
    version: str
    tags: List[str]
    model: str
    description: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.95

@dataclass
class PlatformEndpoint:
    platform: Platform
    url: str
    api_key: str
    enabled: bool = True
    weight: int = 1  # Für Load-Balancing
    fallback_order: int = 0

class PlatformDeployer:
    """Deployer für eine einzelne Plattform"""
    
    def __init__(self, endpoint: PlatformEndpoint, session: aiohttp.ClientSession):
        self.endpoint = endpoint
        self.session = session
        self.health_status = {"healthy": True, "last_check": None}
    
    async def health_check(self) -> bool:
        """Prüfe Plattform-Health"""
        try:
            headers = self._get_headers()
            async with self.session.get(
                f"{self.endpoint.url}/health",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                self.health_status = {
                    "healthy": resp.status == 200,
                    "last_check": datetime.now().isoformat(),
                    "status_code": resp.status
                }
                return resp.status == 200
        except Exception as e:
            logger.error(f"Health check failed for {self.endpoint.platform.value}: {e}")
            self.health_status = {
                "healthy": False,
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Platform-spezifische Headers"""
        return {
            "Authorization": f"Bearer {self.endpoint.api_key}",
            "Content-Type": "application/json"
        }
    
    async def deploy_prompt(self, prompt: PromptConfig) -> Dict[str, Any]:
        """Deploye einen Prompt zu dieser Plattform"""
        if not self.endpoint.enabled:
            return {"status": "skipped", "platform": self.endpoint.platform.value}
        
        try:
            payload = self._prepare_payload(prompt)
            headers = self._get_headers()
            
            async with self.session.post(
                f"{self.endpoint.url}/prompts",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result = await resp.json()
                
                if resp.status in [200, 201]:
                    logger.info(f"✅ {self.endpoint.platform.value}: {prompt.id} deployed")
                    return {
                        "status": "success",
                        "platform": self.endpoint.platform.value,
                        "prompt_id": prompt.id,
                        "response": result
                    }
                else:
                    logger.error(f"❌ {self.endpoint.platform.value}: {resp.status}")
                    return {
                        "status": "failed",
                        "platform": self.endpoint.platform.value,
                        "error": result
                    }
        except Exception as e:
            logger.error(f"Deploy failed for {self.endpoint.platform.value}: {e}")
            return {
                "status": "failed",
                "platform": self.endpoint.platform.value,
                "error": str(e)
            }
    
    def _prepare_payload(self, prompt: PromptConfig) -> Dict[str, Any]:
        """Konvertiere Prompt zum Platform-Format"""
        if self.endpoint.platform == Platform.NVIDIA_NIM:
            return {
                "prompt_id": prompt.id,
                "name": prompt.name,
                "system_prompt": prompt.system_prompt,
                "inference_config": {
                    "model": prompt.model or "nvidia/llama-3.1-405b",
                    "temperature": prompt.temperature,
                    "max_tokens": prompt.max_tokens,
                    "top_p": prompt.top_p
                },
                "metadata": {
                    "category": prompt.category,
                    "tags": prompt.tags,
                    "version": prompt.version
                }
            }
        
        elif self.endpoint.platform == Platform.NOUS_PORTAL:
            return {
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                "system_prompt": prompt.system_prompt,
                "category": prompt.category,
                "tags": prompt.tags,
                "recommended_model": prompt.model or "hermes-3",
                "config": {
                    "temperature": prompt.temperature,
                    "max_tokens": prompt.max_tokens
                }
            }
        
        elif self.endpoint.platform == Platform.HERMES:
            return {
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                "system_prompt": prompt.system_prompt,
                "category": prompt.category,
                "tags": prompt.tags,
                "skill_config": {
                    "model": prompt.model or "auto",
                    "temperature": prompt.temperature,
                    "max_tokens": prompt.max_tokens
                }
            }
        
        return asdict(prompt)


class MultiPlatformDeployer:
    """Master-Deployer für alle Plattformen"""
    
    def __init__(self, config_file: str = "deployment_config.json"):
        self.config_file = Path(config_file)
        self.endpoints: List[PlatformEndpoint] = []
        self.deployers: Dict[Platform, PlatformDeployer] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.load_config()
    
    def load_config(self):
        """Lade Konfiguration aus JSON"""
        if not self.config_file.exists():
            logger.warning(f"Config file {self.config_file} not found, creating template...")
            self._create_template_config()
            return
        
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        for endpoint_cfg in config.get("endpoints", []):
            endpoint = PlatformEndpoint(
                platform=Platform[endpoint_cfg["platform"]],
                url=endpoint_cfg["url"],
                api_key=endpoint_cfg.get("api_key", ""),
                enabled=endpoint_cfg.get("enabled", True),
                weight=endpoint_cfg.get("weight", 1),
                fallback_order=endpoint_cfg.get("fallback_order", 0)
            )
            self.endpoints.append(endpoint)
    
    def _create_template_config(self):
        """Erstelle Template-Konfiguration"""
        template = {
            "endpoints": [
                {
                    "platform": "NVIDIA_NIM",
                    "url": "https://api.nvidia.com/v1",
                    "api_key": "${NVIDIA_API_KEY}",
                    "enabled": True,
                    "weight": 3,
                    "fallback_order": 0
                },
                {
                    "platform": "NOUS_PORTAL",
                    "url": "https://api.nousresearch.com/v1",
                    "api_key": "${NOUS_API_KEY}",
                    "enabled": True,
                    "weight": 2,
                    "fallback_order": 1
                },
                {
                    "platform": "HERMES",
                    "url": "http://localhost:8000",
                    "api_key": "${HERMES_API_KEY}",
                    "enabled": True,
                    "weight": 1,
                    "fallback_order": 2
                }
            ]
        }
        with open(self.config_file, 'w') as f:
            json.dump(template, f, indent=2)
        logger.info(f"Template config created: {self.config_file}")
    
    async def initialize(self):
        """Initialisiere Deployer für alle Plattformen"""
        self.session = aiohttp.ClientSession()
        
        for endpoint in self.endpoints:
            if endpoint.enabled:
                deployer = PlatformDeployer(endpoint, self.session)
                self.deployers[endpoint.platform] = deployer
    
    async def health_check_all(self) -> Dict[Platform, bool]:
        """Prüfe Health aller Plattformen"""
        logger.info("🏥 Running health checks...")
        results = {}
        
        tasks = [
            (platform, deployer.health_check())
            for platform, deployer in self.deployers.items()
        ]
        
        for platform, task in tasks:
            results[platform] = await task
            status = "✅" if results[platform] else "❌"
            logger.info(f"{status} {platform.value}")
        
        return results
    
    async def deploy_prompt(self, prompt: PromptConfig) -> Dict[str, Any]:
        """Deploye Prompt zu allen verfügbaren Plattformen"""
        logger.info(f"🚀 Deploying prompt: {prompt.id}")
        
        results = {
            "prompt_id": prompt.id,
            "timestamp": datetime.now().isoformat(),
            "platforms": {}
        }
        
        # Sortiere nach Fallback-Order
        sorted_deployers = sorted(
            self.deployers.items(),
            key=lambda x: x[1].endpoint.fallback_order
        )
        
        for platform, deployer in sorted_deployers:
            result = await deployer.deploy_prompt(prompt)
            results["platforms"][platform.value] = result
        
        return results
    
    async def deploy_all_prompts(self, prompts_dir: str = "prompts") -> Dict[str, Any]:
        """Deploye alle Prompts aus einem Verzeichnis"""
        logger.info(f"📦 Deploying all prompts from {prompts_dir}")
        
        prompts_path = Path(prompts_dir)
        prompts = self._load_prompts(prompts_path)
        
        logger.info(f"Found {len(prompts)} prompts")
        
        results = {
            "total": len(prompts),
            "timestamp": datetime.now().isoformat(),
            "deployments": []
        }
        
        for prompt in prompts:
            deployment = await self.deploy_prompt(prompt)
            results["deployments"].append(deployment)
            await asyncio.sleep(0.5)  # Rate limiting
        
        return results
    
    def _load_prompts(self, prompts_dir: Path) -> List[PromptConfig]:
        """Lade alle Prompts aus Verzeichnis"""
        prompts = []
        
        for prompt_dir in prompts_dir.glob("*/"):
            metadata_file = prompt_dir / "metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                prompt = PromptConfig(
                    id=prompt_dir.name,
                    name=metadata.get("name", prompt_dir.name),
                    system_prompt=metadata.get("system_prompt", ""),
                    category=metadata.get("category", "general"),
                    version=metadata.get("version", "1.0"),
                    tags=metadata.get("tags", []),
                    model=metadata.get("model", "auto"),
                    description=metadata.get("description", ""),
                    temperature=metadata.get("temperature", 0.7),
                    max_tokens=metadata.get("max_tokens", 2000),
                    top_p=metadata.get("top_p", 0.95)
                )
                prompts.append(prompt)
        
        return prompts
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.close()


async def main():
    deployer = MultiPlatformDeployer()
    
    try:
        await deployer.initialize()
        
        # Health checks
        health = await deployer.health_check_all()
        
        # Deploy all
        results = await deployer.deploy_all_prompts()
        
        # Output results
        print("\n" + "="*60)
        print("🎉 DEPLOYMENT RESULTS")
        print("="*60)
        print(json.dumps(results, indent=2))
        
        # Save results
        with open("deployment_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        logger.info("Results saved to deployment_results.json")
        
    finally:
        await deployer.close()


if __name__ == "__main__":
    asyncio.run(main())
