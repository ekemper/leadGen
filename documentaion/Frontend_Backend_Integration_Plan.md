# Frontend-Backend Integration Implementation Plan

## Project Overview
**Project Type:** Full-stack web application with FastAPI backend and React/TypeScript frontend  
**Technology Stack:** Python/FastAPI, React 19/TypeScript, PostgreSQL, Redis, Vite  
**Current State:** Well-formed API for user auth, campaigns, organizations, leads, and jobs. Frontend app exists but needs full API integration.

## General Rules & Instructions

### Technical Assessment & User Interaction
- **CRITICAL**: In interacting with the User, always make a technical, critical assessment for any queries, statements, ideas, questions. Don't be afraid to question the user's plan.
- **CLARITY**: Always ask for more clarification if needed from the user when implementing the steps of the plan.
- **RATIONALE**: NEVER MAKE SHIT UP - always provide rationale for a decision.

### Implementation Guidelines
- **Code Changes**: In cases where there are code edits, the AI agent is to perform the changes.
- **Command Execution**: In cases where there are commands to be run, the AI agent is to run them in the chat window context and parse the output for errors and other actionable information.
- **Migration Commands**: When creating and running migrations, run the commands in the API docker container.
- **Testing Focus**: Pay particular attention to the API testing logic (routes, service, model, tests). Always run the tests after making changes to the API.
- **Individual Tests**: When running individual tests, run them in the API docker container: use `docker exec api pytest...`
- **Full Test Suite**: When running the whole suite of tests, use `make docker-test`.
- **Test Updates**: When planning code edits, plan to update the tests immediately.

### Environment & Configuration
- **Environment Variables**: If there are any env vars that need to be updated or created, use the .env.example as a reference. Create any new env vars in the .env.example file.
- **Environment Reference**: If you need to reference env vars, the example file is up to date with all that is available in the actual .env. Or, you can use `cat .env`.
- **Environment Safety**: Do not modify the .env file directly.

## Current State Analysis

### Backend API Assessment
Based on codebase analysis, the following endpoints are available:

#### Authentication (`/api/v1/auth/`)
- `POST /signup` - User registration (email whitelist enforced)
- `POST /login` - User authentication (returns JWT token)
- `GET /me` - Get current user information (protected)

#### Organizations (`/api/v1/organizations/`)
- `GET /` - List organizations with pagination
- `POST /` - Create new organization
- `GET /{id}` - Get specific organization
- `PUT /{id}` - Update organization
- `DELETE /{id}` - Delete organization

#### Campaigns (`/api/v1/campaigns/`)
- `GET /` - List campaigns with optional organization filtering
- `POST /` - Create new campaign
- `GET /{id}` - Get specific campaign
- `PUT /{id}` - Update campaign
- `DELETE /{id}` - Delete campaign
- `POST /{id}/start` - Start campaign processing
- `GET /{id}/status` - Get campaign status
- `GET /{id}/details` - Get detailed campaign information

#### Jobs (`/api/v1/jobs/`)
- `GET /` - List jobs with filtering options
- `POST /` - Create new job
- `GET /{id}` - Get specific job
- `PUT /{id}` - Update job
- `DELETE /{id}` - Delete job

#### Leads (`/api/v1/leads/`)
- `GET /` - List leads with filtering
- `POST /` - Create new lead
- `GET /{id}` - Get specific lead
- `PUT /{id}` - Update lead
- `DELETE /{id}` - Delete lead

#### Health (`/api/v1/health/`)
- `GET /` - Basic health check
- `GET /ready` - Readiness check
- `GET /live` - Liveness check

### Frontend Current State Assessment
Based on codebase analysis:

#### Current API Integration Issues
1. **Path Mismatch**: Frontend uses `/api/` paths while backend expects `/api/v1/` paths
2. **Authentication Flow**: Basic authentication exists but lacks proper context management
3. **Error Handling**: Inconsistent error handling across components
4. **Data Fetching**: Ad-hoc API calls without centralized service layer
5. **Type Safety**: Missing TypeScript interfaces for API responses

#### Current Frontend Features
- **Authentication Pages**: SignIn, SignUp (partially implemented)
- **Campaign Management**: List, Detail, Create pages
- **Organization Management**: List, Detail, Create pages
- **Protected Routes**: Basic ProtectedRoute component exists
- **UI Components**: Comprehensive UI component library

