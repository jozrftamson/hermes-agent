#!/usr/bin/env python3
"""
Nous Research Portal Integration
Multi-Agent Orchestration & Open-Source Model Management
"""

import os
import asyncio
import json
from typing import Dict, Any, List, Optional
import httpx
import logging
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NousResearchManager")

@dataclass
class NousConfig:
    api_key: str
    api_url: str = "https://api.nousresearch.com/v1"
    workspace: str = "default"
    default_model: str = "hermes-3"
    enable_multi_agent: bool = True
    agent_count: int = 3

class NousResearchClient:
    """Client für Nous Research Portal Multi-Agent Setup"""
    
    def __init__(self, config: NousConfig):
        self.config = config
        self.session: Optional[httpx.AsyncClient] = None
        self.agents: List[Dict[str, Any]] = []
        self.metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_latency": 0
        }
    
    async def initialize(self):
        """Initialisiere Client & Agents"""
        self.session = httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=60
        )
        
        # Health Check
        if await self.health_check():
            # Initialisiere Multi-Agents
            if self.config.enable_multi_agent:
                await self._setup_agents()
    
    def _get_headers(self) -> Dict[str, str]:
        """Nous Research Headers"""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-Workspace": self.config.workspace
        }
    
    async def health_check(self) -> bool:
        """Prüfe Nous Portal Health"""
        try:
            resp = await self.session.get(f"{self.config.api_url}/health")
            is_healthy = resp.status_code == 200
            logger.info(f"✅ Nous Portal Health: {'OK' if is_healthy else 'FAILED'}")
            return is_healthy
        except Exception as e:
            logger.error(f"❌ Nous Portal Health Check Failed: {e}")
            return False
    
    async def _setup_agents(self):
        """Initialisiere Multi-Agent Umgebung"""
        logger.info(f"🤖 Setting up {self.config.agent_count} agents...")
        
        for i in range(self.config.agent_count):
            agent_config = {
                "id": f"agent-{i+1}",
                "name": f"Agent {i+1}",
                "model": self.config.default_model,
                "role": self._get_agent_role(i),
                "workspace": self.config.workspace,
                "capabilities": self._get_agent_capabilities(i)
            }
            
            try:
                resp = await self.session.post(
                    f"{self.config.api_url}/agents/create",
                    json=agent_config
                )
                
                if resp.status_code == 201:
                    agent = resp.json()
                    self.agents.append(agent)
                    logger.info(f"✅ Agent {i+1} created: {agent['id']}")
            except Exception as e:
                logger.error(f"Failed to create agent {i+1}: {e}")
    
    def _get_agent_role(self, index: int) -> str:
        """Definiere Agent-Rolle basierend auf Index"""
        roles = [
            "coordinator",      # Agent 1: Koordiniert anderen
            "executor",        # Agent 2: Führt Tasks aus
            "validator"        # Agent 3: Validiert Ergebnisse
        ]
        return roles[index % len(roles)]
    
    def _get_agent_capabilities(self, index: int) -> List[str]:
        """Agent-spezifische Fähigkeiten"""
        capabilities_map = {
            0: ["task_planning", "delegation", "monitoring"],
            1: ["code_execution", "prompt_execution", "tool_calling"],
            2: ["result_validation", "quality_check", "error_handling"]
        }
        return capabilities_map.get(index, [])
    
    async def deploy_prompt(
        self,
        prompt_id: str,
        name: str,
        system_prompt: str,
        category: str,
        tags: List[str],
        recommended_model: str = None
    ) -> Dict[str, Any]:
        """Deploye Prompt zu Nous Portal"""
        
        payload = {
            "id": prompt_id,
            "name": name,
            "description": f"{name} - {category}",
            "system_prompt": system_prompt,
            "category": category,
            "tags": tags,
            "recommended_model": recommended_model or self.config.default_model,
            "workspace": self.config.workspace,
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
                logger.info(f"✅ Nous Portal: Prompt '{prompt_id}' deployed")
                return {
                    "status": "success",
                    "prompt_id": prompt_id,
                    "deployment_id": result.get("id"),
                    "response": result
                }
            else:
                self.metrics["failed"] += 1
                logger.error(f"❌ Nous Portal Deploy failed: {resp.status_code}")
                return {
                    "status": "failed",
                    "prompt_id": prompt_id,
                    "error": resp.text
                }
        except Exception as e:
            self.metrics["failed"] += 1
            logger.error(f"❌ Nous Portal Error: {e}")
            return {
                "status": "failed",
                "prompt_id": prompt_id,
                "error": str(e)
            }
    
    async def execute_with_multi_agent(
        self,
        prompt_id: str,
        input_text: str,
        use_all_agents: bool = True
    ) -> Dict[str, Any]:
        """Führe Prompt mit Multi-Agent Orchestration aus"""
        
        if not self.agents:
            logger.error("No agents available")
            return {"status": "failed", "error": "No agents available"}
        
        # Wähle Agents
        agents_to_use = self.agents if use_all_agents else [self.agents[1]]
        
        results = []
        
        for agent in agents_to_use:
            payload = {
                "prompt_id": prompt_id,
                "input": input_text,
                "agent_id": agent["id"],
                "model": agent.get("model", self.config.default_model)
            }
            
            try:
                resp = await self.session.post(
                    f"{self.config.api_url}/execute",
                    json=payload
                )
                
                if resp.status_code == 200:
                    self.metrics["successful"] += 1
                    result = resp.json()
                    results.append({
                        "agent_id": agent["id"],
                        "status": "success",
                        "output": result.get("output"),
                        "reasoning": result.get("reasoning")
                    })
                else:
                    self.metrics["failed"] += 1
                    results.append({
                        "agent_id": agent["id"],
                        "status": "failed",
                        "error": resp.text
                    })
            except Exception as e:
                self.metrics["failed"] += 1
                results.append({
                    "agent_id": agent["id"],
                    "status": "failed",
                    "error": str(e)
                })
        
        self.metrics["total_requests"] += 1
        
        return {
            "status": "completed",
            "prompt_id": prompt_id,
            "agent_results": results,
            "consensus": self._compute_consensus(results),
            "timestamp": datetime.now().isoformat()
        }
    
    def _compute_consensus(self, results: List[Dict]) -> Optional[str]:
        """Berechne Konsens aus Multi-Agent Ergebnissen"""
        successful = [r for r in results if r["status"] == "success"]
        
        if len(successful) >= len(results) / 2:
            # Einfache Heuristik: Nehme Output des Validators (Agent 3)
            for result in successful:
                if "validator" in result.get("agent_id", ""):
                    return result.get("output")
            
            # Fallback: Erster erfolgreicher Output
            return successful[0].get("output")
        
        return None
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """Liste verfügbare Open-Source Modelle"""
        try:
            resp = await self.session.get(f"{self.config.api_url}/models")
            
            if resp.status_code == 200:
                return resp.json().get("models", [])
            else:
                logger.error(f"Failed to list models: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Status aller Agents"""
        statuses = []
        
        for agent in self.agents:
            try:
                resp = await self.session.get(
                    f"{self.config.api_url}/agents/{agent['id']}/status"
                )
                
                if resp.status_code == 200:
                    statuses.append(resp.json())
            except Exception as e:
                logger.error(f"Failed to get status for {agent['id']}: {e}")
        
        return {
            "agents": statuses,
            "total": len(self.agents),
            "healthy": len([s for s in statuses if s.get("status") == "healthy"]),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Gib Metriken aus"""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            ),
            "agents_deployed": len(self.agents),
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.aclose()


# Beispiel-Nutzung
async def main():
    config = NousConfig(
        api_key=os.getenv("NOUS_API_KEY", "test-key"),
        workspace="my-prompts",
        agent_count=3
    )
    
    client = NousResearchClient(config)
    await client.initialize()
    
    # Deploy Prompt
    deploy_result = await client.deploy_prompt(
        prompt_id="code-review",
        name="Code Security Review",
        system_prompt="Du bist ein Security Expert...",
        category="security",
        tags=["python", "security"]
    )
    
    print("Deploy Result:", deploy_result)
    
    # Execute mit Multi-Agent
    exec_result = await client.execute_with_multi_agent(
        prompt_id="code-review",
        input_text="def unsafe_code(): pass",
        use_all_agents=True
    )
    
    print("Multi-Agent Execution:", exec_result)
    
    # Agent Status
    agent_status = await client.get_agent_status()
    print("Agent Status:", agent_status)
    
    # Metriken
    print("Metrics:", client.get_metrics())
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
