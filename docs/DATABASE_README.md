# Database Documentation

## Overview
This application uses PostgreSQL as the primary database, with SQLAlchemy as the ORM and Alembic for database migrations.

## Local Database Setup

### Prerequisites
- PostgreSQL 13+
- Python 3.9+
- psycopg2-binary

### Installation

1. Install PostgreSQL:
```bash
# macOS (using Homebrew)
brew install postgresql@13

# Start PostgreSQL service
brew services start postgresql@13
```

2. Create Database:
```bash
createdb leadgen
createuser -P leadgen_user  # You'll be prompted for a password
```

3. Grant Privileges:
```sql
psql leadgen
GRANT ALL PRIVILEGES ON DATABASE leadgen TO leadgen_user;
```

## Database Configuration

### Environment Variables
```bash
# .env file
DATABASE_URL=postgresql://leadgen_user:password@localhost:5432/leadgen
```

### SQLAlchemy Configuration
```python
# server/config.py
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
SQLALCHEMY_TRACK_MODIFICATIONS = False
```

## Data Models

### User Model
```python
# server/models/user.py
class User(db.Model):
    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    leads = db.relationship('Lead', backref='owner', lazy='dynamic')
```

### Lead Model
```python
# server/models/lead.py
class Lead(db.Model):
    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255))
    company = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    status = db.Column(db.Enum('new', 'contacted', 'qualified', 'lost'))
    source = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

## Database Migrations

### Initial Setup
```bash
# Initialize migrations directory
flask db init

# Create first migration
flask db migrate -m "Initial migration"

# Apply migration
flask db upgrade
```

### Managing Migrations

#### Create New Migration
```bash
# After model changes
flask db migrate -m "Add phone field to leads"
```

#### Apply Migrations
```bash
# Apply all pending migrations
flask db upgrade

# Rollback last migration
flask db downgrade

# Rollback to specific version
flask db downgrade <revision_id>
```

#### View Migration Status
```bash
# Show current revision
flask db current

# Show migration history
flask db history
```

### Migration Best Practices
1. Always review auto-generated migrations
2. Add data migrations in separate files
3. Make migrations reversible
4. Test migrations on staging before production
5. Backup database before applying migrations

## Data Management

### Seeding Data
```python
# server/seeds/development.py
def seed_development_data():
    # Create test users
    user = User(
        email='test@example.com',
        name='Test User'
    )
    user.set_password('password123')
    db.session.add(user)
    
    # Create test leads
    leads = [
        Lead(
            user_id=user.id,
            name='John Doe',
            email='john@example.com',
            status='new'
        ),
        # Add more test leads...
    ]
    db.session.bulk_save_objects(leads)
    db.session.commit()
```

### Database Backup and Restore

#### Local Backup
```bash
# Backup
pg_dump -U leadgen_user -d leadgen > backup.sql

# Restore
psql -U leadgen_user -d leadgen < backup.sql
```

#### Production Backup (Heroku)
```bash
# Manual backup
heroku pg:backups:capture

# Download latest backup
heroku pg:backups:download
```

## Query Optimization

### Indexing
```python
# Example index creation in models
class Lead(db.Model):
    __table_args__ = (
        db.Index('idx_lead_user_status', 'user_id', 'status'),
        db.Index('idx_lead_created_at', 'created_at'),
    )
```

### Query Best Practices
1. Use eager loading for relationships:
```python
# Bad
leads = Lead.query.all()
for lead in leads:
    print(lead.owner.name)  # N+1 queries

# Good
leads = Lead.query.options(joinedload(Lead.owner)).all()
```

2. Pagination:
```python
leads = Lead.query.paginate(
    page=page,
    per_page=20,
    error_out=False
)
```

3. Bulk Operations:
```python
# Bulk insert
db.session.bulk_save_objects(leads)
db.session.commit()

# Bulk update
Lead.query.filter(Lead.status == 'new').update(
    {'status': 'contacted'},
    synchronize_session=False
)
```

## Performance Monitoring

### Query Performance
```python
# Enable SQL logging
SQLALCHEMY_RECORD_QUERIES = True

# Log slow queries
SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost/db?statement_timeout=1000"
```

### Connection Pool Configuration
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
}
```

## Error Handling

### Database Errors
```python
from sqlalchemy.exc import SQLAlchemyError

try:
    db.session.commit()
except SQLAlchemyError as e:
    db.session.rollback()
    current_app.logger.error(f"Database error: {str(e)}")
    raise
```

## Security Considerations

1. SQL Injection Prevention
- Always use SQLAlchemy's query parameters
- Never concatenate strings for queries

2. Data Encryption
```python
from cryptography.fernet import Fernet

class EncryptedField(TypeDecorator):
    impl = String
    
    def process_bind_parameter(self, value, dialect):
        if value is not None:
            return encrypt_value(value)
        return value
```

3. Access Control
```python
def ensure_owner(user_id):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        lead = Lead.query.get_or_404(kwargs['lead_id'])
        if lead.user_id != user_id:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
``` 