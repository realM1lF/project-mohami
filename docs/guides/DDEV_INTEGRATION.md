# DDEV Integration Guide

This document describes the DDEV integration for the Mohami KI-Mitarbeiter system.

## Quick Start

### 1. Prerequisites

Run the prerequisites setup script:

```bash
./scripts/setup_ddev_prerequisites.sh
```

This will check and install:
- Docker & Docker Compose
- DDEV
- mkcert (for HTTPS)
- Python dependencies

### 2. Configure Customers

Edit `config/customers.yaml` to define your customer environments:

```yaml
customers:
  your-customer:
    display_name: "Your Customer"
    ddev:
      project_name: "your-customer"
      php_version: "8.2"
      database:
        type: "mariadb"
        version: "10.11"
    shopware:
      version: "6.7.0.0"
    git:
      remote: "git@github.com:agency/your-customer.git"
      default_branch: "main"
    workspace:
      base_path: "~/ki-data/customer-workspaces/your-customer"
```

### 3. Setup Customer Workspace

```bash
# Using the setup script
python scripts/setup_customer_ddev.py --customer your-customer --setup --start

# Or using Make
make -f Makefile.ddev ddev-setup CUSTOMER=your-customer
```

### 4. Verify Installation

```bash
# Check status
python scripts/setup_customer_ddev.py --customer your-customer --status

# Run a test command
python scripts/setup_customer_ddev.py --customer your-customer --exec "php -v"
```

## Agent Integration

### Registering DDEV Tools

The DDEV tools are automatically available to agents. To register them:

```python
from src.tools.registry import ToolRegistry
from src.tools.ddev_tools import register_ddev_tools

# Create registry
registry = ToolRegistry()

# Register all DDEV tools
register_ddev_tools(registry)

# Now agents can use these tools
schemas = registry.get_schemas_for_llm(format="openai")
```

### Available Tools

#### 1. DDEVExecuteTool

Execute arbitrary commands in the customer's DDEV container:

```python
tool = DDEVExecuteTool()
result = await tool.run(
    customer_id="alp-shopware",
    command="ls -la /var/www/html",
    timeout=60
)
```

#### 2. DDEVShopwareCommandTool

Run Shopware CLI commands:

```python
tool = DDEVShopwareCommandTool()
result = await tool.run(
    customer_id="alp-shopware",
    command="cache:clear"
)
```

#### 3. DDEVTestTool

Run PHPUnit tests:

```python
tool = DDEVTestTool()
result = await tool.run(
    customer_id="alp-shopware",
    test_suite="unit",
    test_path="custom/plugins/MyPlugin/tests"
)
```

#### 4. DDEVComposerTool

Manage Composer dependencies:

```python
tool = DDEVComposerTool()
result = await tool.run(
    customer_id="alp-shopware",
    command="require shopware/storefront"
)
```

#### 5. DDEVGitSyncTool

Sync changes to repository:

```python
tool = DDEVGitSyncTool()
result = await tool.run(
    customer_id="alp-shopware",
    commit_message="Fix checkout bug",
    branch="feature/fix-checkout"
)
```

## API Reference

### WorkspaceManager

```python
from src.infrastructure.workspace_manager import get_workspace_manager

manager = get_workspace_manager()

# Setup workspace
manager.setup_workspace('customer-id', repo_url='https://...')

# Start/stop DDEV
manager.start_ddev('customer-id')
manager.stop_ddev('customer-id')

# Execute commands
success, stdout, stderr = manager.execute_in_ddev(
    'customer-id', 'bin/console cache:clear'
)

# Run Shopware commands
success, stdout, stderr = manager.run_shopware_command(
    'customer-id', 'cache:clear'
)

# Run tests
success, stdout, stderr = manager.run_tests(
    'customer-id', test_suite='unit'
)

# Sync to Git
success, message = manager.sync_to_repo(
    'customer-id',
    branch='main',
    commit_message='Changes'
)

# Get status
status = manager.get_status('customer-id')
```

