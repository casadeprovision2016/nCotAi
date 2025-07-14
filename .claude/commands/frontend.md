# Frontend Development Commands

React TypeScript frontend operations for COTAI system.

## Usage
`/frontend` - Start development server
`/frontend install` - Install dependencies
`/frontend build` - Build for production
`/frontend lint` - Run linting and formatting
`/frontend test` - Run frontend tests
`/frontend type-check` - Run TypeScript type checking

## Commands Executed

### Start Development Server
```bash
cd frontend
npm start
```

### Install Dependencies
```bash
cd frontend
npm install
```

### Build for Production
```bash
cd frontend
npm run build
```

### Linting and Formatting
```bash
cd frontend
npm run lint
npm run lint:fix
npm run format
```

### Run Tests
```bash
cd frontend
npm test
npm test -- --coverage
npm test -- --watchAll=false
```

### Type Checking
```bash
cd frontend
npx tsc --noEmit
```

## Development URLs
- Frontend: http://localhost:3000
- API Integration: http://localhost:8000/api

## Build Output
- Production build: `frontend/build/`
- Static assets ready for deployment