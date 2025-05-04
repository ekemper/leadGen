from server.models import Event
from server.config.database import db
from server.utils.logger import logger
from werkzeug.exceptions import NotFound, BadRequest

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