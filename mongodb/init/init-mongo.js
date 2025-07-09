// MongoDB initialization script for PCAP Reporter
// This script creates the database, collections, and indexes

// Switch to the pcap_reporter database
db = db.getSiblingDB('pcap_reporter');

// Create collections with validation schemas
db.createCollection('reports', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['filename', 'status', 'created_at'],
            properties: {
                filename: {
                    bsonType: 'string',
                    description: 'Original filename of the PCAP file'
                },
                status: {
                    bsonType: 'string',
                    enum: ['pending', 'processing', 'completed', 'failed'],
                    description: 'Current status of the analysis'
                },
                file_size: {
                    bsonType: 'long',
                    description: 'Size of the PCAP file in bytes'
                },
                upload_path: {
                    bsonType: 'string',
                    description: 'Path where the PCAP file is stored'
                },
                created_at: {
                    bsonType: 'date',
                    description: 'When the report was created'
                },
                updated_at: {
                    bsonType: 'date',
                    description: 'When the report was last updated'
                },
                completed_at: {
                    bsonType: 'date',
                    description: 'When the analysis was completed'
                },
                error_message: {
                    bsonType: 'string',
                    description: 'Error message if analysis failed'
                },
                analysis_results: {
                    bsonType: 'object',
                    description: 'Complete analysis results'
                }
            }
        }
    }
});

db.createCollection('analysis_jobs', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['report_id', 'job_id', 'status', 'created_at'],
            properties: {
                report_id: {
                    bsonType: 'objectId',
                    description: 'Reference to the report'
                },
                job_id: {
                    bsonType: 'string',
                    description: 'Celery job ID'
                },
                status: {
                    bsonType: 'string',
                    enum: ['pending', 'started', 'retry', 'failure', 'success'],
                    description: 'Current status of the job'
                },
                created_at: {
                    bsonType: 'date',
                    description: 'When the job was created'
                },
                started_at: {
                    bsonType: 'date',
                    description: 'When the job started processing'
                },
                completed_at: {
                    bsonType: 'date',
                    description: 'When the job completed'
                },
                progress: {
                    bsonType: 'int',
                    minimum: 0,
                    maximum: 100,
                    description: 'Job progress percentage'
                },
                result: {
                    bsonType: 'object',
                    description: 'Job result data'
                },
                error: {
                    bsonType: 'string',
                    description: 'Error message if job failed'
                }
            }
        }
    }
});

db.createCollection('users', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['username', 'email', 'hashed_password', 'created_at'],
            properties: {
                username: {
                    bsonType: 'string',
                    description: 'Unique username'
                },
                email: {
                    bsonType: 'string',
                    pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
                    description: 'User email address'
                },
                hashed_password: {
                    bsonType: 'string',
                    description: 'Hashed password'
                },
                is_active: {
                    bsonType: 'bool',
                    description: 'Whether the user is active'
                },
                is_admin: {
                    bsonType: 'bool',
                    description: 'Whether the user has admin privileges'
                },
                created_at: {
                    bsonType: 'date',
                    description: 'When the user was created'
                },
                last_login: {
                    bsonType: 'date',
                    description: 'When the user last logged in'
                }
            }
        }
    }
});

// Create indexes for better performance
print('Creating indexes...');

// Reports collection indexes
db.reports.createIndex({ 'filename': 1 });
db.reports.createIndex({ 'status': 1 });
db.reports.createIndex({ 'created_at': -1 });
db.reports.createIndex({ 'updated_at': -1 });
db.reports.createIndex({ 'status': 1, 'created_at': -1 });

// Analysis jobs collection indexes
db.analysis_jobs.createIndex({ 'report_id': 1 });
db.analysis_jobs.createIndex({ 'job_id': 1 }, { unique: true });
db.analysis_jobs.createIndex({ 'status': 1 });
db.analysis_jobs.createIndex({ 'created_at': -1 });
db.analysis_jobs.createIndex({ 'report_id': 1, 'status': 1 });

// Users collection indexes
db.users.createIndex({ 'username': 1 }, { unique: true });
db.users.createIndex({ 'email': 1 }, { unique: true });
db.users.createIndex({ 'created_at': -1 });

// Create default admin user (change password in production!)
db.users.insertOne({
    username: 'admin',
    email: 'admin@pcap-reporter.local',
    hashed_password: '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', // 'secret'
    is_active: true,
    is_admin: true,
    created_at: new Date(),
    last_login: null
});

print('Database initialization completed successfully!');
print('Collections created: reports, analysis_jobs, users');
print('Indexes created for optimal performance');
print('Default admin user created (username: admin, password: secret)');
print('IMPORTANT: Change the default admin password in production!'); 