#!/usr/bin/env python3
"""
Hermes Local Manager & Advanced Configuration
Self-Hosted Development & Production Setup
"""

import os
import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional
import httpx
import logging
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HermesManager")

@dataclass
class HermesConfig:
    api_url: str = "http://localhost:9001"
    api_key: str = "local-dev-key"
    home_dir: str = "~/.hermes"
    enable_dashboard: bool = True
    enable_gateway: bool = True
    enable_mcp: bool = True
    available_models: List[str] = None
    
    def __post_init__(self):
        if self.available_models is None:
            self.available_models = [
                "openrouter/openai/gpt-4",
                "openrouter/anthropic/claude-3-opus",
                "openrouter/nous-research/hermes-3",
                "openrouter/meta-llama/llama-3.1-405b"
            ]

class HermesLocalManager:
    """Manager für Self-Hosted Hermes"""
    
    def __init__(self, config: HermesConfig):
        self.config = config
        self.session: Optional[httpx.AsyncClient] = None
        self.skills: Dict[str, Dict] = {}
        self.sessions: Dict[str, Dict] = {}
        self.metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "active_sessions": 0
        }
    
    async def initialize(self):
        """Initialisiere Hermes Local"""
        self.session = httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=60
        )
        
        # Health Check
        is_healthy = await self.health_check()
        if is_healthy:
            await self._load_configuration()
    
    def _get_headers(self) -> Dict[str, str]:
        """Hermes API Headers"""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    async def health_check(self) -> bool:
        """Prüfe Hermes Health"""
        try:
            resp = await self.session.get(f"{self.config.api_url}/health")
            is_healthy = resp.status_code == 200
            logger.info(f"✅ Hermes Health: {'OK' if is_healthy else 'FAILED'}")
            return is_healthy
        except Exception as e:
            logger.error(f"❌ Hermes Health Check Failed: {e}")
            logger.info("💡 Starte Hermes mit: docker-compose up hermes")
            return False
    
    async def _load_configuration(self):
        """Lade Hermes Konfiguration"""
        home_path = Path(self.config.home_dir).expanduser()
        config_file = home_path / "config.yaml"
        
        if config_file.exists():
            logger.info(f"📖 Loaded config from {config_file}")
        else:
            logger.warning(f"⚠️ Config not found at {config_file}")
    
    async def deploy_skill(
        self,
        prompt_id: str,
        name: str,
        system_prompt: str,
        category: str,
        tags: List[str],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Deploye Prompt als Hermes Skill"""
        
        skill = {
            "id": prompt_id,
            "name": name,
            "description": f"{name} ({category})",
            "system_prompt": system_prompt,
            "category": category,
            "tags": tags,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        try:
            resp = await self.session.post(
                f"{self.config.api_url}/skills",
                json=skill
            )
            
            self.metrics["total_requests"] += 1
            
            if resp.status_code in [200, 201]:
                self.metrics["successful"] += 1
                result = resp.json()
                self.skills[prompt_id] = skill
                logger.info(f"✅ Hermes: Skill '{prompt_id}' deployed")
                return {
                    "status": "success",
                    "skill_id": prompt_id,
                    "response": result
                }
            else:
                self.metrics["failed"] += 1
                logger.error(f"❌ Hermes Deploy failed: {resp.status_code}")
                return {
                    "status": "failed",
                    "skill_id": prompt_id,
                    "error": resp.text
                }
        except Exception as e:
            self.metrics["failed"] += 1
            logger.error(f"❌ Hermes Error: {e}")
            return {
                "status": "failed",
                "skill_id": prompt_id,
                "error": str(e)
            }
    
    async def create_session(self, model: str = None) -> Dict[str, Any]:
        """Erstelle neue Hermes Session"""
        
        payload = {
            "model": model or self.config.available_models[0],
            "created_at": datetime.now().isoformat()
        }
        
        try:
            resp = await self.session.post(
                f"{self.config.api_url}/sessions",
                json=payload
            )
            
            if resp.status_code == 201:
                session = resp.json()
                self.sessions[session["id"]] = session
                self.metrics["active_sessions"] += 1
                logger.info(f"✅ Session created: {session['id']}")
                return {
                    "status": "success",
                    "session_id": session["id"],
                    "session": session
                }
            else:
                logger.error(f"Failed to create session: {resp.status_code}")
                return {
                    "status": "failed",
                    "error": resp.text
                }
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def execute_prompt(
        self,
        session_id: str,
        prompt_id: str,
        input_text: str,
        model: str = None
    ) -> Dict[str, Any]:
        """Führe Prompt in Hermes Session aus"""
        
        payload = {
            "skill_id": prompt_id,
            "input": input_text,
            "model": model or self.config.available_models[0]
        }
        
        try:
            resp = await self.session.post(
                f"{self.config.api_url}/sessions/{session_id}/execute",
                json=payload
            )
            
            self.metrics["total_requests"] += 1
            
            if resp.status_code == 200:
                self.metrics["successful"] += 1
                result = resp.json()
                return {
                    "status": "success",
                    "output": result.get("output"),
                    "tokens_used": result.get("tokens_used"),
                    "model_used": result.get("model"),
                    "reasoning": result.get("reasoning")
                }
            else:
                self.metrics["failed"] += 1
                return {
                    "status": "failed",
                    "error": resp.text
                }
        except Exception as e:
            self.metrics["failed"] += 1
            logger.error(f"Execution error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def list_skills(self, category: Optional[str] = None) -> List[Dict]:
        """Liste verfügbare Skills"""
        try:
            params = {}
            if category:
                params["category"] = category
            
            resp = await self.session.get(
                f"{self.config.api_url}/skills",
                params=params
            )
            
            if resp.status_code == 200:
                return resp.json().get("skills", [])
            else:
                return []
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            return []
    
    async def enable_mcp_server(self, server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Aktiviere MCP Server für erweiterte Fähigkeiten"""
        
        payload = {
            "server": server_name,
            "config": config,
            "enabled": True
        }
        
        try:
            resp = await self.session.post(
                f"{self.config.api_url}/mcp/servers",
                json=payload
            )
            
            if resp.status_code in [200, 201]:
                logger.info(f"✅ MCP Server '{server_name}' enabled")
                return {
                    "status": "success",
                    "server": server_name,
                    "response": resp.json()
                }
            else:
                return {
                    "status": "failed",
                    "server": server_name,
                    "error": resp.text
                }
        except Exception as e:
            logger.error(f"Error enabling MCP server: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def enable_gateway(self, platform: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Aktiviere Messaging Gateway (Telegram, Discord, etc.)"""
        
        payload = {
            "platform": platform,
            "credentials": credentials,
            "enabled": True
        }
        
        try:
            resp = await self.session.post(
                f"{self.config.api_url}/gateways",
                json=payload
            )
            
            if resp.status_code in [200, 201]:
                logger.info(f"✅ Gateway '{platform}' enabled")
                return {
                    "status": "success",
                    "platform": platform,
                    "response": resp.json()
                }
            else:
                return {
                    "status": "failed",
                    "platform": platform,
                    "error": resp.text
                }
        except Exception as e:
            logger.error(f"Error enabling gateway: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def get_memory(self, session_id: str) -> Dict[str, Any]:
        """Hole User-Memory aus Session"""
        try:
            resp = await self.session.get(
                f"{self.config.api_url}/sessions/{session_id}/memory"
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": "Memory not found"}
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return {"error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Gib Metriken aus"""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            ),
            "deployed_skills": len(self.skills),
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.aclose()


# Beispiel-Nutzung
async def main():
    config = HermesConfig(
        api_url="http://localhost:9001",
        api_key=os.getenv("HERMES_API_KEY", "local-dev-key")
    )
    
    manager = HermesLocalManager(config)
    await manager.initialize()
    
    # Deploy Skill
    deploy_result = await manager.deploy_skill(
        prompt_id="code-review",
        name="Code Security Review",
        system_prompt="Du bist ein Security Expert...",
        category="security",
        tags=["python", "security"]
    )
    
    print("Deploy Result:", deploy_result)
    
    # Erstelle Session
    session_result = await manager.create_session()
    
    if session_result["status"] == "success":
        session_id = session_result["session_id"]
        
        # Execute Prompt
        exec_result = await manager.execute_prompt(
            session_id=session_id,
            prompt_id="code-review",
            input_text="def unsafe_code(): pass"
        )
        
        print("Execution Result:", exec_result)
    
    # Enable Gateway
    gateway_result = await manager.enable_gateway(
        platform="telegram",
        credentials={
            "token": os.getenv("TELEGRAM_TOKEN", "")
        }
    )
    
    print("Gateway Result:", gateway_result)
    
    # Metriken
    print("Metrics:", manager.get_metrics())
    
    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
