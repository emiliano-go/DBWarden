# Configuration Concepts

Understand how DBWarden configuration works under the hood.

## What is Configuration?

Configuration tells DBWarden:
- **Where** your databases are (connection URLs)
- **What** kind of databases they are (PostgreSQL, SQLite, etc.)
- **Where** your SQLAlchemy models live (for migration generation)
- **Where** to store migrations (directories)

## Why Python Configuration?

### Type Safety

Your IDE can help you:

```python
primary = database_config(
    database_name="primary",  #  IDE suggests parameter names
    default=True,             #  IDE knows this is boolean
    database_type="sqlite",   #  IDE can validate enum values
    database_url_sync="...",
)
```

### Dynamic Configuration

You can use Python logic:

```python
import os

# Different config per environment
environment = os.getenv("ENV", "dev")

if environment == "production":
    database_url = "postgresql://prod-host/myapp"
else:
    database_url = "sqlite:///./dev.db"

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql" if environment == "production" else "sqlite",
    database_url_sync=database_url,
)
```

### Multiple Databases

Easy to configure multiple databases:

```python
DATABASES = {
    "primary": "postgresql://localhost/main",
    "analytics": "postgresql://localhost/analytics",
    "logging": "postgresql://localhost/logs",
}

for name, url in DATABASES.items():
    db = database_config(
        database_name=name,
        default=(name == "primary"),
        database_type="postgresql",
        database_url_sync=url,
        model_paths=[f"app.models.{name}"],
    )
```

## Configuration Loading

### Discovery Order

DBWarden searches for configuration in this order:

```
1. dbwarden.py in current directory
      not found
2. dbwarden.py in parent directories
      not found
3. Full scan for files with database_config()
      not found
4. DBWARDEN_CONFIG_MODULE environment variable
      not found
Error: No configuration found
```

### When Configuration Loads

Configuration loads when you run **any** DBWarden command:

```bash
dbwarden migrate    #  Config loads here
dbwarden status     #  Config loads here
dbwarden history    #  Config loads here
```

**Load process:**
1. Python imports your config module
2. `database_config()` calls execute
3. Databases register in internal registry
4. Validation runs
5. Command executes with loaded config

### Validation Rules

DBWarden validates configuration at load time:

| Rule | Why It Matters |
|------|----------------|
| Exactly one `default=True` | CLI needs to know which DB to use when `--database` is omitted |
| Unique `database_name` | Commands target databases by name |
| Unique `database_url` | Prevents accidental duplicate configurations |
| Unique physical targets | Prevents two configs pointing to same DB with different credentials |
| Required `model_paths` in multi-DB | Keeps model discovery boundaries clear |
| No overlapping `model_paths` | Prevents ambiguous model ownership (unless `overlap_models=True`) |

### Validation Timing

```python
# dbwarden.py
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
)

primary = database_config(
    database_name="primary",  #  Duplicate!
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/other",
)
```

When you run `dbwarden migrate`:

```
Error: Duplicate database_name 'primary'
```

Validation happens **before** any commands execute.

### Config Loading Security (Sandbox)

When DBWarden imports your config file, it applies **path-level security**:

- **Path validation**  Config files must be within the project tree. Paths with `..` traversal sequences are rejected.
- **Model path validation**  Model discovery paths are also checked for path traversal attacks.

This ensures an attacker cannot trick DBWarden into loading config files from outside your project.

For debugging, set the `DBWARDEN_DISABLE_SANDBOX` environment variable to skip all path validation:

```bash
DBWARDEN_DISABLE_SANDBOX=1 dbwarden status  # Skip sandbox (debug only)
```

Keep the sandbox enabled in production. Disabling it (`DBWARDEN_DISABLE_SANDBOX=1`) removes path traversal protection.

## The `default` Database

### Why `default=True` Exists

Consider these commands:

```bash
# Explicit database
dbwarden migrate --database primary

# Implicit database (uses default)
dbwarden migrate
```

Without `default=True`, DBWarden wouldn't know which database to use for the second command.

### Only One Default

```python
#  Good
analytics = database_config(
analytics = database_config(database_name="analytics", default=False, ...)  # or omit default

#  Bad - two defaults
analytics = database_config(
analytics = database_config(database_name="analytics", default=True, ...)  # Error!
```

### Default Affects CLI Behavior

```bash
# These are equivalent when primary is default:
dbwarden migrate
dbwarden migrate --database primary

# These are NOT equivalent:
dbwarden migrate
dbwarden migrate --database analytics  # Targets analytics, not primary
```

