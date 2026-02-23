# 3. Bitbucket-Integration für Multi-Agent KI-System

## 3.1 Übersicht

Die Bitbucket-Integration ermöglicht KI-Agenten, sicher und automatisiert Code-Änderungen in Kunden-Repositorys vorzunehmen. Die Integration ist auf Shopware-Projekte mit DDEV-Workflow optimiert.

## 3.2 Bitbucket-API-Integration

### 3.2.1 Authentifizierung

#### Option A: App Passwords (Empfohlen für Agenten)

```yaml
# config/bitbucket/auth.yaml
auth:
  type: app_password
  workspace: "agentur-name"
  
  # Pro Kunde ein dedizierter App Password
  customers:
    alp-shopware:
      username: "agentur-bot-alp"
      app_password: "${BITBUCKET_APP_PASSWORD_ALP}"  # Env-Variable
      email: "bot-alp@agentur.de"
      
    kraft-shopware:
      username: "agentur-bot-kraft"
      app_password: "${BITBUCKET_APP_PASSWORD_KRAFT}"
      email: "bot-kraft@agentur.de"
      
    lupus:
      username: "agentur-bot-lupus"
      app_password: "${BITBUCKET_APP_PASSWORD_LUPUS}"
      email: "bot-lupus@agentur.de"
```

**App Password erstellen:**
1. Bitbucket → Personal Settings → App passwords → Create app password
2. Berechtigungen: Repositories (Read, Write), Pull requests (Read, Write)
3. Ablauf: 90 Tage (Rotation erforderlich)

#### Option B: OAuth 2.0 (Für erweiterte Integrationen)

```python
# agents/bitbucket/oauth_client.py
from dataclasses import dataclass
from typing import Optional
import requests

@dataclass
class BitbucketOAuthConfig:
    client_id: str
    client_secret: str
    workspace: str
    redirect_uri: str = "http://localhost:8080/callback"
    
class BitbucketOAuthClient:
    BASE_URL = "https://bitbucket.org/site/oauth2"
    API_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, config: BitbucketOAuthConfig):
        self.config = config
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
```

### 3.2.2 Repository-Verwaltung

#### Repository-Liste pro Kunde

```yaml
# config/repositories.yaml
repositories:
  # Mapping: Kunde → Repository(s)
  alp-shopware:
    primary:
      name: "alp-shopware"
      slug: "alp-shopware"
      workspace: "agentur-name"
      default_branch: "main"
      shopware_version: "6.5.8"
      php_version: "8.2"
    
    # Zusätzliche Repos (Plugins, Themes)
    plugins:
      - name: "alp-custom-plugin"
        slug: "alp-custom-plugin"
        path: "custom/plugins/AlpCustom"
        
    deployment:
      pipeline_enabled: true
      staging_branch: "develop"
      production_branch: "main"
      
  kraft-shopware:
    primary:
      name: "kraft-shopware"
      slug: "kraft-shopware"
      workspace: "agentur-name"
      default_branch: "master"
      shopware_version: "6.7.0"
      php_version: "8.3"
    
  lupus:
    primary:
      name: "lupus"
      slug: "lupus"
      workspace: "agentur-name"
      default_branch: "main"
      shopware_version: "6.5.4"
      php_version: "8.1"
```

#### Repository-API-Client

```python
# agents/bitbucket/repository_client.py
from typing import List, Dict, Any, Optional
import requests
import base64

class BitbucketRepositoryClient:
    """
    Bitbucket API Client für Repository-Operationen
    Dokumentation: https://developer.atlassian.com/cloud/bitbucket/rest/
    """
    
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, workspace: str, username: str, app_password: str):
        self.workspace = workspace
        self.auth = (username, app_password)
    
    def get_repositories(self, customer: Optional[str] = None) -> List[Dict]:
        """Alle Repositories des Workspaces abrufen"""
        url = f"{self.BASE_URL}/repositories/{self.workspace}"
        
        if customer:
            url += f"?q=name~\"{customer}\""
        
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json().get("values", [])
    
    def get_repository(self, repo_slug: str) -> Dict[str, Any]:
        """Details eines spezifischen Repositories"""
        url = f"{self.BASE_URL}/repositories/{self.workspace}/{repo_slug}"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()
    
    def get_branches(self, repo_slug: str) -> List[Dict]:
        """Alle Branches eines Repositories auflisten"""
        url = f"{self.BASE_URL}/repositories/{self.workspace}/{repo_slug}/refs/branches"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json().get("values", [])
    
    def get_file_content(self, repo_slug: str, file_path: str, branch: str = "main") -> str:
        """Dateiinhalt aus Repository lesen"""
        url = (
            f"{self.BASE_URL}/repositories/{self.workspace}/{repo_slug}"
            f"/src/{branch}/{file_path}"
        )
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.text
```

### 3.2.3 Branch-Management

