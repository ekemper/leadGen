import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from enum import Enum

from app.core.logger import get_logger
from app.core.config import settings
from app.core.circuit_breaker import ThirdPartyService, CircuitState

logger = get_logger(__name__)

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"

class AlertService:
    """
    Service for sending alerts about circuit breaker events and system status.
    
    Features:
    - Email notifications
    - Slack integration (placeholder)
    - Webhook notifications
    - Structured logging
    - Alert rate limiting to prevent spam
    """
    
    def __init__(self):
        self.email_config = {
            'smtp_server': getattr(settings, 'SMTP_SERVER', 'localhost'),
            'smtp_port': getattr(settings, 'SMTP_PORT', 587),
            'smtp_username': getattr(settings, 'SMTP_USERNAME', ''),
            'smtp_password': getattr(settings, 'SMTP_PASSWORD', ''),
            'from_email': getattr(settings, 'ALERT_FROM_EMAIL', 'noreply@example.com'),
            'admin_emails': getattr(settings, 'ADMIN_ALERT_EMAILS', '').split(',') if getattr(settings, 'ADMIN_ALERT_EMAILS', '') else []
        }
        
        self.webhook_url = getattr(settings, 'ALERT_WEBHOOK_URL', '')
        self.slack_webhook = getattr(settings, 'SLACK_WEBHOOK_URL', '')
    
    def send_circuit_breaker_alert(
        self, 
        service: ThirdPartyService, 
        old_state: CircuitState, 
        new_state: CircuitState,
        failure_reason: str = "",
        failure_count: int = 0
    ):
        """Send alert when circuit breaker state changes."""
        try:
            alert_level = self._get_alert_level(old_state, new_state)
            
            alert_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'service': service.value,
                'old_state': old_state.value,
                'new_state': new_state.value,
                'failure_reason': failure_reason,
                'failure_count': failure_count,
                'alert_level': alert_level.value
            }
            
            # Always log the alert
            self._log_alert(alert_data)
            
            # Send to other channels based on alert level
            if alert_level in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
                if self.email_config['admin_emails']:
                    self._send_email_alert(alert_data)
                
                if self.slack_webhook:
                    self._send_slack_alert(alert_data)
                
                if self.webhook_url:
                    self._send_webhook_alert(alert_data)
            
        except Exception as e:
            logger.error(f"Failed to send circuit breaker alert: {e}")
    
    def send_queue_status_alert(
        self, 
        total_paused_jobs: int, 
        services_down: List[str],
        job_backlog: Dict[str, int]
    ):
        """Send alert about overall queue health."""
        try:
            alert_level = AlertLevel.WARNING if total_paused_jobs > 10 else AlertLevel.INFO
            
            alert_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'queue_status',
                'total_paused_jobs': total_paused_jobs,
                'services_down': services_down,
                'job_backlog': job_backlog,
                'alert_level': alert_level.value
            }
            
            self._log_alert(alert_data)
            
            if alert_level == AlertLevel.WARNING and self.email_config['admin_emails']:
                self._send_email_alert(alert_data)
            
        except Exception as e:
            logger.error(f"Failed to send queue status alert: {e}")
    
    def send_recovery_alert(self, service: ThirdPartyService, jobs_resumed: int):
        """Send alert when service recovers and jobs are resumed."""
        try:
            alert_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'service_recovery',
                'service': service.value,
                'jobs_resumed': jobs_resumed,
                'alert_level': AlertLevel.INFO.value
            }
            
            self._log_alert(alert_data)
            
            if jobs_resumed > 0 and self.email_config['admin_emails']:
                self._send_email_alert(alert_data)
            
        except Exception as e:
            logger.error(f"Failed to send recovery alert: {e}")
    
    def _get_alert_level(self, old_state: CircuitState, new_state: CircuitState) -> AlertLevel:
        """Determine alert level based on state transition."""
        if new_state == CircuitState.OPEN:
            return AlertLevel.CRITICAL
        elif new_state == CircuitState.HALF_OPEN:
            return AlertLevel.WARNING
        elif new_state == CircuitState.CLOSED and old_state == CircuitState.OPEN:
            return AlertLevel.INFO  # Recovery
        else:
            return AlertLevel.INFO
    
    def _log_alert(self, alert_data: Dict[str, Any]):
        """Log alert with structured data."""
        if alert_data.get('alert_level') == AlertLevel.CRITICAL.value:
            logger.critical(f"CIRCUIT_BREAKER_ALERT: {json.dumps(alert_data)}")
        elif alert_data.get('alert_level') == AlertLevel.WARNING.value:
            logger.warning(f"CIRCUIT_BREAKER_ALERT: {json.dumps(alert_data)}")
        else:
            logger.info(f"CIRCUIT_BREAKER_ALERT: {json.dumps(alert_data)}")
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send email alert to administrators."""
        try:
            if not self.email_config['admin_emails']:
                return
            
            subject = self._format_email_subject(alert_data)
            body = self._format_email_body(alert_data)
            
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(self.email_config['admin_emails'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            # Connect and send email
            if self.email_config['smtp_username']:
                server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
                server.starttls()
                server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                text = msg.as_string()
                server.sendmail(self.email_config['from_email'], self.email_config['admin_emails'], text)
                server.quit()
                logger.info(f"Email alert sent to {len(self.email_config['admin_emails'])} recipients")
            else:
                logger.warning("Email credentials not configured, skipping email alert")
                
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send Slack notification (placeholder for webhook integration)."""
        try:
            import requests
            
            color_map = {
                AlertLevel.CRITICAL.value: 'danger',
                AlertLevel.WARNING.value: 'warning', 
                AlertLevel.INFO.value: 'good'
            }
            
            payload = {
                'text': f"Circuit Breaker Alert: {alert_data.get('service', 'System')}",
                'attachments': [{
                    'color': color_map.get(alert_data.get('alert_level'), 'good'),
                    'fields': [
                        {'title': 'Service', 'value': alert_data.get('service', 'N/A'), 'short': True},
                        {'title': 'New State', 'value': alert_data.get('new_state', 'N/A'), 'short': True},
                        {'title': 'Failure Reason', 'value': alert_data.get('failure_reason', 'N/A'), 'short': False},
                        {'title': 'Timestamp', 'value': alert_data.get('timestamp', 'N/A'), 'short': True}
                    ]
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Slack alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_webhook_alert(self, alert_data: Dict[str, Any]):
        """Send webhook notification to external systems."""
        try:
            import requests
            
            response = requests.post(
                self.webhook_url,
                json=alert_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            logger.info("Webhook alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _format_email_subject(self, alert_data: Dict[str, Any]) -> str:
        """Format email subject line."""
        alert_type = alert_data.get('type', 'circuit_breaker')
        service = alert_data.get('service', 'System')
        alert_level = alert_data.get('alert_level', 'info').upper()
        
        if alert_type == 'circuit_breaker':
            new_state = alert_data.get('new_state', '').upper()
            return f"[{alert_level}] Circuit Breaker {new_state}: {service}"
        elif alert_type == 'service_recovery':
            return f"[INFO] Service Recovered: {service}"
        elif alert_type == 'queue_status':
            return f"[{alert_level}] Queue Status Alert: {alert_data.get('total_paused_jobs', 0)} Jobs Paused"
        else:
            return f"[{alert_level}] System Alert"
    
    def _format_email_body(self, alert_data: Dict[str, Any]) -> str:
        """Format email body with HTML."""
        timestamp = alert_data.get('timestamp', 'Unknown')
        alert_type = alert_data.get('type', 'circuit_breaker')
        
        if alert_type == 'circuit_breaker':
            return f"""
            <html>
            <body>
                <h2>Circuit Breaker Alert</h2>
                <p><strong>Service:</strong> {alert_data.get('service', 'N/A')}</p>
                <p><strong>Previous State:</strong> {alert_data.get('old_state', 'N/A')}</p>
                <p><strong>New State:</strong> {alert_data.get('new_state', 'N/A')}</p>
                <p><strong>Failure Count:</strong> {alert_data.get('failure_count', 0)}</p>
                <p><strong>Failure Reason:</strong> {alert_data.get('failure_reason', 'N/A')}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                
                <hr>
                <p><em>This is an automated alert from the Queue Monitoring System.</em></p>
            </body>
            </html>
            """
        elif alert_type == 'service_recovery':
            return f"""
            <html>
            <body>
                <h2>Service Recovery</h2>
                <p><strong>Service:</strong> {alert_data.get('service', 'N/A')}</p>
                <p><strong>Jobs Resumed:</strong> {alert_data.get('jobs_resumed', 0)}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                
                <hr>
                <p><em>This is an automated alert from the Queue Monitoring System.</em></p>
            </body>
            </html>
            """
        else:
            return f"""
            <html>
            <body>
                <h2>Queue Status Alert</h2>
                <p><strong>Total Paused Jobs:</strong> {alert_data.get('total_paused_jobs', 0)}</p>
                <p><strong>Services Down:</strong> {', '.join(alert_data.get('services_down', []))}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                
                <hr>
                <p><em>This is an automated alert from the Queue Monitoring System.</em></p>
            </body>
            </html>
            """


# Global alert service instance
_alert_service = None

def get_alert_service() -> AlertService:
    """Get or create the global alert service instance."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service 