## Model Discovery

### What Are `model_paths`?

`model_paths` tells DBWarden where your SQLAlchemy models live:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
    model_paths=["app.models"],  #  Look here for models
)
```

### How Discovery Works

```
1. Import each module in model_paths
     
2. Find all classes inheriting from DeclarativeBase
     
3. Extract table metadata (__tablename__, columns, etc.)
     
4. Build internal representation for migration generation
```

### When Is It Required?

**Single database:** Optional (DBWarden scans entire codebase)

```python
# This works
primary = database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
    # No model_paths needed
)
```

**Multiple databases:** Required for each database

```python
# This is required
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/main",
    model_paths=["app.models.primary"],  #  Required
)

analytics = database_config(
    database_name="analytics",
    database_type="postgresql",
    database_url_sync="postgresql://localhost/analytics",
    model_paths=["app.models.analytics"],  #  Required
)
```

**Why?** To prevent ambiguity about which models belong to which database.

## Dev Mode

### What Is Dev Mode?

Dev mode lets you use a different database for local development:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",              # Production
    database_url_sync="postgresql://prod/myapp",
    dev_database_type="sqlite",              # Development
    dev_database_url="sqlite:///./dev.db",
)
```

Run commands with `--dev`:

```bash
dbwarden --dev migrate  # Uses SQLite
dbwarden migrate        # Uses PostgreSQL
```

### How It Works

```
Command: dbwarden --dev migrate
    
Check for --dev flag
    
Swap database_type  dev_database_type
Swap database_url  dev_database_url
    
Connect to dev database
    
Execute command
```

### Why Use It?

**Speed:**
- SQLite is faster than PostgreSQL for local iteration
- No network latency
- No server setup

**Safety:**
- Can't accidentally affect production
- Each developer has their own isolated database
- Easy to reset (just delete the file)

**Simplicity:**
- No Docker containers needed
- No database server installation
- Works on all platforms

## Multi-Database Configuration

### Why Multiple Databases?

Common scenarios:
- **Separation of concerns** - Transactions vs analytics
- **Performance** - Offload reporting to separate database
- **Compliance** - Audit logs in separate database
- **Legacy systems** - New and old databases coexist

### How It Works

Each `database_config()` call registers an independent database:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/main",
    model_paths=["app.models.primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="postgresql",
    database_url_sync="postgresql://localhost/analytics",
    model_paths=["app.models.analytics"],
)
```

They're completely independent:
- Separate migration histories
- Separate migration directories
- Separate model sets
- Can use different database types

### Model Path Boundaries

```python
app/
  models/
    primary/
      user.py         #  Goes to primary database
      order.py
    analytics/
      event.py        #  Goes to analytics database
      metric.py
```

Configuration:

```python
primary = database_config(
    database_name="primary",
    model_paths=["app.models.primary"],  #  Only primary models
    ...
)

analytics = database_config(
    database_name="analytics",
    model_paths=["app.models.analytics"],  #  Only analytics models
    ...
)
```

## Secure Values

### What Is `secure_values`?

Prevents credentials from appearing in terminal output:

```python
import os

DATABASE_URL = os.getenv("DATABASE_URL")

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=DATABASE_URL,
    secure_values=True,  #  Hide credentials
)
```

### Without `secure_values`:

```bash
$ dbwarden settings show
Database: primary
  URL: postgresql://user:SECRET_PASSWORD@prod-host/myapp
```

### With `secure_values`:

```bash
$ dbwarden settings show --all
Database: primary
  URL: DATABASE_URL (expression)
```

Shows the variable name instead of resolved value.

## Configuration vs Runtime

### Configuration Time

When config loads:
- `database_config()` calls execute
- Validation runs
- Internal registry populates
- **No database connections made**

### Runtime

When commands run:
- DBWarden reads from registry
- **Connects to database**
- Executes command logic

**Key point:** Configuration errors are caught early, before any database operations.

## Recap

You learned:

 Why Python configuration is powerful  
 How configuration discovery works  
 When validation runs  
 Why `default=True` is required  
 How model discovery works  
 What dev mode does  
 How multi-database configuration works  
 When to use `secure_values`  

## What's Next?

- **[Connection URLs](connection-urls.md)** - URL format reference
- **[Model Discovery](model-discovery.md)** - Deep dive into model paths
- **[Dev Mode](dev-mode.md)** - Local development workflows
- **[Multi-Database](multi-database.md)** - Multi-database patterns