```python
# agents/bitbucket/branch_manager.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import requests

@dataclass
class BranchConfig:
    """Konfiguration für Agent-Branches"""
    prefix: str = "feature/"
    ticket_pattern: str = "ticket-{ticket_id}"
    max_branch_name_length: int = 50
    
    def generate_branch_name(self, ticket_id: str, description: str) -> str:
        """Branch-Name nach Konvention generieren"""
        # Description kürzen und normalisieren
        clean_desc = description.lower()
        clean_desc = clean_desc.replace(" ", "-")
        clean_desc = "".join(c for c in clean_desc if c.isalnum() or c == "-")
        clean_desc = clean_desc[:30]  # Max 30 Zeichen
        
        branch_name = f"{self.prefix}{self.ticket_pattern.format(ticket_id=ticket_id)}-{clean_desc}"
        return branch_name[:self.max_branch_name_length]

class BitbucketBranchManager:
    """Verwaltung von Branches über Bitbucket API"""
    
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, workspace: str, repo_slug: str, auth):
        self.workspace = workspace
        self.repo_slug = repo_slug
        self.auth = auth
    
    def create_branch(self, branch_name: str, source_branch: str = "main") -> dict:
        """Neuen Branch erstellen"""
        # Source-Branch Hash ermitteln
        source_hash = self._get_branch_hash(source_branch)
        
        url = (
            f"{self.BASE_URL}/repositories/{self.workspace}/{self.repo_slug}"
            f"/refs/branches"
        )
        
        payload = {
            "name": branch_name,
            "target": {"hash": source_hash}
        }
        
        response = requests.post(url, auth=self.auth, json=payload)
        response.raise_for_status()
        return response.json()
    
    def _get_branch_hash(self, branch_name: str) -> str:
        """Commit-Hash eines Branches ermitteln"""
        url = (
            f"{self.BASE_URL}/repositories/{self.workspace}/{self.repo_slug}"
            f"/refs/branches/{branch_name}"
        )
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()["target"]["hash"]
    
    def branch_exists(self, branch_name: str) -> bool:
        """Prüfen ob Branch existiert"""
        try:
            self._get_branch_hash(branch_name)
            return True
        except requests.HTTPError:
            return False
```

### 3.2.4 Commit-Erstellung

```python
# agents/bitbucket/commit_manager.py
import base64
import json
from typing import List, Dict, Optional
import requests

class BitbucketCommitManager:
    """Erstellung von Commits über Bitbucket API"""
    
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, workspace: str, repo_slug: str, auth):
        self.workspace = workspace
        self.repo_slug = repo_slug
        self.auth = auth
    
    def create_commit(
        self,
        branch: str,
        message: str,
        files: List[Dict[str, str]],
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> dict:
        """
        Commit mit mehreren Dateien erstellen
        
        Args:
            branch: Ziel-Branch
            message: Commit-Nachricht
            files: Liste von {"path": str, "content": str, "encoding": "utf-8|base64"}
        """
        url = f"{self.BASE_URL}/repositories/{self.workspace}/{self.repo_slug}/src"
        
        data = {"message": message, "branch": branch}
        
        if author_name and author_email:
            data["author"] = f"{author_name} <{author_email}>"
        
        files_data = {}
        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            encoding = file_info.get("encoding", "utf-8")
            
            if encoding == "base64":
                files_data[path] = base64.b64decode(content)
            else:
                files_data[path] = content.encode("utf-8")
        
        response = requests.post(
            url,
            auth=self.auth,
            data=data,
            files={k: (k, v) for k, v in files_data.items()}
        )
        response.raise_for_status()
        return response.json()
```

### 3.2.5 Pull Request Erstellung

```python
# agents/bitbucket/pr_manager.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests

@dataclass
class PullRequestTemplate:
    """Template für PR-Beschreibungen"""
    
    template: str = """
## Ticket
{ticket_id}

## Änderungen
{changes_description}

## Testing
- [ ] Code wurde lokal getestet
- [ ] Unit Tests vorhanden
- [ ] Manuelles Testing durchgeführt

## Shopware-Version
{shopware_version}

## Breaking Changes
{breaking_changes}

## Checkliste
- [ ] Code folgt Projekt-Konventionen
- [ ] Keine sensiblen Daten im Commit
- [ ] DDEV-Umgebung aktualisiert
- [ ] Composer-Abhängigkeiten geprüft

---
Automatisch erstellt von KI-Agent
Zeitstempel: {timestamp}
"""
    
    def render(self, ticket_id: str, changes_description: str,
               shopware_version: str = "6.5.x", breaking_changes: str = "Keine") -> str:
        return self.template.format(
            ticket_id=ticket_id,
            changes_description=changes_description,
            shopware_version=shopware_version,
            breaking_changes=breaking_changes,
            timestamp=datetime.now().isoformat()
        )

class BitbucketPullRequestManager:
    """Verwaltung von Pull Requests"""
    
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, workspace: str, repo_slug: str, auth):
        self.workspace = workspace
        self.repo_slug = repo_slug
        self.auth = auth
        self.template = PullRequestTemplate()
    
    def create_pull_request(
        self,
        title: str,
        source_branch: str,
        destination_branch: str = "main",
        description: Optional[str] = None,
        reviewers: Optional[List[str]] = None,
        close_source_branch: bool = True
    ) -> dict:
        """Neuen Pull Request erstellen"""
        url = (
            f"{self.BASE_URL}/repositories/{self.workspace}/{self.repo_slug}"
            f"/pullrequests"
        )
        
        payload = {
            "title": title,
            "source": {"branch": {"name": source_branch}},
            "destination": {"branch": {"name": destination_branch}},
            "close_source_branch": close_source_branch
        }
        
        if description:
            payload["description"] = description
        
        if reviewers:
            payload["reviewers"] = [{"username": r} for r in reviewers]
        
        response = requests.post(url, auth=self.auth, json=payload)
        response.raise_for_status()
        return response.json()
```


## 3.3 Git-Workflow für Agenten

### 3.3.1 Branching-Strategie

```yaml
# config/git-workflow.yaml
git_workflow:
  # Hauptbranches
  main_branches:
    - main
    - master
    - develop
  
  # Agent-Branch Konventionen
  agent_branches:
    # Feature-Branches für neue Funktionen
    feature:
      pattern: "feature/ticket-{ticket_id}-{short-desc}"
      example: "feature/ticket-1234-add-payment-method"
      source: "main"
      
    # Bugfix-Branches
    bugfix:
      pattern: "bugfix/ticket-{ticket_id}-{short-desc}"
      example: "bugfix/ticket-5678-fix-checkout-error"
      source: "main"
      
    # Hotfix-Branches
    hotfix:
      pattern: "hotfix/ticket-{ticket_id}-{short-desc}"
      example: "hotfix/ticket-9999-critical-security-fix"
      source: "main"
      
    # Plugin-spezifische Branches
    plugin:
      pattern: "plugin/{plugin-name}-ticket-{ticket_id}"
      example: "plugin/alp-custom-ticket-4321"
      source: "main"
  
  # Automatische Cleanup-Einstellungen
  cleanup:
    delete_merged_branches: true
    delete_after_days: 7
    protected_branches: ["main", "master", "develop"]
```

### 3.3.2 Commit-Nachrichten-Konventionen

```yaml
# config/commit-conventions.yaml
commit_conventions:
  # Format: type(scope): subject [ticket-id]
  format: "{type}({scope}): {subject} [{ticket_id}]"
  
  types:
    feat:     "Neue Funktion"
    fix:      "Bugfix"
    docs:     "Dokumentation"
    style:    "Formatierung (keine Code-Änderung)"
    refactor: "Code-Refactoring"
    perf:     "Performance-Optimierung"
    test:     "Tests hinzugefügt/aktualisiert"
    chore:    "Wartung/Build-Änderungen"
    
  scopes:
    shopware:    "Shopware-Core"
    plugin:      "Plugin-Änderung"
    theme:       "Theme-Änderung"
    config:      "Konfiguration"
    composer:    "Composer-Abhängigkeiten"
    db:          "Datenbank-Migrationen"
    
  examples:
    - "feat(plugin): add new payment provider integration [TICKET-1234]"
    - "fix(theme): correct mobile menu styling [TICKET-5678]"
    - "chore(composer): update shopware/core to 6.5.8 [TICKET-9012]"
    - "refactor(shopware): optimize cart calculation [TICKET-3456]"
```

```python
# agents/git/commit_formatter.py
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class CommitMessage:
    type: str
    scope: str
    subject: str
    ticket_id: str
    body: Optional[str] = None
    breaking: bool = False
    
    def format(self) -> str:
        """Commit-Nachricht nach Konvention formatieren"""
        message = f"{self.type}({self.scope}): {self.subject} [{self.ticket_id}]"
        
        if self.breaking:
            message = message.replace(f"{self.type}(", f"{self.type}(!)(", 1)
        
        if self.body:
            message += f"\n\n{self.body}"
        
        return message
    
    @classmethod
    def parse(cls, message: str) -> "CommitMessage":
        """Commit-Nachricht parsen"""
        pattern = r"^(\w+)(\((\w+)\))?:\s*(.+?)\s*\[(\w+-\d+)\]$"
        match = re.match(pattern, message, re.MULTILINE)
        
        if not match:
            raise ValueError(f"Invalid commit message format: {message}")
        
        commit_type = match.group(1)
        scope = match.group(3) or "general"
        subject = match.group(4)
        ticket_id = match.group(5)
        
        lines = message.split("\n")
        body = None
        if len(lines) > 2:
            body = "\n".join(lines[2:]).strip() or None
        
        breaking = "!" in commit_type
        
        return cls(
            type=commit_type.replace("!", ""),
            scope=scope,
            subject=subject,
            ticket_id=ticket_id,
            body=body,
            breaking=breaking
        )
```

### 3.3.3 PR-Beschreibungs-Templates

```yaml
# config/pr-templates.yaml
pull_request_templates:
  # Standard-Template für Feature-PRs
  feature:
    template: |
      ## Zusammenfassung
      {{description}}
      
      ## Verwandte Tickets
      - {{ticket_id}}
      
      ## Änderungstyp
      - [ ] Neues Feature
      - [ ] Bugfix
      - [ ] Dokumentation
      - [ ] Refactoring
      - [ ] Performance
      
      ## Testing
      ### Manuelle Tests
      - [ ] Funktion lokal in DDEV getestet
      - [ ] Shopware-Version kompatibel: {{shopware_version}}
      - [ ] Keine Breaking Changes
      
      ### Automatisierte Tests
      - [ ] Unit Tests vorhanden
      - [ ] Integration Tests vorhanden
      - [ ] Alle Tests grün
      
      ## Betroffene Bereiche
      {{affected_areas}}
      
      ## Breaking Changes
      {{breaking_changes}}
      
      ## Review-Checkliste
      - [ ] Code folgt PSR-12
      - [ ] Keine sensiblen Daten
      - [ ] Kommentare bei komplexer Logik
      - [ ] DDEV-Config aktualisiert falls nötig
      
      ---
      Automatisch erstellt von {{agent_name}}
      Zeitstempel: {{timestamp}}
    
  # Template für Plugin-Änderungen
  plugin:
    template: |
      ## Plugin-Änderung
      
      **Plugin:** {{plugin_name}}
      **Version:** {{plugin_version}}
      **Shopware-Kompatibilität:** {{shopware_version}}
      
      ## Änderungen
      {{description}}
      
      ## Struktur
      ```
      custom/plugins/{{plugin_name}}/
      {{plugin_structure}}
      ```
      
      ## Testing
      - [ ] Plugin in DDEV installiert
      - [ ] Plugin aktiviert
      - [ ] Funktionalität geprüft
      - [ ] Keine Konflikte mit anderen Plugins
      
      ## Migrationen
      {{migrations}}
      
      ---
      Automatisch erstellt von {{agent_name}}
```

