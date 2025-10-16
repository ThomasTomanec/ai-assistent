#!/usr/bin/env python3
"""
Automaticky vyčistí virtualenv od nevyužitých balíčků.
"""

import ast
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# Mapa: import_name -> pip_package_name (pro častá rozdílná jména)
IMPORT_TO_PACKAGE = {
    'cv2': 'opencv-python',
    'PIL': 'pillow',
    'sklearn': 'scikit-learn',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'google': 'google-api-python-client',
    'deepgram': 'deepgram-sdk',
    'webrtcvad': 'webrtcvad-wheels',
}

# Balíčky které NIKDY nesmažeme
PROTECTED_PACKAGES = {
    'pip', 'setuptools', 'wheel', 'pkg-resources'
}

# Dev tools - separovat do requirements-dev.txt
DEV_TOOLS = {
    'black', 'mypy', 'ruff', 'pytest', 'pytest-asyncio',
    'pytest-cov', 'coverage', 'flake8', 'pylint', 'isort'
}


class DependencyCleaner:
    def __init__(self, project_paths=None):
        self.project_paths = project_paths or ['src', 'main.py']
        self.imports = set()
        self.installed_packages = {}

    def log(self, message, emoji="ℹ️"):
        print(f"{emoji} {message}")

    def find_all_imports(self):
        """Najde všechny importy v projektu pomocí AST."""
        self.log("Hledám importy v projektu...", "🔍")

        for path_str in self.project_paths:
            path = Path(path_str)

            if path.is_file() and path.suffix == '.py':
                self._parse_file(path)
            elif path.is_dir():
                for py_file in path.rglob('*.py'):
                    # Přeskoč venv a __pycache__
                    if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                        continue
                    self._parse_file(py_file)

        self.log(f"Nalezeno {len(self.imports)} unikátních importů", "✅")
        return self.imports

    def _parse_file(self, filepath):
        """Parsuje Python soubor a extrahuje importy."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(filepath))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        self.imports.add(module)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        self.imports.add(module)

        except Exception as e:
            self.log(f"⚠️  Chyba při parsování {filepath}: {e}", "⚠️")

    def get_installed_packages(self):
        """Získá seznam nainstalovaných pip balíčků."""
        self.log("Získávám seznam nainstalovaných balíčků...", "📦")

        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format', 'json'],
            capture_output=True,
            text=True
        )

        packages = json.loads(result.stdout)
        self.installed_packages = {
            pkg['name'].lower(): pkg['version']
            for pkg in packages
        }

        self.log(f"Nalezeno {len(self.installed_packages)} nainstalovaných balíčků", "✅")
        return self.installed_packages

    def map_imports_to_packages(self):
        """Mapuje import jména na pip package jména."""
        mapped_packages = set()

        for imp in self.imports:
            # Standardní knihovna - přeskoč
            if self._is_stdlib(imp):
                continue

            # Použij mapu pro speciální případy
            package_name = IMPORT_TO_PACKAGE.get(imp, imp)

            # Normalizuj na lowercase
            package_name = package_name.lower().replace('_', '-')

            # Zkontroluj že je nainstalovaný
            if package_name in self.installed_packages:
                mapped_packages.add(package_name)
            else:
                # Zkus bez úprav
                if imp.lower() in self.installed_packages:
                    mapped_packages.add(imp.lower())

        return mapped_packages

    def _is_stdlib(self, module_name):
        """Zkontroluje jestli je modul součástí standardní knihovny."""
        stdlib_modules = {
            'abc', 'argparse', 'asyncio', 'base64', 'collections', 'concurrent',
            'contextlib', 'copy', 'dataclasses', 'datetime', 'enum', 'functools',
            'gzip', 'hashlib', 'http', 'importlib', 'io', 'itertools', 'json',
            'logging', 'math', 'multiprocessing', 'os', 'pathlib', 'pickle',
            'platform', 'queue', 're', 'shutil', 'socket', 'ssl', 'string',
            'subprocess', 'sys', 'tempfile', 'threading', 'time', 'traceback',
            'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref', 'xml',
        }
        return module_name in stdlib_modules

    def identify_unused_packages(self, used_packages):
        """Identifikuje nevyužité balíčky."""
        all_packages = set(self.installed_packages.keys())
        unused = all_packages - used_packages - PROTECTED_PACKAGES

        return unused

    def create_backup(self):
        """Vytvoří zálohu requirements.txt a pip freeze."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Zálohuj requirements.txt
        if Path('requirements.txt').exists():
            backup_req = f'requirements.txt.backup_{timestamp}'
            Path('requirements.txt').rename(backup_req)
            self.log(f"Zálohován requirements.txt -> {backup_req}", "💾")

        # Vytvoř zálohu všech nainstalovaných balíčků
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'freeze'],
            capture_output=True,
            text=True
        )

        backup_freeze = f'installed_packages_{timestamp}.txt'
        with open(backup_freeze, 'w') as f:
            f.write(result.stdout)

        self.log(f"Zálohován pip freeze -> {backup_freeze}", "💾")

        return backup_req, backup_freeze

    def uninstall_packages(self, packages_to_remove):
        """Odinstaluje balíčky."""
        if not packages_to_remove:
            self.log("Žádné balíčky k odstranění!", "✅")
            return

        self.log(f"Odinstalovávám {len(packages_to_remove)} balíčků...", "🗑️")

        # Odinstaluj v dávkách
        packages_list = list(packages_to_remove)

        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', '-y'] + packages_list,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.log(f"Úspěšně odinstalováno {len(packages_to_remove)} balíčků!", "✅")
        else:
            self.log(f"Chyba při odinstalaci: {result.stderr}", "❌")

    def generate_requirements(self, used_packages):
        """Vygeneruje nový requirements.txt."""
        self.log("Generuji nový requirements.txt...", "📝")

        # Separuj dev tools
        production_packages = []
        dev_packages = []

        for pkg in sorted(used_packages):
            if pkg in DEV_TOOLS:
                dev_packages.append(pkg)
            else:
                # Získej verzi
                version = self.installed_packages.get(pkg, '')
                if version:
                    production_packages.append(f"{pkg}=={version}")
                else:
                    production_packages.append(pkg)

        # Vytvoř requirements.txt (production)
        with open('requirements.txt', 'w') as f:
            f.write("# Production dependencies\n")
            f.write("# Generated: " + datetime.now().isoformat() + "\n\n")
            for pkg in production_packages:
                f.write(pkg + '\n')

        self.log(f"Vytvořen requirements.txt ({len(production_packages)} balíčků)", "✅")

        # Vytvoř requirements-dev.txt
        if dev_packages:
            with open('requirements-dev.txt', 'w') as f:
                f.write("# Development dependencies\n")
                f.write("-r requirements.txt\n\n")
                for pkg in dev_packages:
                    version = self.installed_packages.get(pkg, '')
                    if version:
                        f.write(f"{pkg}=={version}\n")
                    else:
                        f.write(pkg + '\n')

            self.log(f"Vytvořen requirements-dev.txt ({len(dev_packages)} balíčků)", "✅")

    def print_summary(self, used, unused):
        """Vypíše shrnutí."""
        print("\n" + "=" * 60)
        print("📊 SHRNUTÍ")
        print("=" * 60)
        print(f"✅ Použité balíčky: {len(used)}")
        print(f"🗑️  Nevyužité balíčky: {len(unused)}")
        print(f"📦 Celkem nainstalováno: {len(self.installed_packages)}")

        if unused:
            print("\n🗑️  Balíčky k odstranění:")
            for pkg in sorted(unused):
                print(f"   - {pkg}")

    def run(self, auto_confirm=False):
        """Spustí celý proces."""
        print("\n" + "=" * 60)
        print("🧹 AUTOMATICKÉ ČIŠTĚNÍ DEPENDENCIES")
        print("=" * 60 + "\n")

        # 1. Najdi importy
        imports = self.find_all_imports()

        print(f"\n📋 Nalezené importy:")
        for imp in sorted(imports):
            print(f"   - {imp}")

        # 2. Získej nainstalované balíčky
        self.get_installed_packages()

        # 3. Mapuj importy na balíčky
        used_packages = self.map_imports_to_packages()

        # 4. Identifikuj nevyužité
        unused_packages = self.identify_unused_packages(used_packages)

        # 5. Vypíš shrnutí
        self.print_summary(used_packages, unused_packages)

        if not unused_packages:
            self.log("\n✅ Všechny balíčky jsou využité! Nic k odstranění.", "✅")
            return

        # 6. Potvrď akci
        if not auto_confirm:
            print("\n⚠️  VAROVÁNÍ: Budou provedeny následující akce:")
            print("   1. Záloha requirements.txt a pip freeze")
            print("   2. Odinstalace nevyužitých balíčků")
            print("   3. Vygenerování nového requirements.txt")

            response = input("\n❓ Pokračovat? (ano/ne): ").strip().lower()
            if response not in ['ano', 'a', 'yes', 'y']:
                self.log("Operace zrušena.", "❌")
                return

        # 7. Vytvoř zálohy
        self.create_backup()

        # 8. Odinstaluj nevyužité balíčky
        self.uninstall_packages(unused_packages)

        # 9. Vygeneruj nový requirements.txt
        self.generate_requirements(used_packages)

        # 10. Vytvoř lock file
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'freeze'],
            capture_output=True,
            text=True
        )
        with open('requirements.lock', 'w') as f:
            f.write(result.stdout)
        self.log("Vytvořen requirements.lock", "✅")

        print("\n" + "=" * 60)
        print("✅ HOTOVO!")
        print("=" * 60)
        print("\n📁 Vytvořené soubory:")
        print("   - requirements.txt (production)")
        print("   - requirements-dev.txt (development)")
        print("   - requirements.lock (exact versions)")
        print("\n💾 Zálohy:")
        print("   - requirements.txt.backup_*")
        print("   - installed_packages_*.txt")


if __name__ == '__main__':
    # Konfigurace - upravit podle tvého projektu
    cleaner = DependencyCleaner(
        project_paths=['src', 'main.py', 'tests']  # <-- UPRAV PODLE POTŘEBY
    )

    # Spusť čištění
    # auto_confirm=True pro automatické potvrzení (nebezpečné!)
    cleaner.run(auto_confirm=False)