### CORS Configuration Analysis
Current CORS settings in backend:
```python
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

**Issue Identified**: Frontend runs on `http://localhost:5173` (Vite default) but CORS only allows ports 3000 and 8000.

## Implementation Steps

### Phase 1: Environment & Configuration Setup

#### Step 1.1: Update CORS Configuration
**Goal**: Enable API communication from frontend running locally on port 5173

**Actions**:
1. Add `http://localhost:5173` to BACKEND_CORS_ORIGINS in .env.example
2. Document the change requirement for user to update actual .env file
3. Verify CORS configuration in app/main.py

**Verification Strategy**:
- Check that .env.example contains the new CORS origin
- Test API accessibility from frontend development server
- Run `curl -H "Origin: http://localhost:5173" http://localhost:5001/api/v1/health` to verify CORS

**Expected Outcome**: Frontend development server can successfully make API requests

#### Step 1.2: Frontend Environment Configuration
**Goal**: Properly configure frontend environment variables

**Actions**:
1. Create frontend/.env.example with VITE_API_URL variable
2. Update vite-env.d.ts with proper TypeScript definitions
3. Verify API_BASE_URL configuration in frontend/src/config/api.ts

**Verification Strategy**:
- Check that environment variables are properly typed
- Verify API base URL resolves correctly in development
- Test environment variable loading in browser console

**Expected Outcome**: Frontend properly configured to communicate with backend API

### Phase 2: API Client Layer Standardization

#### Step 2.1: Fix API Endpoint Alignment
**Goal**: Align frontend API calls with backend endpoint structure

**Actions**:
1. Update all frontend API calls from `/api/` to `/api/v1/` pattern
2. Standardize request/response handling in api.ts
3. Add proper TypeScript interfaces for all API responses
4. Implement consistent error handling across all API methods

**Files to Update**:
- `frontend/src/config/api.ts` - Update base configuration
- `frontend/src/pages/CampaignsList.tsx` - Fix campaign API calls
- `frontend/src/pages/OrganizationsList.tsx` - Fix organization API calls
- `frontend/src/pages/CampaignDetail.tsx` - Fix campaign detail calls
- `frontend/src/pages/OrganizationDetail.tsx` - Fix organization detail calls
- `frontend/src/components/auth/SignInForm.tsx` - Fix authentication calls

**Verification Strategy**:
- Run frontend in development mode
- Test each API endpoint from browser network tab
- Verify proper error responses are handled
- Check that authentication headers are included in protected requests

**Expected Outcome**: All frontend API calls properly aligned with backend endpoints

#### Step 2.2: Create TypeScript Interfaces for API Responses
**Goal**: Ensure type safety across frontend-backend communication

**Actions**:
1. Create `frontend/src/types/api.ts` with interfaces matching backend schemas
2. Create individual type files for each domain:
   - `frontend/src/types/auth.ts`
   - `frontend/src/types/campaign.ts`
   - `frontend/src/types/organization.ts`
   - `frontend/src/types/job.ts`
   - `frontend/src/types/lead.ts`
3. Update API client to use proper typing
4. Update all components to use typed interfaces

**Verification Strategy**:
- Run TypeScript compiler to verify no type errors
- Test API responses match interface definitions
- Verify IDE provides proper autocomplete and error checking

**Expected Outcome**: Fully typed API communication with compile-time error checking

### Phase 3: Authentication System Integration

#### Step 3.1: Create Authentication Context
**Goal**: Implement centralized authentication state management

**Actions**:
1. Create `frontend/src/context/AuthContext.tsx` with comprehensive auth state
2. Implement authentication methods (login, signup, logout, refresh)
3. Add proper error handling and loading states
4. Integrate with existing token storage mechanism

**Features to Implement**:
- User state management
- Token management and persistence
- Automatic token refresh on app load
- Centralized authentication error handling
- Loading states for auth operations

**Verification Strategy**:
- Test login flow from SignIn page
- Test signup flow from SignUp page
- Test token persistence across browser refresh
- Test automatic logout on token expiration
- Verify protected routes work with authentication context

**Expected Outcome**: Fully functional authentication system with centralized state management

#### Step 3.2: Update Authentication Components
**Goal**: Integrate authentication context with existing auth components

**Actions**:
1. Update `frontend/src/components/auth/SignInForm.tsx` to use auth context
2. Update `frontend/src/components/auth/ProtectedRoute.tsx` to use auth context
3. Create `frontend/src/components/auth/SignUpForm.tsx` with proper integration
4. Update `frontend/src/components/header/UserDropdown.tsx` to use auth context