## 3.4 Repository-Konfiguration

### 3.4.1 Mapping-Tabelle Kunde → Repositories

```yaml
# config/customer-repository-mapping.yaml
customer_repository_mapping:
  version: "1.0"
  
  # ALP-Shopware Projekt
  alp-shopware:
    customer_info:
      name: "ALP GmbH"
      contact_email: "tech@alp-shopware.de"
      priority: "high"
    
    repositories:
      primary:
        name: "alp-shopware"
        workspace: "agentur-name"
        slug: "alp-shopware"
        clone_url: "https://bitbucket.org/agentur-name/alp-shopware.git"
        
      plugins:
        - name: "AlpCustomPlugin"
          repo_slug: "alp-custom-plugin"
          local_path: "custom/plugins/AlpCustomPlugin"
          git_url: "https://bitbucket.org/agentur-name/alp-custom-plugin.git"
          
        - name: "AlpPayment"
          repo_slug: "alp-payment-plugin"
          local_path: "custom/plugins/AlpPayment"
          git_url: "https://bitbucket.org/agentur-name/alp-payment-plugin.git"
      
      themes:
        - name: "AlpTheme"
          repo_slug: "alp-theme"
          local_path: "custom/apps/alp-theme"
          git_url: "https://bitbucket.org/agentur-name/alp-theme.git"
    
    configuration:
      shopware_version: "6.5.8"
      php_version: "8.2"
      default_branch: "main"
      deployment:
        staging: "develop"
        production: "main"
        pipeline: "bitbucket-pipelines.yml"
  
  # Kraft-Shopware Projekt
  kraft-shopware:
    customer_info:
      name: "Kraft Online GmbH"
      contact_email: "dev@kraft-shopware.de"
      priority: "medium"
    
    repositories:
      primary:
        name: "kraft-shopware"
        workspace: "agentur-name"
        slug: "kraft-shopware"
        clone_url: "https://bitbucket.org/agentur-name/kraft-shopware.git"
      
      plugins:
        - name: "KraftCustom"
          repo_slug: "kraft-custom"
          local_path: "custom/plugins/KraftCustom"
          git_url: "https://bitbucket.org/agentur-name/kraft-custom.git"
    
    configuration:
      shopware_version: "6.7.0"
      php_version: "8.3"
      default_branch: "master"
  
  # Lupus Projekt
  lupus:
    customer_info:
      name: "Lupus Medical"
      contact_email: "it@lupus-medical.de"
      priority: "high"
    
    repositories:
      primary:
        name: "lupus"
        workspace: "agentur-name"
        slug: "lupus"
        clone_url: "https://bitbucket.org/agentur-name/lupus.git"
    
    configuration:
      shopware_version: "6.5.4"
      php_version: "8.1"
      default_branch: "main"
```

### 3.4.2 Shopware-Versions-Erkennung

```python
# agents/shopware/version_detector.py
import json
import re
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class ShopwareVersion:
    major: int
    minor: int
    patch: int
    stability: str = "stable"
    
    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @property
    def short_version(self) -> str:
        return f"{self.major}.{self.minor}"
    
    def is_at_least(self, major: int, minor: int = 0) -> bool:
        if self.major > major:
            return True
        if self.major == major and self.minor >= minor:
            return True
        return False
    
    def supports_feature(self, feature: str) -> bool:
        feature_requirements = {
            "app_system_v2": (6, 5),
            "new_media_management": (6, 5),
            "flow_builder_v2": (6, 6),
            "es8_support": (6, 5),
            "api_aware_rules": (6, 5),
        }
        required = feature_requirements.get(feature)
        if not required:
            return True
        return self.is_at_least(*required)

class ShopwareVersionDetector:
    """Erkennt Shopware-Version aus verschiedenen Quellen"""
    
    def detect_from_composer(self, composer_json_content: str) -> Optional[ShopwareVersion]:
        try:
            data = json.loads(composer_json_content)
            require = data.get("require", {})
            
            core_version = require.get("shopware/core", "")
            if not core_version:
                core_version = require.get("shopware/platform", "")
            
            return self._parse_version_constraint(core_version)
        except (json.JSONDecodeError, ValueError):
            return None
    
    def _parse_version_constraint(self, constraint: str) -> Optional[ShopwareVersion]:
        clean = constraint.lstrip("~^>=<!").strip()
        match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", clean)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3)) if match.group(3) else 0
            return ShopwareVersion(major, minor, patch)
        return None
    
    def get_project_requirements(self, version: ShopwareVersion) -> Dict:
        requirements = {
            "php": "8.2",
            "mysql": "8.0",
            "elasticsearch": "8.x",
            "redis": "7.x",
            "node": "18.x",
            "composer": "2.6+",
        }
        
        if version.major == 6:
            if version.minor <= 4:
                requirements.update({
                    "php": "8.1",
                    "mysql": "5.7",
                    "elasticsearch": "7.x",
                    "node": "16.x",
                })
            elif version.minor == 5:
                requirements.update({
                    "php": "8.2",
                    "mysql": "8.0",
                    "elasticsearch": "8.x",
                    "node": "18.x",
                })
            elif version.minor >= 6:
                requirements.update({
                    "php": "8.3",
                    "mysql": "8.0",
                    "elasticsearch": "8.x",
                    "node": "20.x",
                })
        
        return requirements
```


