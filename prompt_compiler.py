#!/usr/bin/env python3
"""
Prompt Compiler & Validator
Automatisiert:
1. Validierung von Contributor-Prompts
2. Metadaten-Extraktion
3. Deployment zu Hermes / NVIDIA NIM / Nous Portal
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
import hashlib
from datetime import datetime

class PromptCompiler:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.prompts_dir = self.base_dir / "prompts"
        self.metadata_file = self.base_dir / "metadata.json"

    def scan_prompts(self) -> List[Dict[str, Any]]:
        """Scanne alle prompt.md Dateien"""
        prompts = []
        for prompt_dir in self.prompts_dir.glob("*/"):
            prompt_file = prompt_dir / "prompt.md"
            if prompt_file.exists():
                prompts.append(self._parse_prompt(prompt_file))
        return prompts

    def _parse_prompt(self, prompt_file: Path) -> Dict[str, Any]:
        """Parse eine prompt.md Datei"""
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Frontmatter extrahieren
        lines = content.split("\n")
        metadata = {}
        prompt_name = prompt_file.parent.name

        # Einfache Parsing: Suche nach **Key:** Pattern
        for line in lines:
            if line.startswith("**") and ":" in line:
                key, value = line.split(":", 1)
                key = key.replace("**", "").strip().lower()
                metadata[key] = value.strip()

        # Sections extrahieren
        sections = self._extract_sections(content)

        return {
            "id": prompt_name,
            "name": metadata.get("prompt name", prompt_name),
            "category": metadata.get("category", "general"),
            "version": metadata.get("version", "1.0"),
            "tags": [t.strip() for t in metadata.get("tags", "").split(",")],
            "model": metadata.get("model", "auto"),
            "description": metadata.get("beschreibung", ""),
            "system_prompt": sections.get("system prompt", ""),
            "example_input": sections.get("beispiel input", ""),
            "example_output": sections.get("beispiel output", ""),
            "config": metadata.get("konfiguration", {}),
            "file_path": str(prompt_file),
            "checksum": self._checksum(content),
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extrahiere Abschnitte nach ## Headers"""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            if line.startswith("##"):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line.replace("##", "").strip().lower()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _checksum(self, content: str) -> str:
        """Generiere SHA256 Checksum für Versioning"""
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def validate_prompts(self, prompts: List[Dict]) -> Dict[str, List[str]]:
        """Validiere alle Prompts"""
        errors = {}
        warnings = {}

        for prompt in prompts:
            prompt_errors = []
            prompt_warnings = []

            # Pflichtfelder
            if not prompt.get("system_prompt"):
                prompt_errors.append("❌ System Prompt fehlt")
            if not prompt.get("category"):
                prompt_errors.append("❌ Category fehlt")
            if not prompt.get("model"):
                prompt_warnings.append("⚠️ Model nicht spezifiziert (nutze 'auto')")

            # Längen-Checks
            if len(prompt.get("system_prompt", "")) > 5000:
                prompt_warnings.append("⚠️ System Prompt sehr lang (>5000 chars)")

            if prompt_errors:
                errors[prompt["id"]] = prompt_errors
            if prompt_warnings:
                warnings[prompt["id"]] = prompt_warnings

        return {"errors": errors, "warnings": warnings}

    def compile_metadata(self, prompts: List[Dict]) -> Dict[str, Any]:
        """Generiere metadata.json"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_prompts": len(prompts),
            "categories": list(set(p["category"] for p in prompts)),
            "prompts": {p["id"]: {k: v for k, v in p.items() if k != "system_prompt"} 
                       for p in prompts},
            "full_prompts": {p["id"]: p for p in prompts}  # Für interne Nutzung
        }

    def export_for_hermes(self, prompts: List[Dict]) -> str:
        """Exportiere Skills für Hermes"""
        hermes_skills = {}
        for prompt in prompts:
            hermes_skills[prompt["id"]] = {
                "name": prompt["name"],
                "description": prompt["description"],
                "system_prompt": prompt["system_prompt"],
                "tags": prompt["tags"],
                "models": [prompt["model"]] if prompt["model"] != "auto" else ["auto"]
            }
        return json.dumps(hermes_skills, indent=2, ensure_ascii=False)

    def export_for_nvidia(self, prompts: List[Dict]) -> str:
        """Exportiere für NVIDIA NIM API"""
        nim_config = {
            "version": "1.0",
            "prompts": []
        }
        for prompt in prompts:
            nim_config["prompts"].append({
                "id": prompt["id"],
                "name": prompt["name"],
                "system_prompt": prompt["system_prompt"],
                "inference_config": {
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "model": "nvidia/llama-3.1-405b"
                }
            })
        return json.dumps(nim_config, indent=2)

    def export_for_nous_portal(self, prompts: List[Dict]) -> str:
        """Exportiere für Nous Research Portal"""
        portal_config = {
            "workspace": "my-project",
            "prompts": {}
        }
        for prompt in prompts:
            portal_config["prompts"][prompt["id"]] = {
                "name": prompt["name"],
                "system_prompt": prompt["system_prompt"],
                "category": prompt["category"],
                "recommended_model": prompt["model"]
            }
        return json.dumps(portal_config, indent=2)

    def run(self):
        """Hauptfunktion: Scan → Validate → Compile"""
        print("🔍 Scanne Prompts...")
        prompts = self.scan_prompts()
        print(f"✅ {len(prompts)} Prompts gefunden\n")

        print("🔎 Validiere...")
        validation = self.validate_prompts(prompts)
        if validation["errors"]:
            print("❌ FEHLER:")
            for prompt_id, errors in validation["errors"].items():
                print(f"  {prompt_id}:")
                for error in errors:
                    print(f"    {error}")
        if validation["warnings"]:
            print("⚠️  WARNUNGEN:")
            for prompt_id, warnings in validation["warnings"].items():
                print(f"  {prompt_id}:")
                for warning in warnings:
                    print(f"    {warning}")

        print("\n📝 Generiere Metadaten...")
        metadata = self.compile_metadata(prompts)
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"✅ metadata.json aktualisiert")

        print("\n🚀 Exportiere für verschiedene Plattformen...")
        
        # Hermes Export
        hermes_export = self.export_for_hermes(prompts)
        with open(self.base_dir / "exports" / "hermes_skills.json", "w") as f:
            f.write(hermes_export)
        print("✅ hermes_skills.json")

        # NVIDIA Export
        nvidia_export = self.export_for_nvidia(prompts)
        with open(self.base_dir / "exports" / "nvidia_nim_config.json", "w") as f:
            f.write(nvidia_export)
        print("✅ nvidia_nim_config.json")

        # Nous Portal Export
        nous_export = self.export_for_nous_portal(prompts)
        with open(self.base_dir / "exports" / "nous_portal_config.json", "w") as f:
            f.write(nous_export)
        print("✅ nous_portal_config.json")

        print("\n✨ Fertig!")

if __name__ == "__main__":
    compiler = PromptCompiler()
    compiler.run()
