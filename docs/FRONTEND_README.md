# Frontend Documentation

## Overview
The frontend of our Lead Generation application is built using modern web technologies to provide a responsive and user-friendly interface.

## Tech Stack
- Next.js
- TypeScript
- Tailwind CSS
- React Query for data fetching
- React Hook Form for form management

## Getting Started

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn

### Installation
1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Set up environment variables:
```bash
cp .env.example .env.local
```

4. Start the development server:
```bash
npm run dev
# or
yarn dev
```

## Project Structure
```
frontend/
├── src/
│   ├── components/    # Reusable UI components
│   ├── pages/        # Page components and routing
│   ├── hooks/        # Custom React hooks
│   ├── utils/        # Utility functions
│   ├── types/        # TypeScript type definitions
│   ├── styles/       # Global styles and Tailwind config
│   └── api/          # API integration and services
├── public/           # Static assets
└── tests/            # Frontend tests
```

## Development Guidelines

### Component Structure
- Use functional components with TypeScript
- Implement proper prop typing
- Follow the container/presenter pattern for complex components

### Styling
- Use Tailwind CSS classes for styling
- Create custom utility classes in `tailwind.config.js`
- Follow mobile-first responsive design

### State Management
- Use React Query for server state
- Implement React Context for global state when necessary
- Utilize local state for component-specific data

### Testing
- Write unit tests for components using Jest and React Testing Library
- Implement integration tests for critical user flows
- Run tests with `npm test` or `yarn test`

## Build and Deployment
```bash
# Create production build
npm run build
# or
yarn build

# Start production server
npm start
# or
yarn start
```

## Best Practices
- Follow ESLint and Prettier configurations
- Write meaningful commit messages
- Document complex components and utilities
- Optimize images and assets
- Implement proper error handling
- Use semantic HTML elements
- Ensure accessibility standards are met 