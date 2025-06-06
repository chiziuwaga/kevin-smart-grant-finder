# Smart Grant Finder Frontend

This is the frontend for the Smart Grant Finder application, built with React.

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```
   or
   ```
   yarn install
   ```

### Development

To start the development server:

```
npm start
```

or

```
yarn start
```

This will run the app in development mode. Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes. You may also see any lint errors in the console.

### Building for Production

To build the app for production:

```
npm run build
```

or

```
yarn build
```

This builds the app for production to the `build` folder. It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes. Your app is ready to be deployed!

## Features

- Dashboard with grant metrics and visualizations
- Grant search functionality
- Grant management
- Responsive design for mobile and desktop

## API Integration

The frontend connects to the backend API. The base URL for API calls can be configured in the `.env` file:

```
REACT_APP_API_URL=http://localhost:8501/api
```

For production deployment, you'll need to set this to your actual API endpoint.

## Folder Structure

- `/src/api` - API client and request handling
- `/src/components` - Reusable UI components
- `/src/pages` - Top-level page components
- `/src/hooks` - Custom React hooks
- `/src/assets` - Static assets like images and icons

## Technologies Used

- React.js
- Material UI for components
- Recharts for data visualization
- React Router for navigation
 