


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


# Here is detailed information about what needs to happen for the code change to be successful:

## 1. Context & Overview
**Project Type:** [e.g., Flask API, React frontend, Full-stack web app, etc.]
**Technology Stack:** [e.g., Python/Flask, React/TypeScript, PostgreSQL, etc.]
**Current State:** [Brief description of what currently exists]

## 2. Change Request
**Summary:** [One-line description of what you want to achieve]

**Detailed Description:**
[Provide a clear, detailed explanation of the desired change. Include:]
- What functionality needs to be added/modified/removed
- Why this change is needed
- How it should work from a user perspective

## 3. Technical Requirements
**Must Have:**
- [ ] [Specific requirement 1]
- [ ] [Specific requirement 2]
- [ ] [Specific requirement 3]

**Nice to Have:**
- [ ] [Optional enhancement 1]
- [ ] [Optional enhancement 2]

**Constraints:**
- [Any limitations, restrictions, or guidelines to follow]
- [Performance requirements]
- [Security considerations]
- [Compatibility requirements]

## 4. Files & Components Involved
**Primary Files to Modify:**
- `path/to/file1.py` - [Brief description of changes needed]
- `path/to/file2.tsx` - [Brief description of changes needed]

**Related Files (may need updates):**
- `path/to/related1.py`
- `path/to/related2.tsx`

**New Files to Create:**
- `path/to/new_file.py` - [Purpose/description]

## 5. Expected Behavior
**Before:** [Current behavior/state]
**After:** [Expected behavior after changes]

**User Flow:**
1. [Step 1 of user interaction]
2. [Step 2 of user interaction]
3. [Expected outcome]

## 6. API/Interface Changes
**New Endpoints:**
- `POST /api/endpoint` - [Description]
- `GET /api/another` - [Description]

**Modified Endpoints:**
- `PUT /api/existing` - [What changes]

**Data Models:**
- [Any new or modified database tables/models]
- [New fields or relationships]

## 7. Testing Requirements
**Unit Tests:** [What needs to be tested]
**Integration Tests:** [End-to-end scenarios to verify]
**Manual Testing Steps:**
1. [Step 1]
2. [Step 2]
3. [Expected result]

## 8. Dependencies & Setup
**New Dependencies:** [Any new packages/libraries needed]
**Environment Variables:** [New or modified env vars]
**Database Changes:** [Migrations, new tables, etc.]
**Build/Deploy Changes:** [Any changes to build process]

## 9. Examples & References
**Similar Implementations:** [Point to existing code that does something similar]
**External References:** [Links to documentation, examples, etc.]
**Mockups/Wireframes:** [Visual references if applicable]

## 10. Success Criteria
The change will be considered complete when:
- [ ] [Specific measurable outcome 1]
- [ ] [Specific measurable outcome 2]
- [ ] [All tests pass]
- [ ] [Documentation is updated]
- [ ] [No breaking changes to existing functionality]

---

# Please create the plan for this task and document it!