### 3.4.3 Projektstruktur-Erkennung

```python
# agents/shopware/project_structure.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import json

@dataclass
class PluginInfo:
    name: str
    path: str
    namespace: str
    composer_name: Optional[str] = None
    version: str = "1.0.0"
    has_administration: bool = False
    has_storefront: bool = False
    
@dataclass
class ThemeInfo:
    name: str
    path: str
    parent_theme: Optional[str] = None
    style_path: str = ""
    
@dataclass
class ProjectStructure:
    shopware_version: str = "unknown"
    php_version: str = "8.2"
    plugins: List[PluginInfo] = field(default_factory=list)
    themes: List[ThemeInfo] = field(default_factory=list)
    has_custom_apps: bool = False
    has_custom_plugins: bool = False
    has_custom_static: bool = False
    config_paths: Dict[str, str] = field(default_factory=dict)

class ProjectStructureAnalyzer:
    """Analysiert die Struktur eines Shopware-Projekts"""
    
    def analyze(self, project_root: Path) -> ProjectStructure:
        structure = ProjectStructure()
        structure.shopware_version = self._detect_version(project_root)
        structure.plugins = self._scan_plugins(project_root)
        structure.themes = self._scan_themes(project_root)
        structure.has_custom_apps = (project_root / "custom/apps").exists()
        structure.has_custom_plugins = (project_root / "custom/plugins").exists()
        structure.has_custom_static = (project_root / "custom/static-plugins").exists()
        structure.config_paths = self._find_config_files(project_root)
        return structure
    
    def _detect_version(self, project_root: Path) -> str:
        composer_file = project_root / "composer.json"
        if not composer_file.exists():
            return "unknown"
        try:
            data = json.loads(composer_file.read_text())
            require = data.get("require", {})
            core = require.get("shopware/core", require.get("shopware/platform", ""))
            return core.lstrip("~^>=<!").strip()
        except (json.JSONDecodeError, IOError):
            return "unknown"
    
    def _scan_plugins(self, project_root: Path) -> List[PluginInfo]:
        plugins = []
        plugin_dirs = [
            project_root / "custom/plugins",
            project_root / "custom/apps",
            project_root / "custom/static-plugins",
        ]
        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                continue
            for plugin_path in plugin_dir.iterdir():
                if not plugin_path.is_dir():
                    continue
                info = self._parse_plugin_info(plugin_path)
                if info:
                    plugins.append(info)
        return plugins
    
    def _parse_plugin_info(self, plugin_path: Path) -> Optional[PluginInfo]:
        composer_file = plugin_path / "composer.json"
        name = plugin_path.name
        namespace = name
        version = "1.0.0"
        composer_name = None
        
        if composer_file.exists():
            try:
                data = json.loads(composer_file.read_text())
                composer_name = data.get("name")
                version = data.get("version", "1.0.0")
                autoload = data.get("autoload", {}).get("psr-4", {})
                if autoload:
                    namespace = list(autoload.keys())[0].rstrip("\\")
            except (json.JSONDecodeError, IOError):
                pass
        
        has_admin = (plugin_path / "src/Resources/app/administration").exists()
        has_storefront = (plugin_path / "src/Resources/app/storefront").exists()
        
        return PluginInfo(
            name=name,
            path=str(plugin_path.relative_to(plugin_path.parent.parent.parent)),
            namespace=namespace,
            composer_name=composer_name,
            version=version,
            has_administration=has_admin,
            has_storefront=has_storefront
        )
    
    def _scan_themes(self, project_root: Path) -> List[ThemeInfo]:
        themes = []
        theme_dirs = [project_root / "custom/apps", project_root / "custom/plugins"]
        for theme_dir in theme_dirs:
            if not theme_dir.exists():
                continue
            for theme_path in theme_dir.iterdir():
                if not theme_path.is_dir():
                    continue
                theme_json = theme_path / "theme.json"
                if theme_json.exists():
                    info = self._parse_theme_info(theme_path, theme_json)
                    if info:
                        themes.append(info)
        return themes
    
    def _parse_theme_info(self, theme_path: Path, theme_json: Path) -> Optional[ThemeInfo]:
        try:
            data = json.loads(theme_json.read_text())
            return ThemeInfo(
                name=data.get("name", theme_path.name),
                path=str(theme_path.relative_to(theme_path.parent.parent.parent)),
                parent_theme=data.get("parentThemeId"),
                style_path=data.get("style", ["app/storefront/src/scss/base.scss"])[0]
            )
        except (json.JSONDecodeError, IOError):
            return None
    
    def _find_config_files(self, project_root: Path) -> Dict[str, str]:
        configs = {}
        config_files = {
            "composer": "composer.json",
            "ddev": ".ddev/config.yaml",
            "pipelines": "bitbucket-pipelines.yml",
            "env": ".env",
            "env_local": ".env.local",
            "phpunit": "phpunit.xml.dist",
            "ecs": "ecs.php",
            "phpstan": "phpstan.neon.dist",
        }
        for name, path in config_files.items():
            full_path = project_root / path
            if full_path.exists():
                configs[name] = str(path)
        return configs
```

## 3.5 Sicherheitsmaßnahmen

### 3.5.1 Token-Scopes und Berechtigungen

