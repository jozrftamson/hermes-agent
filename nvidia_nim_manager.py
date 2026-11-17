#!/usr/bin/env python3
"""
NVIDIA NIM Integration & Management
GPU-beschleunigte Prompt Execution via NVIDIA's Inference Microservices
"""

import os
import asyncio
import time
from typing import Dict, Any, List, Optional
import httpx
import logging
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NVIDIANIMManager")

@dataclass
class NIMConfig:
    api_key: str
    api_url: str = "https://api.nvidia.com/v1"
    model: str = "nvidia/llama-3.1-405b"
    max_retries: int = 3
    timeout: int = 60

class NVIDIANIMClient:
    """Client für NVIDIA NIM GPU Inference"""
    
    def __init__(self, config: NIMConfig):
        self.config = config
        self.session: Optional[httpx.AsyncClient] = None
        self.metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_latency": 0,
            "total_tokens": 0
        }
    
    async def initialize(self):
        """Initialisiere Client"""
        self.session = httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=self.config.timeout
        )
        await self.health_check()
    
    def _get_headers(self) -> Dict[str, str]:
        """NVIDIA NIM Headers"""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PromptDeployer/1.0"
        }
    
    async def health_check(self) -> bool:
        """Prüfe NVIDIA NIM Health"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.config.api_url}/health",
                    headers=self._get_headers(),
                    timeout=10
                )
                is_healthy = resp.status_code == 200
                logger.info(f"✅ NVIDIA NIM Health: {'OK' if is_healthy else 'FAILED'}")
                return is_healthy
        except Exception as e:
            logger.error(f"❌ NVIDIA NIM Health Check Failed: {e}")
            return False
    
    async def deploy_prompt(
        self,
        prompt_id: str,
        system_prompt: str,
        name: str,
        category: str,
        tags: List[str],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploye Prompt zu NVIDIA NIM"""
        
        payload = {
            "id": prompt_id,
            "name": name,
            "system_prompt": system_prompt,
            "category": category,
            "tags": tags,
            "model": self.config.model,
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            resp = await self.session.post(
                f"{self.config.api_url}/prompts/deploy",
                json=payload
            )
            
            self.metrics["total_requests"] += 1
            
            if resp.status_code in [200, 201]:
                self.metrics["successful"] += 1
                result = resp.json()
                logger.info(f"✅ NVIDIA NIM: Prompt '{prompt_id}' deployed")
                return {
                    "status": "success",
                    "prompt_id": prompt_id,
                    "deployment_id": result.get("id"),
                    "response": result
                }
            else:
                self.metrics["failed"] += 1
                logger.error(f"❌ NVIDIA NIM Deploy failed: {resp.status_code}")
                return {
                    "status": "failed",
                    "prompt_id": prompt_id,
                    "error": resp.text
                }
        except Exception as e:
            self.metrics["failed"] += 1
            logger.error(f"❌ NVIDIA NIM Error: {e}")
            return {
                "status": "failed",
                "prompt_id": prompt_id,
                "error": str(e)
            }
    
    async def execute_prompt(
        self,
        prompt_id: str,
        input_text: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Führe Prompt auf NVIDIA NIM aus"""
        
        start_time = time.time()
        
        try:
            payload = {
                "prompt_id": prompt_id,
                "input": input_text,
                "model": self.config.model,
                "parameters": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.95
                }
            }
            
            resp = await self.session.post(
                f"{self.config.api_url}/prompts/execute",
                json=payload
            )
            
            latency = time.time() - start_time
            self.metrics["total_requests"] += 1
            self.metrics["total_latency"] += latency
            
            if resp.status_code == 200:
                self.metrics["successful"] += 1
                result = resp.json()
                self.metrics["total_tokens"] += result.get("tokens_used", 0)
                
                return {
                    "status": "success",
                    "prompt_id": prompt_id,
                    "output": result.get("output"),
                    "tokens_used": result.get("tokens_used"),
                    "latency_ms": latency * 1000,
                    "model": self.config.model
                }
            else:
                self.metrics["failed"] += 1
                return {
                    "status": "failed",
                    "error": resp.text,
                    "latency_ms": latency * 1000
                }
        except Exception as e:
            self.metrics["failed"] += 1
            latency = time.time() - start_time
            return {
                "status": "failed",
                "error": str(e),
                "latency_ms": latency * 1000
            }
    
    async def list_deployed_prompts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Liste alle deployed Prompts"""
        try:
            params = {}
            if category:
                params["category"] = category
            
            resp = await self.session.get(
                f"{self.config.api_url}/prompts",
                params=params
            )
            
            if resp.status_code == 200:
                return resp.json().get("prompts", [])
            else:
                logger.error(f"Failed to list prompts: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Gib Metriken aus"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["successful"]
            if self.metrics["successful"] > 0 else 0
        )
        
        return {
            "total_requests": self.metrics["total_requests"],
            "successful": self.metrics["successful"],
            "failed": self.metrics["failed"],
            "success_rate": (
                self.metrics["successful"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            ),
            "avg_latency_ms": avg_latency * 1000,
            "total_tokens": self.metrics["total_tokens"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.aclose()


# Beispiel-Nutzung
async def main():
    config = NIMConfig(
        api_key=os.getenv("NVIDIA_API_KEY", "test-key"),
        model="nvidia/llama-3.1-405b"
    )
    
    client = NVIDIANIMClient(config)
    await client.initialize()
    
    # Deploy Prompt
    deploy_result = await client.deploy_prompt(
        prompt_id="code-review",
        system_prompt="Du bist ein Security Expert...",
        name="Code Security Review",
        category="security",
        tags=["python", "security", "analysis"],
        metadata={"version": "1.0"}
    )
    
    print("Deploy Result:", deploy_result)
    
    # Execute Prompt
    exec_result = await client.execute_prompt(
        prompt_id="code-review",
        input_text="def unsafe_code(): pass"
    )
    
    print("Execution Result:", exec_result)
    
    # Metriken
    print("Metrics:", client.get_metrics())
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
