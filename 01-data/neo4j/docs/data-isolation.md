# Neo4j Data Isolation Patterns

This document describes strategies for ensuring users can only access their own data in Neo4j Community Edition.

## Overview

Neo4j Community Edition does not have built-in multi-tenancy or database-level isolation. Data isolation must be implemented at the **application layer** by filtering queries based on user identity.

## User Identity Source

User identity comes from Cloudflare Access headers:

- `CF-Access-Authenticated-User-Email`: User's email address
- `CF-Access-JWT-Assertion`: JWT token with user claims

Extract user email from headers in your application code:

```python
user_email = request.headers.get('CF-Access-Authenticated-User-Email')
```

## Isolation Patterns

### Pattern 1: Property-Based Filtering (Recommended)

**Approach**: Add `userId` property to all user-specific nodes.

**Implementation**:

```cypher
// Create user data with userId property
CREATE (n:UserData {
  userId: $userEmail,
  data: "user-specific content"
})

// Query user's data (ALWAYS filter by userId)
MATCH (n:UserData {userId: $userEmail})
RETURN n

// Update user's data
MATCH (n:UserData {userId: $userEmail})
SET n.data = $newData
RETURN n

// Delete user's data
MATCH (n:UserData {userId: $userEmail})
DELETE n
```

**Pros**:
- Simple to implement
- Easy to understand
- Works with any query pattern
- Index-friendly

**Cons**:
- Requires adding `userId` to every node
- Easy to forget in queries (security risk)

**Best For**: Most use cases, especially when data is clearly user-specific

### Pattern 2: Relationship-Based Isolation

**Approach**: Link all user data to a user node via relationships.

**Implementation**:

```cypher
// Create user node
MERGE (u:User {email: $userEmail})

// Create data linked to user
MATCH (u:User {email: $userEmail})
CREATE (u)-[:OWNS]->(d:Data {value: "content"})

// Query user's data (traverse from user)
MATCH (u:User {email: $userEmail})-[:OWNS]->(d)
RETURN d

// Query with relationships
MATCH (u:User {email: $userEmail})-[:OWNS]->(d:Data)-[:RELATES_TO]->(other:Data)
RETURN d, other

// Delete user's data
MATCH (u:User {email: $userEmail})-[:OWNS]->(d)
DELETE d
```

**Pros**:
- Natural graph structure
- Supports complex relationships
- Clear ownership model
- Can query user's entire subgraph

**Cons**:
- More complex queries
- Requires user node creation
- Relationship traversal overhead

**Best For**: Complex graph structures with relationships between user data

### Pattern 3: Label-Based Isolation

**Approach**: Use user-specific labels for nodes.

**Implementation**:

```cypher
// Create data with user-specific label
CREATE (n:UserData_user_example_com {
  data: "content"
})

// Query user's data (dynamic label)
MATCH (n)
WHERE labels(n)[0] = 'UserData_' + replace($userEmail, '@', '_at_')
RETURN n

// Or using APOC (if available)
MATCH (n)
WHERE any(label IN labels(n) WHERE label = 'UserData_' + replace($userEmail, '@', '_at_'))
RETURN n
```

**Pros**:
- Clear separation at label level
- Can use label-based indexes
- Easy to identify user data

**Cons**:
- Dynamic label construction
- Less flexible than properties
- Harder to query across users

**Best For**: When you need strict label-based separation

## Implementation Examples

### Python (Neo4j Driver)

```python
from neo4j import GraphDatabase

class Neo4jUserData:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def get_user_data(self, user_email):
        """Get all data for a specific user."""
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
        """Create data for a specific user."""
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
    
    def delete_user_data(self, user_email, data_id):
        """Delete specific data for a user."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (n:UserData {userId: $userEmail, id: $dataId})
                DELETE n
                """,
                userEmail=user_email,
                dataId=data_id
            )
```

### JavaScript (Neo4j Driver)

```javascript
const neo4j = require('neo4j-driver');

class Neo4jUserData {
    constructor(uri, user, password) {
        this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password));
    }
    
    async close() {
        await this.driver.close();
    }
    
    async getUserData(userEmail) {
        const session = this.driver.session();
        try {
            const result = await session.run(
                `MATCH (n:UserData {userId: $userEmail})
                 RETURN n`,
                { userEmail }
            );
            return result.records.map(record => record.get('n'));
        } finally {
            await session.close();
        }
    }
    
    async createUserData(userEmail, data) {
        const session = this.driver.session();
        try {
            const result = await session.run(
                `CREATE (n:UserData {
                    userId: $userEmail,
                    data: $data,
                    createdAt: datetime()
                })
                RETURN n`,
                { userEmail, data }
            );
            return result.records[0].get('n');
        } finally {
            await session.close();
        }
    }
}
```

## Security Best Practices

### 1. Always Filter by User

**❌ Bad**: Query without user filter
```cypher
MATCH (n:UserData)
RETURN n
```

**✅ Good**: Always include user filter
```cypher
MATCH (n:UserData {userId: $userEmail})
RETURN n
```

### 2. Validate User Identity

Always extract and validate user email from Cloudflare Access headers:

```python
def get_user_email(request):
    """Extract and validate user email from Cloudflare Access headers."""
    user_email = request.headers.get('CF-Access-Authenticated-User-Email')
    if not user_email:
        raise ValueError("User not authenticated")
    return user_email
```

### 3. Use Parameterized Queries

**❌ Bad**: String concatenation (SQL injection risk)
```python
query = f"MATCH (n:UserData {{userId: '{user_email}'}})"
```

**✅ Good**: Parameterized queries
```python
query = "MATCH (n:UserData {userId: $userEmail})"
params = {"userEmail": user_email}
```

### 4. Create Indexes

Improve query performance with indexes:

```cypher
CREATE INDEX user_data_user_id IF NOT EXISTS
FOR (n:UserData)
ON (n.userId);
```

### 5. Audit Queries

Log all queries for security auditing:

```python
def execute_user_query(user_email, query, params):
    logger.info(f"User {user_email} executing query: {query}")
    # Verify query includes user filter
    assert 'userId' in params or user_email in str(query)
    # Execute query
    result = session.run(query, params)
    return result
```

## Migration Strategy

If you have existing data without user isolation:

1. **Add userId Property**:
   ```cypher
   MATCH (n:UserData)
   WHERE n.userId IS NULL
   SET n.userId = 'unknown@example.com'  // Or migrate based on other criteria
   ```

2. **Create Index**:
   ```cypher
   CREATE INDEX user_data_user_id IF NOT EXISTS
   FOR (n:UserData)
   ON (n.userId);
   ```

3. **Update Application Code**: Ensure all queries filter by userId

4. **Test**: Verify users can only see their own data

## Testing Data Isolation

### Test Script

```python
def test_data_isolation():
    """Test that users can only see their own data."""
    # Create test data for user1
    create_user_data("user1@example.com", "data1")
    create_user_data("user1@example.com", "data2")
    
    # Create test data for user2
    create_user_data("user2@example.com", "data3")
    
    # Query as user1
    user1_data = get_user_data("user1@example.com")
    assert len(user1_data) == 2
    assert all(d["userId"] == "user1@example.com" for d in user1_data)
    
    # Query as user2
    user2_data = get_user_data("user2@example.com")
    assert len(user2_data) == 1
    assert all(d["userId"] == "user2@example.com" for d in user2_data)
```

## Related Documentation

- [Authentication Flow](authentication-flow.md) - How users authenticate
- [User Management](user-management.md) - Managing Neo4j user accounts
- [Bolt API Authentication](bolt-api-authentication.md) - Programmatic access