```yaml
# config/security/token-scopes.yaml
token_management:
  # App Password Konfiguration
  app_passwords:
    rotation_days: 90
    warning_before_days: 7
    
    # Standard-Berechtigungen für Agenten
    default_scopes:
      repositories:
        - read        # Repository lesen
        - write       # Repository schreiben (Commits, Branches)
      
      pullrequests:
        - read        # PRs lesen
        - write       # PRs erstellen, updaten
      
      # KEINE Admin-Berechtigungen
      # - admin:write
      # - admin:read
      # - project:write
  
  # Pro-Kunde Token-Isolation
  customer_isolation:
    enabled: true
    token_pattern: "BITBUCKET_APP_PASSWORD_{CUSTOMER_UPPER}"
    
    customers:
      alp-shopware:
        token_env: "BITBUCKET_APP_PASSWORD_ALP"
        allowed_repos:
          - "alp-shopware"
          - "alp-custom-plugin"
          - "alp-payment-plugin"
          - "alp-theme"
        
      kraft-shopware:
        token_env: "BITBUCKET_APP_PASSWORD_KRAFT"
        allowed_repos:
          - "kraft-shopware"
          - "kraft-custom"
        
      lupus:
        token_env: "BITBUCKET_APP_PASSWORD_LUPUS"
        allowed_repos:
          - "lupus"
```

```python
# agents/security/token_validator.py
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Set
import fnmatch

@dataclass
class TokenConfig:
    customer: str
    token_env: str
    allowed_repos: List[str]
    
class TokenSecurityManager:
    """Verwaltung und Validierung von API-Tokens"""
    
    def __init__(self, config_path: str = "config/security/token-scopes.yaml"):
        self.config = self._load_config(config_path)
        self._active_tokens: dict = {}
    
    def _load_config(self, path: str) -> dict:
        import yaml
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_token_for_customer(self, customer: str) -> Optional[str]:
        """Token für Kunden abrufen"""
        customer_config = self.config.get("token_management", {}).get("customer_isolation", {}).get("customers", {}).get(customer)
        
        if not customer_config:
            raise ValueError(f"Keine Token-Konfiguration für Kunde: {customer}")
        
        token_env = customer_config.get("token_env")
        token = os.environ.get(token_env)
        
        if not token:
            raise ValueError(f"Token nicht gefunden in Umgebungsvariable: {token_env}")
        
        return token
    
    def validate_repo_access(self, customer: str, repo_slug: str) -> bool:
        """Prüft ob Kunde Zugriff auf Repository hat"""
        customer_config = self.config.get("token_management", {}).get("customer_isolation", {}).get("customers", {}).get(customer)
        
        if not customer_config:
            return False
        
        allowed_repos = customer_config.get("allowed_repos", [])
        
        for pattern in allowed_repos:
            if fnmatch.fnmatch(repo_slug, pattern):
                return True
        
        return False
    
    def get_workspace(self, customer: str) -> str:
        return "agentur-name"
    
    def sanitize_branch_name(self, branch_name: str) -> str:
        """Branch-Name validieren und säubern"""
        sanitized = re.sub(r'[^a-zA-Z0-9\-_/.]', '', branch_name)
        max_length = 100
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized
    
    def validate_commit_message(self, message: str) -> tuple[bool, str]:
        """Commit-Nachricht auf Sicherheit prüfen"""
        forbidden_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'PRIVATE KEY',
            r'-----BEGIN',
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False, f"Verbotenes Muster in Commit-Nachricht gefunden: {pattern}"
        
        return True, "OK"
```

### 3.5.2 Branch-Protection

```yaml
# config/security/branch-protection.yaml
branch_protection:
  enabled: true
  
  # Globale Regeln für alle Repositories
  global_rules:
    # Protected Branches
    protected_patterns:
      - "main"
      - "master"
      - "release/*"
      - "hotfix/*"
    
    # Agenten dürfen NICHT direkt auf protected branches pushen
    agent_push_allowed: false
    
    # Erforderliche PR-Reviews
    required_reviews:
      count: 1
      dismiss_stale: true
      require_code_owner: true
    
    # Status-Checks
    required_status_checks:
      - "Build"
      - "PHPUnit"
      - "Code Style"
    
    # Branch-Löschung verhindern
    allow_deletions: false
    
    # Force-Push verhindern
    allow_force_pushes: false
  
  # Kundenspezifische Regeln
  customer_rules:
    alp-shopware:
      protected_patterns:
        - "main"
        - "develop"
        - "release/*"
      required_reviews:
        count: 2
        
    kraft-shopware:
      protected_patterns:
        - "master"
        - "production"
```

```python
# agents/security/branch_protection.py
from dataclasses import dataclass
from typing import List, Optional
import fnmatch

@dataclass
class ProtectionRule:
    pattern: str
    required_reviews: int
    required_checks: List[str]
    allow_force_push: bool = False
    allow_deletion: bool = False

class BranchProtectionEnforcer:
    """Enforcement von Branch-Protection Regeln"""
    
    def __init__(self, config_path: str = "config/security/branch-protection.yaml"):
        self.config = self._load_config(config_path)
        self.rules = self._build_rules()
    
    def _load_config(self, path: str) -> dict:
        import yaml
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def _build_rules(self) -> List[ProtectionRule]:
        rules = []
        global_config = self.config.get("branch_protection", {}).get("global_rules", {})
        
        for pattern in global_config.get("protected_patterns", []):
            rules.append(ProtectionRule(
                pattern=pattern,
                required_reviews=global_config.get("required_reviews", {}).get("count", 1),
                required_checks=global_config.get("required_status_checks", []),
                allow_force_push=global_config.get("allow_force_pushes", False),
                allow_deletion=global_config.get("allow_deletions", False)
            ))
        
        return rules
    
    def is_protected(self, branch_name: str) -> bool:
        for rule in self.rules:
            if fnmatch.fnmatch(branch_name, rule.pattern):
                return True
        return False
    
    def can_agent_push(self, branch_name: str) -> bool:
        if self.is_protected(branch_name):
            return self.config.get("branch_protection", {}).get("global_rules", {}).get("agent_push_allowed", False)
        return True
    
    def get_required_reviews(self, branch_name: str) -> int:
        for rule in self.rules:
            if fnmatch.fnmatch(branch_name, rule.pattern):
                return rule.required_reviews
        return 0
    
    def validate_branch_creation(self, new_branch: str, source_branch: str) -> tuple[bool, str]:
        forbidden_prefixes = ["main", "master", "release", "hotfix"]
        parts = new_branch.split("/")
        if parts[0] in forbidden_prefixes and len(parts) == 1:
            return False, f"Branch '{new_branch}' verwendet reservierten Namen"
        return True, "OK"
```

