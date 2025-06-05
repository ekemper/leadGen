
the testibility of the app has decreased to a point that is intractible. we need to reduce complexity. 

we will completeley remove the concept of the paused state of a campaign. jobs will keep the paused state.

the use of unavailable_services is too complex. the circuit breaker state ( only open and closed ) will be used as the source of truth for if the background processes can be resumed. 

the only means of closing the breaker will be from the front end - this will replace the concept of the queue being paused and resumed. only the state of the breaker will be important. 

The front end queue management page will have to be simplified greatly, however this will be in another plan. dont make any front end updates yet. 

it is critical that the existing logic around state changes of campaigns be updated to not involve a pending state. if the breaker opens the campaign will remain in a running state. 

if the breaker opens, the current running and pending jobs will be paused. 

when the breaker is closed, the paused jobs will be set to pending, and a new celery task of the correct type for each one will be created. The only means to close the breaker will be via an api endpoint ( potentially already exists ). in a later refactor, we will rework the queue management dash on the front end, keep the changes for this plan confined to the back end. 

please evaluate all of the documentation in the app to ensure this new paradigm is explained properly. Ensure that any references to older logic should be updated. 

TESTING will be critical here: please first identify and depricate all the tests that will be unneeded based on the new logic. tests that need to be updated should be updated. please consolidate if possible. please adopt a TDD approach here. create or update  the basic tests that will be needed and then, as you make edits to the code use them as confirmation that your changes were correct. 


The new logical for handling third party api integrations will be as follows:
* the current logic for handling third party api errors informs the circuit breaker of the error
* the breaker is triggered.
* all of the jobs in a pending or running state are switched to paused. 
* the campaigns that were in a running state will still be in a running state
* the queue status will be available via the existing endpoint, but the response should be greatly simplified- we will takle this in a different refactor. 

Please find all the TODOs in the codebase and use them to inform your plan - all the TODOs should be accomplished by the plan ( critical for continuity )

at the end of the plan make a checklist that incorporates all of the details that needed to be accomplished in the todos. when they are all done, please remove them from the code so we can start fresh

PLEASE IDENTIFY AND DOCUMENT ANY DISCONTIUTITIES IN THE LOGIC OR TECHNICAL RISKS WITH THIS SIMPLIFICATION

Simpicity is critical - focus on simplicity for the sake of my weary monkey brain. 

# Your job is to create an extreamly detailed set of step by step instructions for an ai agent to perform this task.


## In creating the plan, the following rules must be observed and followed:


    * always make a plan for approaching a problem

    * Make a comprehensive assessment of the entire application codebase, its archetecture, patterns, tests, services, and documentation. You will need to incorporate this knowledge into the plan you are creating. 

    * The current patterns, conventions, and configuration for this app should be maintained at all cost. If there are specific changes to establihed patterns, these should be documented. Please make copious use of doc strings and comments in source code to add context for decisions that are made. If there is significant change - please create a markdown document in the documentation directory to reestablish the source of truth for the pattern. 

    * The instructions should break the process down in to discrete, testable steps.

    * Each step should have a clear goal, a clear set of actions to be performed by the ai agent, and a strategy for confirming that the actions were sucessfull. ( either running tests, curling an endpoint, manual testing, or checking for specific rows in a database table. )

## The following instruction MUST BE followed as part of the implementation of the plan that you are creating. Please add them to the general rules / instructions section of the plan:

    * In interacting with the User, always make a technical, critical assessment for any queries, statements, ideas, questions... Don't be afraid to question the user's plan. 

    * Always ask for more clarification if needed from the user when implementing the steps of the plan. 
    
    * NEVER MAKE SHIT UP - always provide rationale for a desiscion. 

    * In cases where there are code edits, the ai agent is to perform the changes.

    * In cases where there are commands to be run, the ai agent is to run them in the chat window context and parse the output for errors and other actionable information.

    * When createing and running migrations, run the commands in the api docker container.

    * Pay particular attention to the api testing  logic ( routes, service, model, tests). Always run the tests after making changes to the api.

    * When running individual tests, run them in the api docker container: use ' Docker exec api pytest...'

    * When running the whole suite of tests, use 'make docker-test'.

    * Lets leave the unit tests out of the picture for the moment - we need a comprehensive set of functional api layer tests - the tests should hit the api and then check the database for results. 

    * When planning code edits, plan to update the tests immediately.

    * to assess what environment variables are used in the application you can run 'cat .env' 

    * DO NOT create or modify or otherwise fuck with the env files. 

    * if there are configuration values that need to be updated or modified, you can ask the user to add or change something

    * if there is a script or command that will need a connection to postgres or redis, the command or script should be run in the api socker container

    * before creating a command that uses a container name, please run `docker ps` to get the correct name

    * never use the depricated `docker-compose` command version. always use the newer `docker compose` command version.

    * For the plan you create, please create a md document in the root of the project and put the instructions there for safe keeping

