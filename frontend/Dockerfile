# Development Dockerfile for Next.js frontend
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=development
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1

# Install wget for health checks
RUN apk add --no-cache wget

# Create non-root user with configurable UID/GID
ARG USER_ID=1001
ARG GROUP_ID=1001
RUN addgroup -g $GROUP_ID -S nodejs 2>/dev/null || addgroup -S nodejs
RUN adduser -S nextjs -u $USER_ID -G nodejs 2>/dev/null || adduser -S nextjs -G nodejs

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for development)
RUN npm ci

# Copy source code
COPY . .

# Create .next directory with proper permissions
RUN mkdir -p /app/.next/cache && chmod 777 /app/.next && chmod 777 /app/.next/cache

# Change ownership to non-root user
RUN chown -R nextjs:nodejs /app

# Switch to non-root user (commented out for now to fix permissions)
# USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Start the development server
CMD ["sh", "-c", "mkdir -p /app/.next/cache && chmod 777 /app/.next/cache && npm run dev"] 