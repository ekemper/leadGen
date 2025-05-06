from server.models import Event
from server.config.database import db
from server.utils.logging_config import browser_logger, combined_logger
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
            
            # Log to browser logger if source is browser
            if data['source'] == 'browser':
                browser_logger.info(
                    f"Browser event: {data['tag']}",
                    extra={
                        'tag': data['tag'],
                        'type': data['type'],
                        'data': data['data']
                    }
                )
                combined_logger.info(
                    f"Browser event: {data['tag']}",
                    extra={
                        'component': 'browser',
                        'tag': data['tag'],
                        'type': data['type'],
                        'data': data['data']
                    }
                )
            
            return event.to_dict()
        except Exception as e:
            db.session.rollback()
            browser_logger.error(f"Error creating event: {str(e)}")
            combined_logger.error(
                f"Error creating event: {str(e)}",
                extra={'component': 'browser', 'error': str(e)}
            )
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
            # Log each console log entry
            for log in logs:
                log_data = {
                    'level': log['level'],
                    'console_message': log['message'],  # renamed to avoid conflict
                    'data': log.get('data', []),
                    'timestamp': log['timestamp']
                }
                
                browser_logger.info(
                    "Browser console log received",
                    extra=log_data
                )
                combined_logger.info(
                    "Browser console log received",
                    extra={**log_data, 'component': 'browser'}
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
            browser_logger.error("Error handling console logs", extra={'error': str(e)})
            combined_logger.error(
                "Error handling console logs",
                extra={'component': 'browser', 'error': str(e)}
            )
            raise BadRequest(str(e)) 