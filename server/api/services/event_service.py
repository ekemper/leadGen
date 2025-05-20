from server.models import Event
from server.config.database import db
from server.utils.logging_config import app_logger
from werkzeug.exceptions import NotFound, BadRequest
import os
import json
from datetime import datetime

class EventService:
    def create_event(self, data):
        try:
            event = Event(
                source=data['source'],
                tag=data['tag'],
                data=data['data'],
                type=data['type']
            )
            db.session.add(event)
            db.session.commit()
            
            # Log all events to combined log
            app_logger.info(
                f"Event created: {data['tag']}",
                extra={
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': 'INFO',
                    'log_message': f"Event created: {data['tag']}",
                    'source': data.get('source', 'api'),
                    'component': 'event_service',
                    'event_data': data
                }
            )
            
            return event.to_dict()
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error creating event: {str(e)}", extra={'component': 'event_service', 'source': data.get('source', 'api')})
            raise BadRequest(str(e))

    def get_event(self, event_id):
        event = Event.query.get(event_id)
        if not event:
            raise NotFound('Event not found')
        return event.to_dict()

    def get_events(self):
        events = Event.query.order_by(Event.created_at.desc()).all()
        return [event.to_dict() for event in events]

    def handle_console_logs(self, logs):
        """Handle console logs from the browser."""
        try:
            # Log each console log entry to combined log
            for log in logs:
                app_logger.info(
                    "Browser console log received",
                    extra={
                        'timestamp': log.get('timestamp', datetime.utcnow().isoformat()),
                        'level': log.get('level', 'INFO').upper(),
                        'log_message': log.get('message', ''),
                        'source': 'browser',
                        'component': 'frontend',
                        'data': log.get('data', [])
                    }
                )

            # Create event in database
            event = Event(
                source='browser',
                tag='console',
                data=logs,
                type='log'
            )
            db.session.add(event)
            db.session.commit()

            return {'status': 'success', 'message': 'Logs processed successfully'}
        except Exception as e:
            db.session.rollback()
            app_logger.error("Error handling console logs", extra={'error': str(e), 'source': 'browser', 'component': 'frontend'})
            raise BadRequest(str(e))

    @staticmethod
    def log_event(event_type, data=None):
        """Log a browser event with the given type and data.
        
        Args:
            event_type (str): Type of event (e.g., 'click', 'pageview')
            data (dict): Additional event data
        """
        try:
            event_data = {
                'type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data or {}
            }
            
            app_logger.info(
                f"Browser event: {event_type}",
                extra={
                    'event': event_data,
                    'source': 'browser'
                }
            )
            
            return True
            
        except Exception as e:
            app_logger.error(
                f"Failed to log browser event: {str(e)}",
                extra={
                    'event_type': event_type,
                    'error': str(e),
                    'source': 'browser'
                }
            )
            return False
    
    @staticmethod
    def log_page_view(page_name, user_id=None):
        """Log a page view event.
        
        Args:
            page_name (str): Name of the page being viewed
            user_id (str): Optional ID of the user viewing the page
        """
        data = {
            'page': page_name,
            'user_id': user_id
        }
        
        app_logger.info(
            f"Page view: {page_name}",
            extra={
                'event': {
                    'type': 'pageview',
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'source': 'browser'
            }
        )
    
    @staticmethod
    def log_error(error_type, error_message, stack_trace=None):
        """Log a browser error event.
        
        Args:
            error_type (str): Type of error
            error_message (str): Error message
            stack_trace (str): Optional stack trace
        """
        data = {
            'type': error_type,
            'message': error_message,
            'stack_trace': stack_trace
        }
        
        app_logger.error(
            f"Browser error: {error_type}",
            extra={
                'event': {
                    'type': 'error',
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'source': 'browser'
            }
        ) 