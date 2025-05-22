from server.models import Event
from server.config.database import db
from server.utils.logging_config import setup_logger, ContextLogger
from werkzeug.exceptions import NotFound, BadRequest
import os
import json
from datetime import datetime
from flask import g

# Set up logger
logger = setup_logger('event_service')

class EventService:
    def create_event(self, data):
        """Create a new event."""
        with ContextLogger(logger, event_type=data.get('type')):
            try:
                event = Event(**data)
                db.session.add(event)
                db.session.commit()
                
                logger.info("Event created", extra={
                    'metadata': {
                        'event_id': event.id,
                        'event_type': event.type,
                        'source': event.source
                    }
                })
                
                return event
            except Exception as e:
                db.session.rollback()
                logger.error("Failed to create event", extra={
                    'metadata': {
                        'error': str(e),
                        'data': data
                    }
                }, exc_info=True)
                raise BadRequest(str(e))

    def get_event(self, event_id):
        """Get a single event by ID."""
        with ContextLogger(logger, event_id=event_id):
            try:
                event = Event.query.get(event_id)
                if not event:
                    logger.warning("Event not found", extra={
                        'metadata': {'event_id': event_id}
                    })
                    raise NotFound('Event not found')
                logger.info("Event retrieved", extra={
                    'metadata': {'event_id': event_id}
                })
                return event.to_dict()
            except Exception as e:
                logger.error("Failed to get event", extra={
                    'metadata': {
                        'event_id': event_id,
                        'error': str(e)
                    }
                }, exc_info=True)
                raise

    def get_events(self):
        """Get all events ordered by creation date."""
        with ContextLogger(logger, operation='list_events'):
            try:
                events = Event.query.order_by(Event.created_at.desc()).all()
                logger.info("Events retrieved", extra={
                    'metadata': {'count': len(events)}
                })
                return [event.to_dict() for event in events]
            except Exception as e:
                logger.error("Failed to get events", extra={
                    'metadata': {'error': str(e)}
                }, exc_info=True)
                raise

    def handle_console_logs(self, logs):
        """Handle console logs from the browser."""
        with ContextLogger(logger, source='browser', component='frontend'):
            try:
                # Log each console log entry
                for log in logs:
                    logger.info("Browser console log received", extra={
                        'metadata': {
                            'timestamp': log.get('timestamp', datetime.utcnow().isoformat()),
                            'level': log.get('level', 'INFO').upper(),
                            'log_message': log.get('message', ''),
                            'data': log.get('data', [])
                        }
                    })

                # Create event in database
                event = Event(
                    source='browser',
                    tag='console',
                    data=logs,
                    type='log'
                )
                db.session.add(event)
                db.session.commit()

                logger.info("Console logs processed", extra={
                    'metadata': {
                        'event_id': event.id,
                        'log_count': len(logs)
                    }
                })

                return {'status': 'success', 'message': 'Logs processed successfully'}
            except Exception as e:
                db.session.rollback()
                logger.error("Failed to handle console logs", extra={
                    'metadata': {
                        'error': str(e),
                        'log_count': len(logs)
                    }
                }, exc_info=True)
                raise BadRequest(str(e))

    @staticmethod
    def log_event(event_type, data=None):
        """Log a browser event with the given type and data.
        
        Args:
            event_type (str): Type of event (e.g., 'click', 'pageview')
            data (dict): Additional event data
        """
        with ContextLogger(logger, event_type=event_type, source='browser'):
            try:
                event_data = {
                    'type': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data or {}
                }
                
                logger.info("Browser event received", extra={
                    'metadata': event_data
                })
                
                return True
                
            except Exception as e:
                logger.error("Failed to log browser event", extra={
                    'metadata': {
                        'event_type': event_type,
                        'error': str(e)
                    }
                }, exc_info=True)
                return False
    
    @staticmethod
    def log_page_view(page_name, user_id=None):
        """Log a page view event.
        
        Args:
            page_name (str): Name of the page being viewed
            user_id (str): Optional ID of the user viewing the page
        """
        with ContextLogger(logger, page=page_name, user_id=user_id, source='browser'):
            data = {
                'page': page_name,
                'user_id': user_id
            }
            
            logger.info("Page view", extra={
                'metadata': {
                    'type': 'pageview',
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
    
    @staticmethod
    def log_error(error_type, error_message, stack_trace=None):
        """Log a browser error event.
        
        Args:
            error_type (str): Type of error
            error_message (str): Error message
            stack_trace (str): Optional stack trace
        """
        with ContextLogger(logger, error_type=error_type, source='browser'):
            data = {
                'type': error_type,
                'message': error_message,
                'stack_trace': stack_trace
            }
            
            logger.error("Browser error", extra={
                'metadata': {
                    'type': 'error',
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }, exc_info=bool(stack_trace)) 