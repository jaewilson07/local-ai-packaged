# Neo4j User Management Strategies

This document describes strategies for managing Neo4j user accounts when using Cloudflare Access for authentication.

## Overview

Since Neo4j Community Edition requires native authentication, you need to decide how to manage Neo4j user accounts. There are two main approaches:

1. **Shared Account**: All users share a single Neo4j account
2. **Per-User Accounts**: Each user has their own Neo4j account

## Strategy Comparison

| Aspect | Shared Account | Per-User Accounts |
|--------|---------------|-------------------|
| **Complexity** | Simple | Complex |
| **User Management** | None required | Requires provisioning |
| **Security** | Application-layer | Database-layer |
| **Data Isolation** | Application filtering | Can use Neo4j roles |
| **Best For** | Most use cases | Enterprise scenarios |

## Strategy 1: Shared Account (Recommended)

### Overview

All users authenticate with Cloudflare Access, but use the same Neo4j account for database access. Data isolation is handled at the application layer.

### Configuration

**Neo4j Credentials**:
```bash
NEO4J_AUTH=neo4j/shared-secure-password
```

**Usage**:
- All users connect with: `neo4j` / `shared-secure-password`
- Application extracts user identity from Cloudflare Access headers
- All queries filtered by `userId` property

### Pros

- ✅ Simple to set up and maintain
- ✅ No user provisioning required
- ✅ Works well with application-layer data isolation
- ✅ Easy to rotate credentials

### Cons

- ❌ All users share same database credentials
- ❌ Relies entirely on application-layer security
- ❌ Cannot use Neo4j role-based access control per user

### Implementation

```python
from neo4j import GraphDatabase

# Single shared connection
driver = GraphDatabase.driver(
    "bolt://neo4j:7687",
    auth=("neo4j", "shared-secure-password")
)

def get_user_data(user_email):
    """Get data for specific user."""
    with driver.session() as session:
        result = session.run(
            "MATCH (n:UserData {userId: $userEmail}) RETURN n",
            userEmail=user_email
        )
        return [record["n"] for record in result]
```

### Security Considerations

1. **Strong Password**: Use XKCD passphrase or strong random password
2. **Store Securely**: Use Infisical for production credentials
3. **Application Filtering**: Always filter queries by user identity
4. **Audit Logging**: Log all database operations with user identity

## Strategy 2: Per-User Accounts

### Overview

Each Cloudflare Access user gets their own Neo4j account. User provisioning happens automatically or manually.

### Configuration

**Neo4j Admin Account**:
```bash
NEO4J_AUTH=neo4j/admin-password
```

**User Accounts**: Created programmatically or manually

### Pros

- ✅ Database-level user separation
- ✅ Can use Neo4j roles per user
- ✅ Better audit trail per user
- ✅ More granular access control

### Cons

- ❌ Complex user provisioning
- ❌ Requires user management logic
- ❌ More credentials to manage
- ❌ User account cleanup needed

### Implementation

#### User Provisioning

```python
from neo4j import GraphDatabase

# Admin connection
admin_driver = GraphDatabase.driver(
    "bolt://neo4j:7687",
    auth=("neo4j", "admin-password")
)

def provision_user(user_email):
    """Create Neo4j user account for Cloudflare Access user."""
    # Sanitize email for Neo4j username
    username = user_email.replace("@", "_at_").replace(".", "_")
    password = generate_secure_password()

    with admin_driver.session() as session:
        # Create user (requires admin privileges)
        session.run(
            "CREATE USER $username IF NOT EXISTS SET PASSWORD $password",
            username=username,
            password=password
        )

        # Grant permissions
        session.run(
            "GRANT ROLE reader TO $username",
            username=username
        )

    return username, password

def get_user_credentials(user_email):
    """Get Neo4j credentials for user."""
    username = user_email.replace("@", "_at_").replace(".", "_")
    # Retrieve password from secure storage (e.g., Infisical)
    password = get_password_from_storage(username)
    return username, password
```

#### User Authentication

