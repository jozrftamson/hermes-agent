#!/usr/bin/env python3
"""
Smart API Router - Intelligentes Routing zwischen Plattformen
Features:
- Load-Balancing basierend auf Plattform-Gewichtung
- Health-Check basierte Plattformauswahl
- Automatisches Failover
- Request-Logging & Monitoring
"""

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import httpx
import logging
from datetime import datetime
import json
from enum import Enum
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartRouter")

app = FastAPI(title="Multi-Platform Prompt Router")

class RouteStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    RANDOM = "random"
    FALLBACK = "fallback"
    ALL = "all"

class PlatformHealth:
    def __init__(self):
        self.platforms = {
            "nvidia_nim": {"healthy": True, "latency": 0, "weight": 3},
            "nous_portal": {"healthy": True, "latency": 0, "weight": 2},
            "hermes": {"healthy": True, "latency": 0, "weight": 1},
        }
        self.request_count = {}
        self.reset_counters()
    
    def reset_counters(self):
        for platform in self.platforms:
            self.request_count[platform] = 0

health = PlatformHealth()

@app.get("/health")
async def health_check():
    """System Health Status"""
    return {
        "status": "healthy",
        "platforms": health.platforms,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/prompts/execute")
async def execute_prompt(
    request_body: Dict[str, Any],
    strategy: RouteStrategy = RouteStrategy.WEIGHTED,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Führe Prompt auf einer oder mehreren Plattformen aus
    
    Query Parameter:
    - strategy: round_robin, weighted, random, fallback, all
    """
    
    prompt_id = request_body.get("prompt_id")
    input_text = request_body.get("input", "")
    
    if not prompt_id:
        raise HTTPException(status_code=400, detail="prompt_id required")
    
    logger.info(f"📨 Executing prompt: {prompt_id} with strategy: {strategy}")
    
    # Wähle Plattform basierend auf Strategie
    platforms_to_use = _select_platforms(strategy)
    
    if not platforms_to_use:
        raise HTTPException(status_code=503, detail="No healthy platforms available")
    
    results = []
    
    for platform in platforms_to_use:
        result = await _execute_on_platform(
            platform, prompt_id, input_text
        )
        results.append(result)
        
        # Bei erfolg in Fallback-Strategie abbrechen
        if strategy == RouteStrategy.FALLBACK and result["status"] == "success":
            break
    
    # Asynchrones Logging
    background_tasks.add_task(_log_execution, prompt_id, results, strategy)
    
    if strategy == RouteStrategy.ALL:
        return {
            "prompt_id": prompt_id,
            "strategy": strategy,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    # Bei anderen Strategien: Erstes erfolgreiche Ergebnis oder Fehler
    successful = [r for r in results if r["status"] == "success"]
    if successful:
        return {
            "prompt_id": prompt_id,
            "platform": successful[0]["platform"],
            "strategy": strategy,
            "result": successful[0],
            "timestamp": datetime.now().isoformat()
        }
    
    raise HTTPException(
        status_code=503,
        detail={
            "message": "All platforms failed",
            "errors": results
        }
    )

def _select_platforms(strategy: RouteStrategy) -> List[str]:
    """Wähle Plattformen basierend auf Strategie"""
    healthy = [
        p for p, info in health.platforms.items()
        if info["healthy"]
    ]
    
    if not healthy:
        return []
    
    if strategy == RouteStrategy.ROUND_ROBIN:
        # Wähle Platform mit wenigsten Requests
        selected = min(healthy, key=lambda p: health.request_count[p])
        return [selected]
    
    elif strategy == RouteStrategy.WEIGHTED:
        # Gewichtete Auswahl
        weighted = []
        for platform in healthy:
            weight = health.platforms[platform]["weight"]
            weighted.extend([platform] * weight)
        return [random.choice(weighted)]
    
    elif strategy == RouteStrategy.RANDOM:
        return [random.choice(healthy)]
    
    elif strategy == RouteStrategy.FALLBACK:
        # Sortiere nach Fallback-Reihenfolge
        order = {"nvidia_nim": 0, "nous_portal": 1, "hermes": 2}
        return sorted(healthy, key=lambda p: order.get(p, 99))
    
    elif strategy == RouteStrategy.ALL:
        return healthy
    
    return []

async def _execute_on_platform(
    platform: str,
    prompt_id: str,
    input_text: str
) -> Dict[str, Any]:
    """Führe Prompt auf einer spezifischen Plattform aus"""
    
    health.request_count[platform] += 1
    
    start_time = datetime.now()
    
    try:
        # Platform-spezifische URLs & Headers
        endpoints = {
            "nvidia_nim": {
                "url": "https://api.nvidia.com/v1/prompts/execute",
                "header_key": "NVIDIA_API_KEY"
            },
            "nous_portal": {
                "url": "https://api.nousresearch.com/v1/prompts/execute",
                "header_key": "NOUS_API_KEY"
            },
            "hermes": {
                "url": "http://localhost:8000/prompts/execute",
                "header_key": "HERMES_API_KEY"
            }
        }
        
        config = endpoints[platform]
        
        # TODO: Hole API Key aus Environment
        headers = {
            "Authorization": f"Bearer {_get_api_key(config['header_key'])}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt_id": prompt_id,
            "input": input_text
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                config["url"],
                json=payload,
                headers=headers
            )
            
            latency = (datetime.now() - start_time).total_seconds()
            health.platforms[platform]["latency"] = latency
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "platform": platform,
                    "result": result,
                    "latency": latency
                }
            else:
                return {
                    "status": "failed",
                    "platform": platform,
                    "error": response.text,
                    "latency": latency
                }
    
    except Exception as e:
        logger.error(f"Error on {platform}: {e}")
        health.platforms[platform]["healthy"] = False
        
        return {
            "status": "failed",
            "platform": platform,
            "error": str(e),
            "latency": (datetime.now() - start_time).total_seconds()
        }

def _get_api_key(key_name: str) -> str:
    """Hole API Key aus Environment"""
    import os
    return os.getenv(key_name, "dummy-key-for-testing")

async def _log_execution(
    prompt_id: str,
    results: List[Dict],
    strategy: str
):
    """Asynchrones Logging"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt_id": prompt_id,
        "strategy": strategy,
        "results": results
    }
    
    with open("router_logs.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    logger.info(f"✅ Logged execution for {prompt_id}")

@app.post("/platforms/health/check")
async def check_platform_health(background_tasks: BackgroundTasks):
    """Manueller Health Check aller Plattformen"""
    background_tasks.add_task(_background_health_check)
    return {"status": "health check started"}

async def _background_health_check():
    """Prüfe Health aller Plattformen asynchron"""
    platforms = ["nvidia_nim", "nous_portal", "hermes"]
    
    for platform in platforms:
        try:
            # Dummy health check - kann mit echten endpoints erweitert werden
            health.platforms[platform]["healthy"] = True
            logger.info(f"✅ {platform} health check: OK")
        except Exception as e:
            health.platforms[platform]["healthy"] = False
            logger.error(f"❌ {platform} health check failed: {e}")

@app.get("/stats")
async def get_stats():
    """Statistiken über Request-Verteilung"""
    return {
        "request_count": health.request_count,
        "platform_health": health.platforms,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
