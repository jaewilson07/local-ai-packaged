# Neo4j Bolt API Authentication Guide

This guide explains how to programmatically access Neo4j via the Bolt protocol with proper authentication and user identity handling.

## Overview

The Neo4j Bolt API (port 7687) is used for programmatic access to Neo4j. When using Cloudflare Access, you need to:

1. Authenticate with Neo4j using appropriate credentials
2. Extract user identity from Cloudflare Access headers (for web requests)
3. Filter all queries by user identity for data isolation

## Connection Methods

### Direct Connection (Internal)

For services running in the same Docker network:

```python
from neo4j import GraphDatabase

# Direct connection (no Cloudflare Access)
driver = GraphDatabase.driver(
    "bolt://neo4j:7687",
    auth=("neo4j", "your-password")
)
```

### External Connection (Through Cloudflare)

For external access, you'll need to:

1. Authenticate with Cloudflare Access (get service token)
2. Connect through the tunnel
3. Authenticate with Neo4j

**Note**: Bolt protocol (7687) is binary and doesn't work directly through Cloudflare Access. For external programmatic access, consider:

- Using Neo4j HTTP API (port 7474) through Cloudflare Access
- Using a service token for internal services
- Running services in the same Docker network

## Authentication Patterns

### Pattern 1: Shared Account with User Filtering (Recommended)

All services use the same Neo4j account, but filter queries by user identity.

```python
from neo4j import GraphDatabase

class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://neo4j:7687",
            auth=("neo4j", "shared-password")
        )

    def get_user_data(self, user_email):
        """Get data for specific user."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:UserData {userId: $userEmail})
                RETURN n
                """,
                userEmail=user_email
            )
            return [record["n"] for record in result]

    def create_user_data(self, user_email, data):
        """Create data for specific user."""
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (n:UserData {
                    userId: $userEmail,
                    data: $data,
                    createdAt: datetime()
                })
                RETURN n
                """,
                userEmail=user_email,
                data=data
            )
            return result.single()["n"]
```

### Pattern 2: Per-User Accounts

Each user has their own Neo4j account.

```python
from neo4j import GraphDatabase

class Neo4jUserService:
    def __init__(self, admin_user, admin_password):
        self.admin_driver = GraphDatabase.driver(
            "bolt://neo4j:7687",
            auth=(admin_user, admin_password)
        )
        self.user_credentials = {}  # Cache user credentials

    def get_user_driver(self, user_email):
        """Get driver for specific user."""
        username, password = self.get_user_credentials(user_email)
        return GraphDatabase.driver(
            "bolt://neo4j:7687",
            auth=(username, password)
        )

    def get_user_credentials(self, user_email):
        """Get or create Neo4j credentials for user."""
        # Implementation from user-management.md
        pass
```

## Extracting User Identity

### From Cloudflare Access Headers (Web Requests)

```python
from flask import Flask, request
from neo4j import GraphDatabase

app = Flask(__name__)

def get_user_email():
    """Extract user email from Cloudflare Access headers."""
    user_email = request.headers.get('CF-Access-Authenticated-User-Email')
    if not user_email:
        raise ValueError("User not authenticated via Cloudflare Access")
    return user_email

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get user's data."""
    user_email = get_user_email()

    driver = GraphDatabase.driver(
        "bolt://neo4j:7687",
        auth=("neo4j", "shared-password")
    )

    with driver.session() as session:
        result = session.run(
            "MATCH (n:UserData {userId: $userEmail}) RETURN n",
            userEmail=user_email
        )
        data = [record["n"] for record in result]

    driver.close()
    return {"data": data}
```

### From Service Token (Internal Services)

For internal services, use Cloudflare Access service tokens:

```python
import requests
from neo4j import GraphDatabase

def get_service_token():
    """Get Cloudflare Access service token."""
    # Retrieve from environment or Infisical
    return os.getenv("NEO4J_SERVICE_TOKEN")

def make_authenticated_request(url):
    """Make request with service token."""
    token = get_service_token()
    headers = {
        "CF-Access-Client-Id": token.split(".")[0],
        "CF-Access-Client-Secret": token.split(".")[1]
    }
    response = requests.get(url, headers=headers)
    return response
```

## Complete Example: REST API with Neo4j

