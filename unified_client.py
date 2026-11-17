#!/usr/bin/env python3
"""
Unified Multi-Platform Client
Orchestriert NVIDIA NIM, Nous Portal & Hermes mit einer einzigen API
"""

import asyncio
import os
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
import logging

from nvidia_nim_manager import NVIDIANIMClient, NIMConfig
from nous_research_manager import NousResearchClient, NousConfig
from hermes_local_manager import HermesLocalManager, HermesConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedClient")

class Platform(str, Enum):
    NVIDIA_NIM = "nvidia_nim"
    NOUS_PORTAL = "nous_portal"
    HERMES = "hermes"

class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"  # NVIDIA > Nous > Hermes
    LATENCY = "latency"
    FAILOVER = "failover"
    PARALLEL = "parallel"

class UnifiedPromptClient:
    """Unified Client für alle Plattformen"""
    
    def __init__(self):
        self.platforms: Dict[Platform, Any] = {}
        self.request_counts = {
            Platform.NVIDIA_NIM: 0,
            Platform.NOUS_PORTAL: 0,
            Platform.HERMES: 0
        }
        self.latencies = {
            Platform.NVIDIA_NIM: 0.0,
            Platform.NOUS_PORTAL: 0.0,
            Platform.HERMES: 0.0
        }
    
    async def initialize(self):
        """Initialisiere alle Plattformen"""
        logger.info("🚀 Initializing Multi-Platform Client...")
        
        # NVIDIA NIM
        try:
            nvidia_config = NIMConfig(
                api_key=os.getenv("NVIDIA_API_KEY", "test-key")
            )
            nvidia_client = NVIDIANIMClient(nvidia_config)
            await nvidia_client.initialize()
            self.platforms[Platform.NVIDIA_NIM] = nvidia_client
            logger.info("✅ NVIDIA NIM initialized")
        except Exception as e:
            logger.warning(f"⚠️ NVIDIA NIM init failed: {e}")
        
        # Nous Portal
        try:
            nous_config = NousConfig(
                api_key=os.getenv("NOUS_API_KEY", "test-key")
            )
            nous_client = NousResearchClient(nous_config)
            await nous_client.initialize()
            self.platforms[Platform.NOUS_PORTAL] = nous_client
            logger.info("✅ Nous Portal initialized")
        except Exception as e:
            logger.warning(f"⚠️ Nous Portal init failed: {e}")
        
        # Hermes Local
        try:
            hermes_config = HermesConfig(
                api_key=os.getenv("HERMES_API_KEY", "local-dev-key")
            )
            hermes_client = HermesLocalManager(hermes_config)
            await hermes_client.initialize()
            self.platforms[Platform.HERMES] = hermes_client
            logger.info("✅ Hermes Local initialized")
        except Exception as e:
            logger.warning(f"⚠️ Hermes Local init failed: {e}")
        
        if not self.platforms:
            raise Exception("No platforms available!")
    
    def _select_platform(self, strategy: RoutingStrategy) -> List[Platform]:
        """Wähle Plattform basierend auf Strategie"""
        available = list(self.platforms.keys())
        
        if not available:
            raise Exception("No available platforms")
        
        if strategy == RoutingStrategy.ROUND_ROBIN:
            # Wähle mit wenigsten Requests
            return [min(available, key=lambda p: self.request_counts[p])]
        
        elif strategy == RoutingStrategy.WEIGHTED:
            # Bevorzuge: NVIDIA > Nous > Hermes
            weights = {
                Platform.NVIDIA_NIM: 3,
                Platform.NOUS_PORTAL: 2,
                Platform.HERMES: 1
            }
            weighted = []
            for platform in available:
                weight = weights.get(platform, 1)
                weighted.extend([platform] * weight)
            import random
            return [random.choice(weighted)]
        
        elif strategy == RoutingStrategy.LATENCY:
            # Wähle mit niedrigster Latenz
            return [min(available, key=lambda p: self.latencies[p])]
        
        elif strategy == RoutingStrategy.FAILOVER:
            # Returniere sortiert für Fallback-Versuche
            order = [Platform.NVIDIA_NIM, Platform.NOUS_PORTAL, Platform.HERMES]
            return [p for p in order if p in available]
        
        elif strategy == RoutingStrategy.PARALLEL:
            return available
        
        return available
    
    async def deploy_prompt(
        self,
        prompt_id: str,
        name: str,
        system_prompt: str,
        category: str,
        tags: List[str],
        strategy: RoutingStrategy = RoutingStrategy.PARALLEL
    ) -> Dict[str, Any]:
        """Deploye Prompt zu Plattformen"""
        
        platforms = self._select_platform(strategy)
        results = {}
        
        logger.info(f"📤 Deploying prompt '{prompt_id}' to {[p.value for p in platforms]}")
        
        # NVIDIA NIM
        if Platform.NVIDIA_NIM in platforms:
            client = self.platforms[Platform.NVIDIA_NIM]
            result = await client.deploy_prompt(
                prompt_id=prompt_id,
                system_prompt=system_prompt,
                name=name,
                category=category,
                tags=tags,
                metadata={"platform": "unified"}
            )
            results[Platform.NVIDIA_NIM.value] = result
        
        # Nous Portal
        if Platform.NOUS_PORTAL in platforms:
            client = self.platforms[Platform.NOUS_PORTAL]
            result = await client.deploy_prompt(
                prompt_id=prompt_id,
                name=name,
                system_prompt=system_prompt,
                category=category,
                tags=tags
            )
            results[Platform.NOUS_PORTAL.value] = result
        
        # Hermes
        if Platform.HERMES in platforms:
            client = self.platforms[Platform.HERMES]
            result = await client.deploy_skill(
                prompt_id=prompt_id,
                name=name,
                system_prompt=system_prompt,
                category=category,
                tags=tags
            )
            results[Platform.HERMES.value] = result
        
        return {
            "prompt_id": prompt_id,
            "strategy": strategy.value,
            "results": results
        }
    
    async def execute_prompt(
        self,
        prompt_id: str,
        input_text: str,
        strategy: RoutingStrategy = RoutingStrategy.WEIGHTED
    ) -> Dict[str, Any]:
        """Führe Prompt aus"""
        
        platforms = self._select_platform(strategy)
        
        if strategy == RoutingStrategy.FAILOVER:
            # Versuche mit Fallback
            for platform in platforms:
                client = self.platforms[platform]
                
                try:
                    if platform == Platform.NVIDIA_NIM:
                        result = await client.execute_prompt(
                            prompt_id=prompt_id,
                            input_text=input_text
                        )
                    elif platform == Platform.NOUS_PORTAL:
                        result = await client.execute_with_multi_agent(
                            prompt_id=prompt_id,
                            input_text=input_text,
                            use_all_agents=False
                        )
                    else:  # Hermes
                        session_result = await client.create_session()
                        if session_result["status"] == "success":
                            result = await client.execute_prompt(
                                session_id=session_result["session_id"],
                                prompt_id=prompt_id,
                                input_text=input_text
                            )
                        else:
                            continue
                    
                    if result.get("status") == "success":
                        self.request_counts[platform] += 1
                        return {
                            "status": "success",
                            "platform": platform.value,
                            "result": result
                        }
                except Exception as e:
                    logger.warning(f"Failed on {platform.value}: {e}")
                    continue
            
            return {
                "status": "failed",
                "error": "All platforms failed"
            }
        
        elif strategy == RoutingStrategy.PARALLEL:
            # Führe auf allen aus
            results = {}
            
            for platform in platforms:
                client = self.platforms[platform]
                
                try:
                    if platform == Platform.NVIDIA_NIM:
                        result = await client.execute_prompt(
                            prompt_id=prompt_id,
                            input_text=input_text
                        )
                    elif platform == Platform.NOUS_PORTAL:
                        result = await client.execute_with_multi_agent(
                            prompt_id=prompt_id,
                            input_text=input_text
                        )
                    else:  # Hermes
                        session_result = await client.create_session()
                        if session_result["status"] == "success":
                            result = await client.execute_prompt(
                                session_id=session_result["session_id"],
                                prompt_id=prompt_id,
                                input_text=input_text
                            )
                        else:
                            result = {"status": "failed"}
                    
                    results[platform.value] = result
                    self.request_counts[platform] += 1
                except Exception as e:
                    results[platform.value] = {"status": "failed", "error": str(e)}
            
            return {
                "status": "completed",
                "strategy": "parallel",
                "results": results
            }
        
        else:
            # Single platform
            platform = platforms[0]
            client = self.platforms[platform]
            
            try:
                if platform == Platform.NVIDIA_NIM:
                    result = await client.execute_prompt(
                        prompt_id=prompt_id,
                        input_text=input_text
                    )
                elif platform == Platform.NOUS_PORTAL:
                    result = await client.execute_with_multi_agent(
                        prompt_id=prompt_id,
                        input_text=input_text,
                        use_all_agents=False
                    )
                else:  # Hermes
                    session_result = await client.create_session()
                    if session_result["status"] == "success":
                        result = await client.execute_prompt(
                            session_id=session_result["session_id"],
                            prompt_id=prompt_id,
                            input_text=input_text
                        )
                    else:
                        return {"status": "failed", "error": "Session creation failed"}
                
                self.request_counts[platform] += 1
                return {
                    "status": result.get("status"),
                    "platform": platform.value,
                    "result": result
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "platform": platform.value,
                    "error": str(e)
                }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Gib aggregierte Metriken aus"""
        return {
            "request_counts": self.request_counts,
            "platforms": {
                p.value: {
                    "available": p in self.platforms,
                    "metrics": self.platforms[p].get_metrics() if p in self.platforms else None
                }
                for p in Platform
            }
        }
    
    async def close(self):
        """Cleanup"""
        for client in self.platforms.values():
            if hasattr(client, 'close'):
                await client.close()


# Beispiel-Nutzung
async def main():
    client = UnifiedPromptClient()
    await client.initialize()
    
    # Deploy zu allen Plattformen
    deploy_result = await client.deploy_prompt(
        prompt_id="code-review",
        name="Code Security Review",
        system_prompt="Du bist ein Security Expert...",
        category="security",
        tags=["python", "security"],
        strategy=RoutingStrategy.PARALLEL
    )
    
    print("Deploy Result:", deploy_result)
    
    # Execute mit Weighted Routing
    exec_result = await client.execute_prompt(
        prompt_id="code-review",
        input_text="def unsafe_code(): pass",
        strategy=RoutingStrategy.WEIGHTED
    )
    
    print("Execution Result:", exec_result)
    
    # Metriken
    print("Metrics:", client.get_metrics())
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
