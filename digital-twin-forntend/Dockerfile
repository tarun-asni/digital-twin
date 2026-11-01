FROM node:20

WORKDIR /app

# Copy only package.json files first
COPY package*.json ./

# Install dependencies from package.json
RUN npm install

COPY . .