```python
def connect_as_user(user_email):
    """Connect to Neo4j as specific user."""
    username, password = get_user_credentials(user_email)
    driver = GraphDatabase.driver(
        "bolt://neo4j:7687",
        auth=(username, password)
    )
    return driver
```

### User Mapping

Map Cloudflare Access email to Neo4j username:

```python
def email_to_neo4j_username(email):
    """Convert email to Neo4j-compatible username."""
    # Neo4j usernames: alphanumeric, underscore, hyphen
    username = email.replace("@", "_at_")
    username = username.replace(".", "_")
    username = username.replace("-", "_")
    return username.lower()

# Example
email_to_neo4j_username("user@example.com")  # "user_at_example_com"
```

### User Cleanup

```python
def deprovision_user(user_email):
    """Remove Neo4j user account."""
    username = email_to_neo4j_username(user_email)

    with admin_driver.session() as session:
        # Revoke permissions
        session.run("REVOKE ROLE reader FROM $username", username=username)

        # Delete user
        session.run("DROP USER $username IF EXISTS", username=username)
```

## Hybrid Approach

You can combine both strategies:

- **Shared Account**: For most users (application-layer isolation)
- **Per-User Accounts**: For admin users or special cases

## Best Practices

### Password Management

1. **Generate Strong Passwords**:
   ```bash
   # XKCD-style passphrase
   xkcdpass -n 4

   # Or random hex
   openssl rand -hex 32
   ```

2. **Store Securely**:
   - Use Infisical for production
   - Never commit to git
   - Rotate regularly

3. **Password Policy**:
   - Minimum 16 characters
   - Use passphrases for shared accounts
   - Use random passwords for per-user accounts

### User Provisioning

1. **On-Demand**: Create user when first accessed
2. **Bulk**: Provision all Cloudflare Access users at once
3. **Scheduled**: Sync with Cloudflare Access user list

### User Cleanup

1. **Automatic**: Remove users not accessed in X days
2. **Manual**: Remove when user leaves organization
3. **Sync**: Remove users no longer in Cloudflare Access

## Example: On-Demand User Provisioning

```python
from neo4j import GraphDatabase
import secrets
import string

class Neo4jUserManager:
    def __init__(self, admin_uri, admin_user, admin_password):
        self.admin_driver = GraphDatabase.driver(
            admin_uri,
            auth=(admin_user, admin_password)
        )
        self.user_cache = {}  # Cache user credentials

    def get_or_create_user(self, user_email):
        """Get existing user or create new one."""
        username = email_to_neo4j_username(user_email)

        # Check cache
        if username in self.user_cache:
            return self.user_cache[username]

        # Check if user exists
        with self.admin_driver.session() as session:
            result = session.run(
                "SHOW USERS",
            )
            existing_users = [record["user"] for record in result]

            if username not in existing_users:
                # Create new user
                password = self.generate_password()
                session.run(
                    f"CREATE USER {username} SET PASSWORD '{password}'",
                )
                session.run(
                    f"GRANT ROLE reader TO {username}",
                )
                self.user_cache[username] = password
            else:
                # User exists, retrieve password from storage
                password = self.get_password_from_storage(username)
                self.user_cache[username] = password

        return password

    def generate_password(self):
        """Generate secure random password."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(24))

    def get_password_from_storage(self, username):
        """Retrieve password from secure storage."""
        # Implement your storage retrieval logic
        # e.g., Infisical, HashiCorp Vault, etc.
        pass
```

## Recommendation

For most use cases, **use the Shared Account strategy**:

- Simpler to implement and maintain
- Works well with application-layer data isolation
- No user provisioning complexity
- Easier to secure and audit

Only use Per-User Accounts if you need:
- Database-level role-based access control
- Per-user audit trails at database level
- Compliance requirements for separate accounts

## Related Documentation

- [Authentication Flow](authentication-flow.md) - How users authenticate
- [Data Isolation](data-isolation.md) - User-specific data access
- [Bolt API Authentication](bolt-api-authentication.md) - Programmatic access

