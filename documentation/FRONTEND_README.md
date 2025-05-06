# Frontend Documentation

## Overview
The frontend of our Lead Generation application is built using React, Vite, TypeScript, and Tailwind CSS to provide a responsive and user-friendly interface.

## Tech Stack
- React 19
- Vite
- TypeScript
- Tailwind CSS

## Getting Started

### Prerequisites
- Node.js (v20.x or higher)
- npm

### Installation
1. Navigate to the frontend directory:
```bash
cd frontend
```
2. Install dependencies:
```bash
npm install
```
3. Start the development server:
```bash
npm run dev
```
- The frontend runs on port 5173 by default.

## Project Structure
```
frontend/
├── src/
│   ├── components/    # Reusable UI components
│   ├── pages/        # Page components and routing
│   ├── hooks/        # Custom React hooks
│   ├── utils/        # Utility functions
│   └── assets/       # Static assets
├── public/           # Static files
└── ...
```

## Development Guidelines
- Use functional components with TypeScript
- Use Tailwind CSS for styling
- Follow mobile-first responsive design
- Use React Context or local state as needed

## Testing
- Write unit tests for components using React Testing Library
- Run tests with `npm test`

## Build and Deployment
```bash
# Create production build
npm run build
```
- Serve the static files in `frontend/dist` using your preferred web server or hosting platform.

## Best Practices
- Follow ESLint and Prettier configurations
- Write meaningful commit messages
- Document complex components and utilities
- Optimize images and assets
- Implement proper error handling
- Use semantic HTML elements
- Ensure accessibility standards are met 