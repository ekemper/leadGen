from server.models import Event
from server.config.database import db
from server.utils.logger import logger
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
            return event.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating event: {str(e)}")
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
        """Handle console logs from the browser and write them to a file."""
        try:
            # Create logs directory if it doesn't exist
            log_dir = os.path.join(os.getcwd(), 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Create or append to console.log file
            log_file = os.path.join(log_dir, 'console.log')
            
            # Format logs for file writing
            formatted_logs = []
            for log in logs:
                formatted_log = {
                    'timestamp': log['timestamp'],
                    'level': log['level'],
                    'message': log['message'],
                    'data': log.get('data', [])
                }
                formatted_logs.append(formatted_log)

            # Write to file
            with open(log_file, 'a') as f:
                for log in formatted_logs:
                    f.write(json.dumps(log) + '\n')

            # Also create an event in the database
            event = Event(
                source='browser',
                tag='console',
                data=logs,
                type='log'
            )
            db.session.add(event)
            db.session.commit()

            return {'status': 'success', 'message': 'Logs written successfully'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling console logs: {str(e)}")
            raise BadRequest(str(e)) 