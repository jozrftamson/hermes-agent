#!/usr/bin/env python3
"""Skill test for mail-auto-draft optional skill."""

import os
import subprocess
from pathlib import Path

class SkillTest:
    def __init__(self):
        self.base = Path(__file__).parent
        self.results = {}

    def test_all(self):
        print("🧪 MAIL AUTO-DRAFT SKILL VERIFICATION")
        print("=" * 70)
        
        # Test 1: Processor
        print("\n1. Testing processor file...")
        processor = self.base / "process_inbox.py"
        if processor.exists():
            result = subprocess.run(["python3", "-m", "py_compile", str(processor)], capture_output=True)
            if result.returncode == 0:
                print("   ✅ process_inbox.py: EXISTS & VALID PYTHON")
                self.results["Processor"] = True
            else:
                print("   ❌ process_inbox.py: SYNTAX ERROR")
                self.results["Processor"] = False
        else:
            print("   ❌ process_inbox.py: NOT FOUND")
            self.results["Processor"] = False

        # Test 2: Systemd Service
        print("\n2. Testing systemd service...")
        service = self.base / "mail-auto-draft.service"
        if service.exists():
            content = service.read_text()
            if "[Unit]" in content and "[Service]" in content:
                print("   ✅ mail-auto-draft.service: EXISTS & VALID")
                self.results["Service"] = True
            else:
                print("   ❌ mail-auto-draft.service: INVALID FORMAT")
                self.results["Service"] = False
        else:
            print("   ❌ mail-auto-draft.service: NOT FOUND")
            self.results["Service"] = False

        # Test 3: Systemd Timer
        print("\n3. Testing systemd timer...")
        timer = self.base / "mail-auto-draft.timer"
        if timer.exists():
            content = timer.read_text()
            if "[Unit]" in content and "[Timer]" in content:
                print("   ✅ mail-auto-draft.timer: EXISTS & VALID")
                self.results["Timer"] = True
            else:
                print("   ❌ mail-auto-draft.timer: INVALID FORMAT")
                self.results["Timer"] = False
        else:
            print("   ❌ mail-auto-draft.timer: NOT FOUND")
            self.results["Timer"] = False

        # Test 4: Config
        print("\n4. Testing config template...")
        config = self.base / "mail-auto-draft-config.yaml"
        if config.exists():
            print("   ✅ mail-auto-draft-config.yaml: EXISTS")
            self.results["Config"] = True
        else:
            print("   ❌ mail-auto-draft-config.yaml: NOT FOUND")
            self.results["Config"] = False

        # Test 5: Setup Script
        print("\n5. Testing setup script...")
        setup = self.base / "setup.sh"
        if setup.exists():
            result = subprocess.run(["bash", "-n", str(setup)], capture_output=True)
            if result.returncode == 0:
                print("   ✅ setup.sh: EXISTS & VALID BASH")
                self.results["Setup"] = True
            else:
                print("   ❌ setup.sh: BASH SYNTAX ERROR")
                self.results["Setup"] = False
        else:
            print("   ❌ setup.sh: NOT FOUND")
            self.results["Setup"] = False

        # Test 6: Documentation
        print("\n6. Testing documentation...")
        docs_ok = True
        for doc in ["README.md", "SKILL.md", "00-START-HERE.md"]:
            if (self.base / doc).exists():
                print(f"   ✅ {doc}: EXISTS")
            else:
                print(f"   ❌ {doc}: NOT FOUND")
                docs_ok = False
        self.results["Docs"] = docs_ok

        # Test 7: Tests
        print("\n7. Testing test files...")
        tests_ok = True
        for test in ["test_mail_auto_draft_skill.py", "conftest.py"]:
            if (self.base / test).exists():
                print(f"   ✅ {test}: EXISTS")
            else:
                print(f"   ❌ {test}: NOT FOUND")
                tests_ok = False
        self.results["Tests"] = tests_ok

        # Summary
        print("\n" + "=" * 70)
        print("📊 RESULTS")
        print("=" * 70)
        
        for name, result in self.results.items():
            status = "✅" if result else "❌"
            print(f"{status} {name}")
        
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        print(f"\n{passed}/{total} checks passed")
        
        if passed == total:
            print("\n✅ ALL CHECKS PASSED - Skill is complete!")
            return True
        else:
            print(f"\n❌ {total - passed} check(s) failed")
            return False

if __name__ == "__main__":
    test = SkillTest()
    success = test.test_all()
    exit(0 if success else 1)
