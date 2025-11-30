FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

# Use --host to expose to outside container
CMD ["npm", "run", "dev", "--", "--host"]