**Verification Strategy**:
- Test complete authentication flow (signup -> login -> logout)
- Test protected route access control
- Test user information display in header
- Verify proper error messages for authentication failures

**Expected Outcome**: Seamless authentication experience across all components

#### Step 3.3: Add Authentication to App Root
**Goal**: Wrap application with authentication provider

**Actions**:
1. Update `frontend/src/App.tsx` to include AuthProvider
2. Ensure proper provider hierarchy with other contexts
3. Add loading states for authentication initialization
4. Implement authentication-aware routing

**Verification Strategy**:
- Test app initialization with existing token
- Test app initialization without token
- Verify proper loading states during auth initialization
- Test authentication state persistence across app restarts

**Expected Outcome**: Application properly wrapped with authentication context

### Phase 4: Organization Management Integration

#### Step 4.1: Update Organization API Integration
**Goal**: Implement complete organization CRUD operations

**Actions**:
1. Create `frontend/src/services/organizationService.ts` with typed API calls
2. Update `frontend/src/pages/OrganizationsList.tsx` with proper API integration
3. Update `frontend/src/pages/OrganizationDetail.tsx` with full CRUD operations
4. Update `frontend/src/pages/OrganizationCreate.tsx` with proper form handling

**API Operations to Implement**:
- List organizations with pagination
- Create new organization
- Get organization details
- Update organization
- Delete organization

**Verification Strategy**:
- Test organization list loading and pagination
- Test organization creation with form validation
- Test organization editing with proper data loading
- Test organization deletion with confirmation
- Verify API error handling for each operation

**Expected Outcome**: Full organization management functionality

#### Step 4.2: Add Organization Data Validation
**Goal**: Ensure data consistency between frontend and backend

**Actions**:
1. Implement frontend validation matching backend schema validation
2. Add proper error display for validation failures
3. Implement client-side form validation with real-time feedback
4. Add loading states for all organization operations

**Verification Strategy**:
- Test form validation with invalid data
- Test backend validation error display
- Test loading states during API operations
- Verify data consistency between frontend forms and backend schemas

**Expected Outcome**: Robust organization management with proper validation

### Phase 5: Campaign Management Integration

#### Step 5.1: Update Campaign API Integration
**Goal**: Implement complete campaign CRUD operations with status management

**Actions**:
1. Create `frontend/src/services/campaignService.ts` with typed API calls
2. Update `frontend/src/pages/CampaignsList.tsx` with proper API integration
3. Update `frontend/src/pages/CampaignDetail.tsx` with full CRUD operations
4. Implement campaign status management and monitoring

**API Operations to Implement**:
- List campaigns with organization filtering
- Create new campaign with file upload
- Get campaign details and status
- Update campaign
- Delete campaign
- Start campaign processing
- Monitor campaign status

**Verification Strategy**:
- Test campaign list loading with organization filtering
- Test campaign creation with file upload
- Test campaign status monitoring and updates
- Test campaign editing with proper data loading
- Test campaign deletion with confirmation
- Verify real-time status updates

**Expected Outcome**: Full campaign management functionality with status monitoring

### Phase 6: Jobs and Leads Integration

#### Step 6.1: Implement Jobs API Integration
**Goal**: Add complete jobs API communication logic

**Actions**:
1. Create `frontend/src/services/jobService.ts` with typed API calls
2. Create `frontend/src/types/job.ts` with proper TypeScript interfaces
3. Add job filtering and search API methods
4. Ensure proper error handling for all job operations

**API Operations to Implement**:
- List jobs with filtering options
- Create new job
- Get specific job details
- Update job
- Delete job

**Verification Strategy**:
- Test job service API calls independently
- Verify API request/response formats match backend expectations
- Test error handling for each operation
- Verify proper TypeScript typing throughout

**Expected Outcome**: Complete jobs API service layer ready for integration with UI components

#### Step 6.2: Implement Leads API Integration
**Goal**: Add complete leads API communication logic

**Actions**:
1. Create `frontend/src/services/leadService.ts` with typed API calls
2. Create `frontend/src/types/lead.ts` with proper TypeScript interfaces  
3. Add lead filtering and search API methods
4. Ensure proper error handling for all lead operations

**API Operations to Implement**:
- List leads with filtering
- Create new lead
- Get specific lead details
- Update lead
- Delete lead

