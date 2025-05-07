import React, { useEffect } from 'react';
import { logger } from '../utils/logger';

const LoggingTest: React.FC = () => {
    useEffect(() => {
        // Test different types of errors
        const testErrors = () => {
            // Test console error
            console.error('Test console error from LoggingTest component');

            // Test uncaught error
            try {
                throw new Error('Test uncaught error from LoggingTest component');
            } catch (error) {
                logger.logError(error as Error, {
                    tag: 'test.errors',
                    source: 'browser'
                });
            }

            // Test network error
            fetch('/api/nonexistent-endpoint')
                .catch(error => {
                    logger.logError(error as Error, {
                        tag: 'test.network_error',
                        source: 'browser'
                    });
                });

            // Test manual logging
            logger.logError(new Error('Test manual error log'), {
                tag: 'test.manual',
                source: 'browser'
            });
        };

        // Run tests after component mounts
        testErrors();
    }, []);

    return (
        <div>
            <h2>Logging Test Component</h2>
            <p>This component generates test errors to verify the logging system.</p>
            <p>Check the browser console and log files for the generated errors.</p>
        </div>
    );
};

export default LoggingTest; 