### 3.5.3 Review-Pflicht und Qualitätsgates

```yaml
# config/security/quality-gates.yaml
quality_gates:
  enabled: true
  
  # Automatische Checks vor PR-Erstellung
  pre_pr_checks:
    code_style:
      enabled: true
      tool: "ecs"
      auto_fix: true
      fail_on_error: true
    
    static_analysis:
      enabled: true
      tool: "phpstan"
      level: 8
      fail_on_error: true
    
    unit_tests:
      enabled: true
      coverage_threshold: 80
      fail_on_error: true
    
    security_scan:
      enabled: true
      tools:
        - "composer audit"
        - "security-checker"
      fail_on_high_severity: true
  
  # Review-Zuweisung
  review_assignment:
    strategy: "round_robin"
    reviewers_per_pr: 1
    code_owners_enabled: true
    
    # Reviewer-Pools pro Kunde
    reviewer_pools:
      alp-shopware:
        - "senior-dev-1"
        - "senior-dev-2"
        - "tech-lead-alp"
      
      kraft-shopware:
        - "senior-dev-3"
        - "tech-lead-kraft"
      
      lupus:
        - "senior-dev-1"
        - "senior-dev-4"
  
  # Auto-Merge Regeln
  auto_merge:
    enabled: false
```

```python
# agents/security/quality_gate_runner.py
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import json

@dataclass
class CheckResult:
    name: str
    passed: bool
    output: str
    severity: str  # "error", "warning", "info"

class QualityGateRunner:
    """Führt Qualitäts-Checks vor PR-Erstellung aus"""
    
    def __init__(self, project_root: Path, config_path: str = "config/security/quality-gates.yaml"):
        self.project_root = project_root
        self.config = self._load_config(config_path)
    
    def _load_config(self, path: str) -> dict:
        import yaml
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def run_all_checks(self) -> List[CheckResult]:
        results = []
        checks_config = self.config.get("quality_gates", {}).get("pre_pr_checks", {})
        
        if checks_config.get("code_style", {}).get("enabled"):
            results.append(self._check_code_style())
        
        if checks_config.get("static_analysis", {}).get("enabled"):
            results.append(self._check_static_analysis())
        
        if checks_config.get("unit_tests", {}).get("enabled"):
            results.append(self._check_unit_tests())
        
        if checks_config.get("security_scan", {}).get("enabled"):
            results.append(self._check_security())
        
        return results
    
    def _check_code_style(self) -> CheckResult:
        try:
            result = subprocess.run(
                ["vendor/bin/ecs", "check", "--output-format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            passed = result.returncode == 0
            return CheckResult(
                name="Code Style (ECS)",
                passed=passed,
                output=result.stdout if passed else result.stderr,
                severity="error" if not passed else "info"
            )
        except Exception as e:
            return CheckResult(
                name="Code Style (ECS)",
                passed=False,
                output=str(e),
                severity="error"
            )
    
    def _check_static_analysis(self) -> CheckResult:
        try:
            result = subprocess.run(
                ["vendor/bin/phpstan", "analyse", "--error-format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180
            )
            passed = result.returncode == 0
            return CheckResult(
                name="Static Analysis (PHPStan)",
                passed=passed,
                output=result.stdout if passed else result.stderr,
                severity="error" if not passed else "info"
            )
        except Exception as e:
            return CheckResult(
                name="Static Analysis (PHPStan)",
                passed=False,
                output=str(e),
                severity="error"
            )
    
    def _check_unit_tests(self) -> CheckResult:
        try:
            result = subprocess.run(
                ["vendor/bin/phpunit", "--testdox"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            passed = result.returncode == 0
            return CheckResult(
                name="Unit Tests (PHPUnit)",
                passed=passed,
                output=result.stdout,
                severity="error" if not passed else "info"
            )
        except Exception as e:
            return CheckResult(
                name="Unit Tests (PHPUnit)",
                passed=False,
                output=str(e),
                severity="error"
            )
    
    def _check_security(self) -> CheckResult:
        try:
            result = subprocess.run(
                ["composer", "audit", "--format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            passed = result.returncode == 0
            return CheckResult(
                name="Security Audit (Composer)",
                passed=passed,
                output=result.stdout,
                severity="error" if not passed else "info"
            )
        except Exception as e:
            return CheckResult(
                name="Security Audit (Composer)",
                passed=False,
                output=str(e),
                severity="error"
            )
    
    def all_checks_passed(self, results: List[CheckResult]) -> bool:
        return all(r.passed for r in results)
```


## 3.6 Integration mit Shopware/DDEV-Workflow

### 3.6.1 DDEV-Integration