**Verification Strategy**:
- Test lead service API calls independently
- Verify API request/response formats match backend expectations
- Test error handling for each operation
- Verify proper TypeScript typing throughout

**Expected Outcome**: Complete leads API service layer ready for integration with UI components

### Phase 7: Error Handling and User Experience

#### Step 7.1: Implement Global Error Handling
**Goal**: Add consistent error handling across the application

**Actions**:
1. Create `frontend/src/utils/errorHandler.ts` for centralized error processing
2. Add toast notifications for user feedback ( review current implementation)
3. Add proper loading states for all operations

**Verification Strategy**:
- Test error handling for network failures
- Test error handling for API validation errors
- Test retry mechanisms
- Verify user feedback for all error states

**Expected Outcome**: Robust error handling with clear user feedback

#### Step 7.2: Add Loading States and User Feedback
**Goal**: Improve user experience with proper feedback

**Actions**:
1. Add loading spinners for all API operations
2. Implement skeleton loading for list views
3. Add success notifications for completed operations
4. Implement optimistic updates where appropriate

**Verification Strategy**:
- Test loading states for all operations
- Test success notifications
- Test optimistic updates
- Verify user experience during slow network conditions

**Expected Outcome**: Polished user experience with proper feedback

### Phase 8: Testing and Validation

#### Step 8.1: API Integration Testing
**Goal**: Ensure all API integrations work correctly

**Actions**:
1. Test all authentication flows
2. Test all CRUD operations for each entity
3. Test error handling scenarios
4. Test concurrent operations

**Verification Strategy**:
- Run comprehensive manual testing of all features
- Test edge cases and error conditions
- Verify data consistency across operations
- Test performance under load

**Expected Outcome**: Fully tested and validated API integration

## Success Criteria

The frontend-backend integration will be considered complete when:

### Functional Requirements
- [ ] **Authentication**: Complete signup, login, logout, and token management
- [ ] **Organizations**: Full CRUD operations with proper validation
- [ ] **Campaigns**: Full CRUD operations with status monitoring
- [ ] **Jobs**: Full CRUD operations with filtering
- [ ] **Leads**: Full CRUD operations with search
- [ ] **Error Handling**: Consistent error handling across all features
- [ ] **Loading States**: Proper loading indicators for all operations

### Technical Requirements
- [ ] **API Alignment**: All frontend API calls use correct `/api/v1/` endpoints
- [ ] **Type Safety**: Full TypeScript coverage with proper API response types
- [ ] **Authentication Context**: Centralized auth state management
- [ ] **Service Layer**: Organized API service files for each domain
- [ ] **CORS Configuration**: Proper CORS setup for local development

### User Experience Requirements
- [ ] **Responsive Design**: Works on desktop, tablet, and mobile
- [ ] **Error Messages**: Clear, actionable error messages for users
- [ ] **Loading Feedback**: Appropriate loading states for all operations
- [ ] **Success Feedback**: Clear confirmation of successful operations
- [ ] **Navigation**: Intuitive navigation between features

### Performance Requirements
- [ ] **Load Times**: Fast initial load and navigation
- [ ] **API Efficiency**: Optimized API calls with proper caching
- [ ] **Memory Usage**: No memory leaks in React components
- [ ] **Network Handling**: Graceful handling of slow/failed network requests

## Risk Mitigation

### Identified Risks and Mitigation Strategies

1. **API Schema Changes**: 
   - Risk: Backend schema changes break frontend
   - Mitigation: Use TypeScript interfaces and automated testing

2. **Authentication Security**:
   - Risk: Insecure token handling
   - Mitigation: Follow security best practices for JWT handling

3. **Performance Issues**:
   - Risk: Slow API responses impact user experience
   - Mitigation: Implement proper loading states and error handling

4. **CORS Issues**:
   - Risk: Cross-origin requests blocked
   - Mitigation: Proper CORS configuration and testing

## Documentation and Maintenance

### Documentation Requirements
- [ ] API endpoint documentation
- [ ] Component usage documentation
- [ ] Deployment and configuration guide
- [ ] Troubleshooting guide

### Maintenance Considerations
- Regular dependency updates
- Security vulnerability monitoring
- Performance monitoring
- User feedback integration

---

**Note**: This plan should be executed step by step, with each step fully completed and verified before proceeding to the next. Any issues or deviations should be documented and addressed before continuing. 