```python
from flask import Flask, request, jsonify
from neo4j import GraphDatabase
import os

app = Flask(__name__)

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

def get_user_email():
    """Extract user email from Cloudflare Access headers."""
    user_email = request.headers.get('CF-Access-Authenticated-User-Email')
    if not user_email:
        raise ValueError("User not authenticated")
    return user_email

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get all nodes for authenticated user."""
    try:
        user_email = get_user_email()

        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:UserData {userId: $userEmail})
                RETURN n
                """,
                userEmail=user_email
            )
            nodes = [dict(record["n"]) for record in result]

        return jsonify({"nodes": nodes})
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

@app.route('/api/nodes', methods=['POST'])
def create_node():
    """Create node for authenticated user."""
    try:
        user_email = get_user_email()
        data = request.json

        with driver.session() as session:
            result = session.run(
                """
                CREATE (n:UserData {
                    userId: $userEmail,
                    data: $data,
                    createdAt: datetime()
                })
                RETURN n
                """,
                userEmail=user_email,
                data=data
            )
            node = dict(result.single()["n"])

        return jsonify({"node": node}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

@app.route('/api/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Delete node for authenticated user."""
    try:
        user_email = get_user_email()

        with driver.session() as session:
            session.run(
                """
                MATCH (n:UserData {userId: $userEmail, id: $nodeId})
                DELETE n
                """,
                userEmail=user_email,
                nodeId=node_id
            )

        return jsonify({"message": "Node deleted"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

## JavaScript Example

```javascript
const neo4j = require('neo4j-driver');
const express = require('express');

const app = express();

// Neo4j connection
const driver = neo4j.driver(
    process.env.NEO4J_URI || 'bolt://neo4j:7687',
    neo4j.auth.basic(
        process.env.NEO4J_USER || 'neo4j',
        process.env.NEO4J_PASSWORD || 'password'
    )
);

function getUserEmail(req) {
    const userEmail = req.headers['cf-access-authenticated-user-email'];
    if (!userEmail) {
        throw new Error('User not authenticated');
    }
    return userEmail;
}

app.get('/api/nodes', async (req, res) => {
    try {
        const userEmail = getUserEmail(req);
        const session = driver.session();

        const result = await session.run(
            `MATCH (n:UserData {userId: $userEmail})
             RETURN n`,
            { userEmail }
        );

        const nodes = result.records.map(record => record.get('n').properties);
        await session.close();

        res.json({ nodes });
    } catch (error) {
        res.status(401).json({ error: error.message });
    }
});

app.listen(8000, () => {
    console.log('Server running on port 8000');
});
```

## Security Best Practices

### 1. Always Validate User Identity

```python
def validate_user_identity(user_email):
    """Validate user email is authenticated."""
    if not user_email:
        raise ValueError("User not authenticated")
    # Additional validation if needed
    return user_email
```

### 2. Use Parameterized Queries

**❌ Bad**: String concatenation
```python
query = f"MATCH (n:UserData {{userId: '{user_email}'}})"
```

**✅ Good**: Parameterized queries
```python
query = "MATCH (n:UserData {userId: $userEmail})"
params = {"userEmail": user_email}
```

### 3. Filter All Queries by User

```python
def execute_user_query(user_email, query, params):
    """Execute query with user filter."""
    # Ensure userId is in params
    if "userEmail" not in params:
        params["userEmail"] = user_email

    # Verify query includes user filter
    assert "userId" in query.lower() or "userEmail" in query.lower()

    return session.run(query, params)
```

### 4. Connection Pooling

```python
from neo4j import GraphDatabase

# Create driver (manages connection pool)
driver = GraphDatabase.driver(
    "bolt://neo4j:7687",
    auth=("neo4j", "password"),
    max_connection_lifetime=3600,  # 1 hour
    max_connection_pool_size=50
)

# Reuse driver across requests
# Don't create new driver for each request
```

### 5. Error Handling

```python
from neo4j.exceptions import ServiceUnavailable, AuthError

try:
    with driver.session() as session:
        result = session.run(query, params)
except ServiceUnavailable:
    # Handle connection error
    logger.error("Neo4j service unavailable")
except AuthError:
    # Handle authentication error
    logger.error("Neo4j authentication failed")
except Exception as e:
    # Handle other errors
    logger.error(f"Neo4j error: {e}")
```

## Testing

### Unit Test Example

```python
import unittest
from neo4j import GraphDatabase

class TestNeo4jService(unittest.TestCase):
    def setUp(self):
        self.driver = GraphDatabase.driver(
            "bolt://neo4j:7687",
            auth=("neo4j", "password")
        )
        self.service = Neo4jService()

    def test_get_user_data(self):
        """Test getting user data."""
        user_email = "test@example.com"
        data = self.service.get_user_data(user_email)
        self.assertIsInstance(data, list)
        # Verify all data belongs to user
        for item in data:
            self.assertEqual(item["userId"], user_email)

    def tearDown(self):
        self.driver.close()
```

## Related Documentation

- [Authentication Flow](authentication-flow.md) - How users authenticate
- [Data Isolation](data-isolation.md) - User-specific data access patterns
- [User Management](user-management.md) - Managing Neo4j user accounts