```yaml
# config/ddev-integration.yaml
ddev_integration:
  enabled: true
  
  # Standard-DDEV-Konfiguration
  default_config:
    type: "shopware6"
    php_version: "8.2"
    webserver_type: "nginx-fpm"
    database:
      type: "mysql"
      version: "8.0"
    
    services:
      elasticsearch:
        enabled: true
        version: "8"
      redis:
        enabled: true
        version: "7"
  
  # Projektspezifische Overrides
  project_overrides:
    alp-shopware:
      php_version: "8.2"
      shopware_version: "6.5.8"
      
    kraft-shopware:
      php_version: "8.3"
      shopware_version: "6.7.0"
      
    lupus:
      php_version: "8.1"
      shopware_version: "6.5.4"
  
  # Agent-Workflow mit DDEV
  agent_workflow:
    # Vor Code-Änderungen
    pre_changes:
      - "ddev start"
      - "ddev composer install"
      - "ddev exec bin/console cache:clear"
    
    # Nach Code-Änderungen
    post_changes:
      - "ddev exec bin/console plugin:refresh"
      - "ddev exec bin/console cache:clear"
      - "ddev exec bin/console theme:compile"
    
    # Vor Commit
    pre_commit:
      - "ddev exec vendor/bin/ecs check"
      - "ddev exec vendor/bin/phpstan analyse"
      - "ddev exec vendor/bin/phpunit"
```

### 3.6.2 Bitbucket Pipelines Integration

```yaml
# bitbucket-pipelines.yml Template für Agenten-Commits
image: shopware/development:latest

definitions:
  steps:
    - step: &validate-agent-commit
        name: Validate Agent Commit
        script:
          - composer validate --strict
          - composer audit
          - vendor/bin/ecs check
          - vendor/bin/phpstan analyse
        condition:
          changesets:
            includePaths:
              - "custom/**"
              - "src/**"
              - "composer.json"
    
    - step: &test-agent-changes
        name: Test Agent Changes
        script:
          - vendor/bin/phpunit --coverage-text
          - php bin/console plugin:refresh
          - php bin/console theme:compile
        services:
          - mysql
          - elasticsearch
    
    - step: &deploy-staging
        name: Deploy to Staging
        deployment: staging
        script:
          - ./deploy.sh staging
        condition:
          branches:
            - develop
            - feature/*

pipelines:
  # Für Agent-Branches
  feature/*:
    - step: *validate-agent-commit
    - step: *test-agent-changes
    - step: *deploy-staging
  
  bugfix/*:
    - step: *validate-agent-commit
    - step: *test-agent-changes
    - step: *deploy-staging
  
  # Für PRs
  pull-requests:
    '**':
      - step: *validate-agent-commit
      - step: *test-agent-changes
  
  # Main-Branch Deployment
  branches:
    main:
      - step: *validate-agent-commit
      - step: *test-agent-changes
      - step:
          name: Deploy to Production
          deployment: production
          trigger: manual
          script:
            - ./deploy.sh production
```

## 3.7 Zusammenfassung der Integration

| Komponente | Verantwortlichkeit | Schnittstelle |
|------------|-------------------|---------------|
| Auth Manager | Token-Verwaltung, Rotation | Bitbucket REST API |
| Branch Manager | Branch-Erstellung, -Löschung | Bitbucket Git API |
| Commit Manager | Commits, Datei-Updates | Bitbucket Src API |
| PR Manager | PR-Erstellung, Review-Assignment | Bitbucket PR API |
| Security Manager | Token-Validierung, Zugriffskontrolle | Konfiguration |
| Quality Gates | Pre-PR Checks | ECS, PHPStan, PHPUnit |
| DDEV Integration | Lokale Testing-Umgebung | DDEV CLI |

### Sicherheits-Checkliste

- [ ] App Passwords mit minimalen Scopes
- [ ] Token-Rotation alle 90 Tage
- [ ] Customer-Repository-Isolation
- [ ] Keine Secrets in Commits/Branches
- [ ] Branch-Protection für main/master
- [ ] Mindestens 1 Review pro PR
- [ ] Automatische Security-Scans
- [ ] Kein Direct-Push auf geschützte Branches

### API-Endpunkte Übersicht

| Endpoint | Methode | Zweck |
|----------|---------|-------|
| `/repositories/{workspace}/{repo_slug}` | GET | Repository-Details |
| `/repositories/{workspace}/{repo_slug}/refs/branches` | GET/POST | Branches listen/erstellen |
| `/repositories/{workspace}/{repo_slug}/src` | POST | Commits erstellen |
| `/repositories/{workspace}/{repo_slug}/pullrequests` | GET/POST | PRs listen/erstellen |
| `/repositories/{workspace}/{repo_slug}/src/{commit}/{path}` | GET | Dateiinhalt lesen |

### Repository-Mapping Zusammenfassung

| Kunde | Primäres Repo | Shopware | PHP | Default Branch |
|-------|--------------|----------|-----|----------------|
| alp-shopware | alp-shopware | 6.5.8 | 8.2 | main |
| kraft-shopware | kraft-shopware | 6.7.0 | 8.3 | master |
| lupus | lupus | 6.5.4 | 8.1 | main |

### Umgebungsvariablen

```bash
# Erforderliche Umgebungsvariablen
export BITBUCKET_WORKSPACE="agentur-name"
export BITBUCKET_APP_PASSWORD_ALP="xxx"
export BITBUCKET_APP_PASSWORD_KRAFT="xxx"
export BITBUCKET_APP_PASSWORD_LUPUS="xxx"
```
