// MongoDB initialization script for COTAI

// Switch to COTAI database
db = db.getSiblingDB('cotai');

// Create collections with validation
db.createCollection('documents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['filename', 'content_type', 'size', 'created_at'],
      properties: {
        filename: { bsonType: 'string' },
        content_type: { bsonType: 'string' },
        size: { bsonType: 'number' },
        ocr_text: { bsonType: 'string' },
        analysis_results: { bsonType: 'object' },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' }
      }
    }
  }
});

db.createCollection('tender_analysis', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['tender_id', 'analysis_type', 'results', 'created_at'],
      properties: {
        tender_id: { bsonType: 'string' },
        analysis_type: { bsonType: 'string' },
        results: { bsonType: 'object' },
        confidence_score: { bsonType: 'number' },
        created_at: { bsonType: 'date' }
      }
    }
  }
});

db.createCollection('search_history', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'query', 'filters', 'results_count', 'created_at'],
      properties: {
        user_id: { bsonType: 'string' },
        query: { bsonType: 'string' },
        filters: { bsonType: 'object' },
        results_count: { bsonType: 'number' },
        created_at: { bsonType: 'date' }
      }
    }
  }
});

// Create indexes
db.documents.createIndex({ 'filename': 1 });
db.documents.createIndex({ 'created_at': -1 });
db.documents.createIndex({ 'content_type': 1 });

db.tender_analysis.createIndex({ 'tender_id': 1 });
db.tender_analysis.createIndex({ 'analysis_type': 1 });
db.tender_analysis.createIndex({ 'created_at': -1 });

db.search_history.createIndex({ 'user_id': 1 });
db.search_history.createIndex({ 'created_at': -1 });

// Create text indexes for search
db.documents.createIndex({ 'ocr_text': 'text', 'filename': 'text' });

print('MongoDB initialization completed for COTAI database');