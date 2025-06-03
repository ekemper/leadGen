


# Your job is to create an extreamly detailed set of step by step instructions for an ai agent to perform the following task:

Integrate the api rate limiters into the api. Follow the instructions below to create the plan.


## In creating the plan, the following rules must be observed and followed:

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

    * For the plan you create, please create a md document in the root of the project and put the instructions there for safe keeping


# Here is detailed information about what needs to happen for the code change to be successful:


**Detailed Description:**
- What functionality needs to be added/modified/removed
    * i've added two new files: api_integration_rate_limiter.py and API_RATE_LIMITER_README.md
    * please use the readme as a guide for implemneting.
    * each of the external service integrations must be rate limited : {millionVerifier, perplexity, openai, and instantly}
    * the rate limiting shoudl be tested - please propose a testing strategy
- Why this change is needed
    *  we need to limit the rate at which we are calling the external services that we use to avoid getting ip blocked.

##  Technical Requirements
**Must Have:**
please derive these from the readme

##  Files & Components Involved
- `api_integration_rate_limiter.py`
- `API_RATE_LIMITER_README.md`

- the background services:
    * apollo serviece
    * email_verifier_service
    * instantly service
    * openai service
    * perplexity service

##  Expected Behavior
**Before:** no rate limiting implemented for outgoing api calls
**After:** a consistant, testable, rate limiter module is usable by all of the thirdparty api services that we make calls to. all test pass




## Testing Requirements
**Unit Tests:** no unit tests for now
**Integration Tests:** [End-to-end scenarios to verify]


## 8. Dependencies & Setup
**New Dependencies:** please install any new dependencies in requirements.txt
**Environment Variables:** add any new env vars to the .env.example. then I will add them to the .env manually ( this is important !)
**Database Changes:** no database changes
**Build/Deploy Changes:** no build / deploy changes

## 9. Examples & References
* see the readme

## 10. Success Criteria
The change will be considered complete when:
- [ ] each api service integration can be individually configured to have a max requests per minute and it does not exceed that in operation
- [ ] [All tests pass]
- [ ] [Documentation is updated]
- [ ] [No breaking changes to existing functionality]

---

# Please create the plan for this task and document it!