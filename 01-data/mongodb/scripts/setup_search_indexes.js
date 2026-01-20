/**
 * MongoDB Atlas Search Index Setup Script
 *
 * This script creates the required Atlas Search indexes for the RAG system.
 * It can be run manually or as part of the initialization process.
 *
 * Prerequisites:
 * - MongoDB Atlas Local image (mongodb/mongodb-atlas-local:latest)
 * - Replica set initialized (rs0)
 *
 * Usage:
 *   docker exec mongodb mongosh -u admin -p <password> --authenticationDatabase admin /scripts/setup_search_indexes.js
 *
 * Or directly:
 *   mongosh "mongodb://admin:<password>@localhost:27017/?authSource=admin" /path/to/setup_search_indexes.js
 */

// Configuration
const DATABASE_NAME = "rag_db";
const EMBEDDING_DIMENSIONS = 2560;  // Qwen3-Embedding-4B uses 2560 dimensions

// Index definitions
const INDEXES = [
    {
        collection: "chunks",
        name: "vector_index",
        type: "vectorSearch",
        definition: {
            fields: [{
                type: "vector",
                path: "embedding",
                numDimensions: EMBEDDING_DIMENSIONS,
                similarity: "cosine"
            }]
        }
    },
    {
        collection: "chunks",
        name: "text_index",
        type: "search",
        definition: {
            mappings: {
                dynamic: false,
                fields: {
                    content: {
                        type: "string",
                        analyzer: "lucene.standard"
                    }
                }
            }
        }
    },
    {
        collection: "documents",
        name: "documents_text_index",
        type: "search",
        definition: {
            mappings: {
                dynamic: false,
                fields: {
                    title: {
                        type: "string",
                        analyzer: "lucene.standard"
                    },
                    source: {
                        type: "string",
                        analyzer: "lucene.keyword"
                    }
                }
            }
        }
    }
];

// Switch to the target database
db = db.getSiblingDB(DATABASE_NAME);

print("=".repeat(60));
print("MongoDB Atlas Search Index Setup");
print("=".repeat(60));
print(`Database: ${DATABASE_NAME}`);
print(`Embedding dimensions: ${EMBEDDING_DIMENSIONS}`);
print("");

// Helper function to check if index exists
function indexExists(collection, indexName) {
    try {
        const indexes = db.getCollection(collection).getSearchIndexes();
        return indexes.some(idx => idx.name === indexName);
    } catch (e) {
        return false;
    }
}

// Helper function to wait for index to be ready
function waitForIndex(collection, indexName, maxWaitSeconds = 60) {
    const startTime = Date.now();
    while ((Date.now() - startTime) < maxWaitSeconds * 1000) {
        try {
            const indexes = db.getCollection(collection).getSearchIndexes();
            const idx = indexes.find(i => i.name === indexName);
            if (idx && idx.status === "READY") {
                return true;
            }
            sleep(1000);  // Wait 1 second
        } catch (e) {
            return false;
        }
    }
    return false;
}

// Create indexes
let created = 0;
let skipped = 0;
let errors = 0;

for (const indexDef of INDEXES) {
    const { collection, name, type, definition } = indexDef;

    print(`\n[${collection}] Checking ${name}...`);

    // Check if collection exists, create if not
    if (!db.getCollectionNames().includes(collection)) {
        print(`  Creating collection: ${collection}`);
        db.createCollection(collection);
    }

    // Check if index already exists
    if (indexExists(collection, name)) {
        print(`  ✓ Index already exists, skipping`);
        skipped++;
        continue;
    }

    // Create the index
    try {
        print(`  Creating ${type} index: ${name}`);
        db.getCollection(collection).createSearchIndex({
            name: name,
            type: type,
            definition: definition
        });
        print(`  ✓ Index created successfully`);
        created++;

        // Wait for index to be ready (optional, for immediate use)
        print(`  Waiting for index to be ready...`);
        if (waitForIndex(collection, name, 30)) {
            print(`  ✓ Index is READY`);
        } else {
            print(`  ⚠ Index still building (will be available shortly)`);
        }
    } catch (e) {
        print(`  ✗ Error creating index: ${e.message}`);
        errors++;
    }
}

// Summary
print("\n" + "=".repeat(60));
print("Summary");
print("=".repeat(60));
print(`Created: ${created}`);
print(`Skipped (already exist): ${skipped}`);
print(`Errors: ${errors}`);

// Verify all indexes
print("\n" + "=".repeat(60));
print("Current Search Indexes");
print("=".repeat(60));

for (const indexDef of INDEXES) {
    const { collection, name } = indexDef;
    try {
        const indexes = db.getCollection(collection).getSearchIndexes();
        const idx = indexes.find(i => i.name === name);
        if (idx) {
            print(`[${collection}] ${name}: ${idx.status}`);
        } else {
            print(`[${collection}] ${name}: NOT FOUND`);
        }
    } catch (e) {
        print(`[${collection}] ${name}: ERROR - ${e.message}`);
    }
}

print("\n✓ Setup complete!");