### DDEVManager

```python
from src.infrastructure.ddev_manager import DDEVManager

ddev = DDEVManager()

# List projects
projects = ddev.list_all_projects()

# Start/stop/restart
ddev.start_project(Path('/path/to/project'))
ddev.stop_project(Path('/path/to/project'))
ddev.restart_project(Path('/path/to/project'))

# Snapshots
ddev.snapshot_create(Path('/path/to/project'), name='before-change')
ddev.snapshot_restore(Path('/path/to/project'), name='before-change')

# Database
ddev.import_db(Path('/path/to/project'), Path('/path/to/dump.sql.gz'))
ddev.export_db(Path('/path/to/project'), Path('/path/to/output.sql.gz'))

# Health check
healthy, details = ddev.health_check(Path('/path/to/project'))
```

## Docker Compose Profiles

Use profiles to start specific customer environments:

```bash
# Start only the orchestrator
docker-compose -f docker-compose.yml -f docker-compose.ddev.yml --profile ddev up -d

# Start specific customer
docker-compose -f docker-compose.yml -f docker-compose.ddev.yml --profile alp-shopware up -d

# Start multiple customers
docker-compose -f docker-compose.yml -f docker-compose.ddev.yml \
  --profile alp-shopware --profile kraft-shopware up -d

# Start all
docker-compose -f docker-compose.yml -f docker-compose.ddev.yml \
  --profile alp-shopware --profile kraft-shopware --profile lupus up -d
```

## Troubleshooting

### DDEV not found

```bash
# Install DDEV
curl -fsSL https://raw.githubusercontent.com/ddev/ddev/main/scripts/install_ddev.sh | bash

# Or via Homebrew (macOS)
brew install ddev/ddev/ddev
```

### Permission denied errors

```bash
# Fix ownership
ddev exec sudo chown -R www-data:www-data /var/www/html

# Fix permissions
ddev exec sudo chmod -R 755 /var/www/html
```

### Database connection issues

```bash
# Restart database container
ddev restart

# Check database logs
ddev logs -s db

# Reimport database
ddev import-db --file=dump.sql.gz
```

### Port conflicts

If ports are already in use, modify the port mappings in `docker-compose.ddev.yml`:

```yaml
ports:
  - "8081:80"  # Change 8081 to an available port
```

## Security Considerations

1. **Network Isolation**: Each customer has their own Docker network
2. **SSH Keys**: Use customer-specific SSH keys for Git access
3. **Environment Variables**: Store sensitive data in `.env` files
4. **Backup**: Regular database backups before major changes

## Performance Tips

1. **Use Mutagen**: Enabled by default for faster file sync
2. **Composer Cache**: Shared across all environments
3. **NPM Cache**: Shared across all environments
4. **Volume Mounts**: Use named volumes for vendor/, var/, files/

## Monitoring

Check DDEV status:

```bash
# All projects
ddev list

# Specific project
ddev status

# Logs
ddev logs

# Resource usage
ddev exec top
```

## Migration Guide

### From existing DDEV project

1. Copy existing project to workspace:
```bash
cp -r /path/to/existing/project ~/ki-data/customer-workspaces/alp-shopware/html
```

2. Generate DDEV config:
```bash
python scripts/setup_customer_ddev.py --customer alp-shopware --setup
```

3. Start DDEV:
```bash
ddev start
```

### From non-DDEV setup

1. Create workspace structure:
```bash
python scripts/setup_customer_ddev.py --customer alp-shopware --setup
```

2. Clone or copy source code:
```bash
cd ~/ki-data/customer-workspaces/alp-shopware/html
git clone <repo> .
```

3. Configure DDEV and start:
```bash
ddev config --project-type=shopware6
ddev start
```

## Support

For issues and questions:
1. Check DDEV documentation: https://ddev.readthedocs.io/
2. Review logs: `ddev logs`
3. Run diagnostics: `ddev debug`
