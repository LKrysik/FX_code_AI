# FX Cryptocurrency Trading System

> **Quick Links**: [📖 Full Documentation](docs/INDEX.md) | [🤖 Claude Code Guide](CLAUDE.md) | [🤝 Contributing](CONTRIBUTING.md) | [📊 Current Sprint](docs/STATUS.md)

---

# Frontend - Crypto Trading Bot

Next.js + TypeScript frontend for the FX Cryptocurrency Trading System.

## 🚀 Features

- **Strategy Builder Canvas**: Visual drag-and-drop strategy creation
- **Real-time Dashboard**: Live trading metrics and performance
- **WebSocket Integration**: Real-time market data and signals
- **Responsive Design**: Works on desktop and mobile devices
- **Dark Theme**: Professional trading interface

## 🛠️ Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI Library**: Material-UI (MUI)
- **Charts**: Recharts
- **Canvas**: React Flow
- **State Management**: React hooks
- **API Client**: Axios + Socket.io-client

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Dashboard
│   │   └── strategy-builder/  # Strategy Builder page
│   ├── components/
│   │   ├── layout/            # Layout components
│   │   └── canvas/            # Strategy canvas components
│   │       └── nodes/         # Custom node types
│   ├── services/              # API and WebSocket services
│   ├── types/                 # TypeScript type definitions
│   └── utils/                 # Helper functions
├── public/                    # Static assets
├── package.json
├── tsconfig.json
└── next.config.js
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Running FastAPI backend on `http://localhost:8080`

### Installation

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Set up environment variables:**
   Create `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8080
   NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8080/ws
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open browser:**
   Navigate to `http://localhost:3000`

## 🎯 Key Components

### Strategy Builder Canvas

**Location**: `src/app/strategy-builder/page.tsx`

Features:
- Drag & drop node creation
- Visual strategy flow
- Real-time validation
- Node property panels
- Save/load strategies

**Node Types**:
- **Indicator Nodes**: Price, volume, technical indicators
- **Condition Nodes**: Threshold, range, pattern conditions
- **Action Nodes**: Buy/sell signals, alerts

### Dashboard

**Location**: `src/app/page.tsx`

Features:
- Portfolio balance overview
- Trading performance metrics
- Active strategies status
- System health indicators

### API Integration

**Location**: `src/services/api.ts`

Features:
- REST API client with error handling
- WebSocket connection management
- Automatic reconnection
- Request/response interceptors

## 🔧 Development

### Available Scripts

```bash
# Development
npm run dev          # Start dev server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
```

### Code Quality

- **TypeScript**: Strict type checking enabled
- **ESLint**: Code linting and formatting
- **Prettier**: Code formatting (via ESLint)

### Component Patterns

1. **Custom Hooks**: Business logic separation
2. **Compound Components**: Related component grouping
3. **Render Props**: Flexible component APIs
4. **Error Boundaries**: Graceful error handling

## 🌐 API Integration

### Backend Connection

The frontend connects to the FastAPI backend via:

- **REST API**: `http://localhost:8080`
- **WebSocket**: `ws://127.0.0.1:8080/ws`

### Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8080    # FastAPI backend URL
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8080/ws       # WebSocket URL
```

## 🎨 UI/UX Design

### Theme

- **Dark Theme**: Professional trading interface
- **Material Design**: Consistent component library
- **Responsive**: Mobile-first design approach

### Key UI Patterns

1. **Canvas-based Editing**: Visual strategy creation
2. **Real-time Updates**: Live data streaming
3. **Progressive Disclosure**: Show details on demand
4. **Contextual Actions**: Right-click menus and toolbars

## 🚀 Deployment

### Build for Production

```bash
npm run build
npm run start
```

### Docker Deployment

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🔍 Troubleshooting

### Common Issues

1. **Backend Connection Failed**
   - Ensure FastAPI backend is running on port 8000
   - Check CORS settings in backend
   - Verify environment variables

2. **WebSocket Connection Issues**
   - Check WebSocket URL configuration
   - Verify backend WebSocket endpoint
   - Check browser console for connection errors

3. **Build Errors**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Clear Next.js cache: `rm -rf .next`
   - Check TypeScript errors: `npm run type-check`

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Material-UI Documentation](https://mui.com/)
- [React Flow Documentation](https://reactflow.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## 🤝 Contributing

1. Follow TypeScript strict mode
2. Use Material-UI components when possible
3. Write comprehensive tests
4. Follow existing code patterns
5. Update documentation for new features