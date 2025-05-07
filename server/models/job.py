from datetime import datetime
import uuid
from server.config.database import db
from sqlalchemy.dialects.postgresql import JSON

class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'), nullable=False, index=True)
    job_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    result = db.Column(JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    campaign = db.relationship('Campaign', backref=db.backref('jobs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'job_type': self.job_type,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'execution_time': self.execution_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Job {self.id} type={self.job_type} status={self.status}>'

    @classmethod
    def create(cls, campaign_id, job_type, status, result=None, error=None, started_at=None, ended_at=None, execution_time=None):
        try:
            job = cls(
                campaign_id=campaign_id,
                job_type=job_type,
                status=status,
                result=result,
                error=error,
                started_at=started_at,
                ended_at=ended_at,
                execution_time=execution_time
            )
            db.session.add(job)
            db.session.commit()
            return job
        except Exception as e:
            db.session.rollback()
            raise

    def update_status(self, status, result=None, error=None, ended_at=None, execution_time=None):
        try:
            self.status = status
            if result is not None:
                self.result = result
            if error is not None:
                self.error = error
            if ended_at is not None:
                self.ended_at = ended_at
            if execution_time is not None:
                self.execution_time = execution_time
            self.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise 